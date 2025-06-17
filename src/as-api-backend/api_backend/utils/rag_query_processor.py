# Standard Library
import os
import time
import json
import shutil
import hashlib
from typing import Optional, Dict, Any, List

# Third Party
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from langchain_aws import ChatBedrock
from langchain_community.vectorstores import FAISS
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.prompts import PromptTemplate

# Local Modules
from core.aws import S3Client, DynamoDb
from core.utils import DocumentProcessingStatus
from core.services import DatabaseService
from core.utils.config import (
    BEDROCK_EMBEDDING_MODEL_ID,
    BEDROCK_TEXT_GENERATION_MODEL_ID,
    VECTOR_STORE_BUCKET_NAME,
    QUERY_CACHE_TABLE_NAME,
    DOCUMENTS_METADATA_TABLE_NAME,
)
from api_backend.aws import BedrockRuntimeClient

# Initialize logger
logger = Logger(service="rag-query-processor")

# Default cache settings
CACHE_TTL_SECONDS = 3600  # Cache responses for 1 hour, adjust as needed

# Settings for the FAISS index cache
FAISS_INDEX_CACHE: Dict[str, FAISS] = {}
MAX_CACHE_SIZE = 5

# Global LLM and Bedrock clients to reuse across warm invocations
BEDROCK_RUNTIME_CLIENT = BedrockRuntimeClient()
DEFAULT_LLM_INSTANCE: Optional[ChatBedrock] = None


def get_llm_instance(
    generation_config: Dict[str, Any],
) -> Optional[ChatBedrock]:
    """Get a ChatBedrock instance configured with the provided generation
    config. This function validates the generation_config parameters and
    applies them to the ChatBedrock instance. If the configuration is invalid
    or if the ChatBedrock instance cannot be created, it will return the
    default instance if available, or None if no default instance is set.

    Parameters
    ----------
    generation_config : Dict[str, Any]
        The generation configuration parameters, which may include:
        - temperature (float): Controls randomness in generation.
        - topP (float): Controls diversity via nucleus sampling.
        - maxTokenCount (int): Maximum number of tokens to generate.
        - stopSequences (list of str): Sequences that will stop generation.

    Returns
    -------
    Optional[ChatBedrock]
        A ChatBedrock instance configured with the provided generation config,
        or None if the configuration is invalid or if no default instance is
        set.
    """
    global DEFAULT_LLM_INSTANCE  # Can be used if no dynamic config provided

    # Initialize effective model kwargs
    effective_model_kwargs: Dict[str, Any] = {}

    # Handle 'temperature'
    temp_value = generation_config.get("temperature")
    effective_model_kwargs["temperature"] = (
        float(temp_value) if temp_value is not None else 0.1
    )

    # Handle 'topP'
    top_p_value = generation_config.get("top_p")
    effective_model_kwargs["top_p"] = (
        float(top_p_value) if top_p_value is not None else 1.0
    )

    # Handle 'maxTokenCount'
    max_tokens_value = generation_config.get("max_tokens")
    effective_model_kwargs["max_tokens"] = (
        int(max_tokens_value) if max_tokens_value is not None else 1024
    )

    # Handle 'stopSequences'
    stop_sequences_value = generation_config.get("stop_sequences")
    effective_model_kwargs["stop_sequences"] = (
        stop_sequences_value if stop_sequences_value is not None else []
    )

    # Create ChatBedrock instance with effective model kwargs
    try:
        current_llm = BEDROCK_RUNTIME_CLIENT.get_chat_model(
            model_id=BEDROCK_TEXT_GENERATION_MODEL_ID,
            model_kwargs=effective_model_kwargs,
        )
        logger.info(
            f"ChatBedrock instance configured with: {effective_model_kwargs}"
        )
        return current_llm
    # Return the default instance if available
    except Exception as e_llm_init:
        logger.exception(
            f"Failed to initialize dynamic ChatBedrock instance: {e_llm_init}"
        )
        DEFAULT_LLM_INSTANCE = BEDROCK_RUNTIME_CLIENT.get_chat_model(
            model_id=BEDROCK_TEXT_GENERATION_MODEL_ID,
            model_kwargs={
                "temperature": 0.1,
                "maxTokenCount": 1024,
            },
        )
        return DEFAULT_LLM_INSTANCE  # Return default instance if dynamic config fails


def _load_and_merge_faiss_indices_for_srd(
    owner_id: str, srd_id: str, lambda_logger: Logger
) -> Optional[FAISS]:
    """Load and merge FAISS indices for a given SRD (System Reference Document)
    ID. This function retrieves all FAISS indices associated with the specified
    SRD ID from S3, merges them into a single FAISS index, and caches the
    result in memory for future queries. It first checks an in-memory cache,
    then queries DynamoDB for document metadata, downloads the individual FAISS
    indices from S3, and finally merges them into a single FAISS index.

    Parameters
    ----------
    owner_id : str
        The owner ID of the user making the query, typically extracted from
        the authentication token.
    srd_id : str
        The SRD ID to load the FAISS indices for.
    lambda_logger : Logger
        The logger instance to use for logging.

    Returns
    -------
    Optional[FAISS]
        The merged FAISS index for the specified SRD ID, or None if loading
        or merging failed.
    """
    # Construct a composite key for the FAISS index cache
    composite_key = f"{owner_id}#{srd_id}"

    # 1. Check in-memory cache first
    if composite_key in FAISS_INDEX_CACHE:
        lambda_logger.info(
            f"FAISS index for '{composite_key}' found in cache."
        )
        return FAISS_INDEX_CACHE[composite_key]

    # Initialize clients
    db_service = DatabaseService(table_name=DOCUMENTS_METADATA_TABLE_NAME)
    s3_client = S3Client(bucket_name=VECTOR_STORE_BUCKET_NAME)

    # 2. Query DynamoDB for all documents in the SRD
    lambda_logger.info(
        f"Querying DynamoDB for documents in SRD: {composite_key}"
    )
    try:
        document_records = db_service.list_document_records(
            owner_id=owner_id, srd_id=srd_id
        ).get("Items", [])
        if not document_records:
            logger.warning(
                f"No document metadata found for SRD: {composite_key}"
            )
            return None
    except Exception as e:
        logger.exception(f"Failed to query DynamoDB for SRD documents: {e}")
        return None

    # Filter for successfully processed documents
    processed_docs = [
        doc
        for doc in document_records
        if doc.get("processing_status")
        == DocumentProcessingStatus.completed.value
    ]

    if not processed_docs:
        logger.warning(
            f"No successfully processed documents found for SRD: {composite_key}"
        )
        return None

    lambda_logger.info(
        f"Found {len(processed_docs)} processed documents for this SRD."
    )

    # 3. Download and load all FAISS indices
    embedding_model = BEDROCK_RUNTIME_CLIENT.get_embedding_model(
        model_id=BEDROCK_EMBEDDING_MODEL_ID
    )

    # Prepare a list to hold the FAISS vector stores
    vector_stores: List[FAISS] = []
    temp_base_dir = f"/tmp/{composite_key.replace('#', '_')}"
    shutil.rmtree(temp_base_dir, ignore_errors=True)  # Clean up previous runs

    for doc in processed_docs:
        # Get the sort key for the document
        document_id = doc.get("document_id")
        if not document_id:
            # Skip documents without an ID
            continue

        # Create a local directory for this document's FAISS index
        local_faiss_dir = os.path.join(temp_base_dir, document_id)
        os.makedirs(local_faiss_dir, exist_ok=True)

        # Construct the S3 index prefix for this SRD and document
        s3_index_prefix = f"{owner_id}/{srd_id}/vector_store"

        try:
            # Download index.faiss and index.pkl (or however they are named)
            s3_client.download_file(
                object_key=f"{s3_index_prefix}/{document_id}.faiss",
                download_path=os.path.join(
                    local_faiss_dir, f"{document_id}.faiss"
                ),
            )
            s3_client.download_file(
                object_key=f"{s3_index_prefix}/{document_id}.pkl",
                download_path=os.path.join(
                    local_faiss_dir, f"{document_id}.pkl"
                ),
            )

            # Load the individual index from its local path
            loaded_store = FAISS.load_local(
                folder_path=local_faiss_dir,
                embeddings=embedding_model,
                index_name=document_id,
                allow_dangerous_deserialization=True,
            )
            vector_stores.append(loaded_store)
            lambda_logger.info(
                f"Successfully loaded index for document: {document_id}"
            )

        except ClientError as e:
            lambda_logger.error(
                f"Could not download index for document {document_id}. Error: {e}"
            )
            continue  # Skip this document and try others

    # Cleanup downloaded files
    shutil.rmtree(temp_base_dir, ignore_errors=True)

    if not vector_stores:
        lambda_logger.error("Failed to load any vector stores for the SRD.")
        return None

    # 4. Merge the indices
    merged_vector_store = vector_stores[0]
    if len(vector_stores) > 1:
        lambda_logger.info(
            f"Merging {len(vector_stores)} vector stores into one..."
        )
        for i in range(1, len(vector_stores)):
            merged_vector_store.merge_from(vector_stores[i])
        lambda_logger.info("Merge complete.")

    # 5. Update cache
    if len(FAISS_INDEX_CACHE) >= MAX_CACHE_SIZE:
        oldest_key = next(iter(FAISS_INDEX_CACHE))
        FAISS_INDEX_CACHE.pop(oldest_key)
    FAISS_INDEX_CACHE[composite_key] = merged_vector_store

    return merged_vector_store


def get_answer_from_rag(
    query_text: str,
    owner_id: str,
    srd_id: str,
    invoke_generative_llm: bool,
    use_conversational_style: bool,
    generation_config_payload: Dict[str, Any],
    number_of_documents: Optional[int] = 4,
    lambda_logger: Optional[Logger] = None,
) -> Dict[str, Any]:
    """Process a query using RAG (Retrieval-Augmented Generation) with Bedrock.
    This function retrieves relevant documents from a FAISS index and
    optionally invokes a generative LLM to generate an answer based on the
    retrieved context.

    Parameters
    ----------
    query_text : str
        The query text to process.
    owner_id : str
        The owner ID of the user making the query, typically extracted from
        the authentication token.
    srd_id : str
        The SRD ID to use for the query.
    invoke_generative_llm : bool
        Whether to invoke the generative LLM for the query.
    use_conversational_style : bool
        Whether to use a conversational style for the LLM response.
    generation_config_payload : Dict[str, Any]
        Configuration payload for the LLM generation, including parameters
        like temperature, max tokens, etc.
    number_of_documents : Optional[int]
        The number of documents to retrieve from the source. Defaults to 4.
    lambda_logger : Optional[Logger]
        The logger instance to use for logging. If None, a default logger
        will be used.

    Returns
    -------
    Dict[str, Any]
        The response containing the answer and source information, or an error
        message.
    """
    # Initialize the DynamoDB client
    dynamodb_client = DynamoDb(table_name=QUERY_CACHE_TABLE_NAME)

    # Create composite key for FAISS index cache
    composite_key = f"{owner_id}#{srd_id}"

    # Use the provided logger or create a new one if not provided
    if lambda_logger is None:
        lambda_logger = logger

    # Cache table is only relevant if LLM is invoked
    if invoke_generative_llm:
        lambda_logger.warning(
            "Invoking generative LLM, cache table will be used for caching responses."
        )

    # Generate a cache key
    cache_key_string = f"{composite_key}-{query_text}-{invoke_generative_llm}"
    query_hash = hashlib.md5(cache_key_string.encode()).hexdigest()

    # 1. Check cache if invoking LLM and cache is configured
    if invoke_generative_llm and QUERY_CACHE_TABLE_NAME and dynamodb_client:
        try:
            lambda_logger.info(f"Checking cache for query_hash: {query_hash}")

            # Attempt to get the cached response from DynamoDB
            response = dynamodb_client.get_item(
                key={"query_hash": query_hash},
            )

            # Check if the item exists and is still valid (TTL)
            if response and int(response.get("ttl", 0)) > time.time():
                # Return the cached answer if it exists
                lambda_logger.info(f"Cache hit for query_hash: {query_hash}")
                return {
                    "answer": response["answer"],
                    "source": "cache",
                }
        except ClientError as e:
            # Handle DynamoDB client errors
            lambda_logger.warning(
                f"DynamoDB cache get_item error: {e}. Proceeding without cache."
            )
        except Exception as e:
            # Catch other potential errors like missing 'answer' or 'S'
            lambda_logger.warning(
                f"Error processing cache item: {e}. Proceeding without cache."
            )

    # 2. Load the MERGED FAISS index for the entire SRD
    vector_store = _load_and_merge_faiss_indices_for_srd(
        owner_id=owner_id, srd_id=srd_id, lambda_logger=lambda_logger
    )
    if not vector_store:
        return {"error": f"Could not load SRD data for '{composite_key}'."}

    # 3. Perform the similarity search
    lambda_logger.info(
        f"Performing similarity search for query: '{query_text}'"
    )
    try:
        # The retriever will fetch relevant documents.
        retriever = vector_store.as_retriever(
            search_kwargs={"k": number_of_documents}
        )
    except Exception as e:
        lambda_logger.exception(f"Error creating retriever: {e}")
        return {"error": "Failed to prepare for information retrieval."}

    # Handle conversational style for the query text
    final_query_text = query_text
    if invoke_generative_llm and use_conversational_style:
        final_query_text = f"User: {query_text}\nBot:"
        lambda_logger.info(
            "Using conversational style for query input to LLM."
        )

    # If not invoking generative LLM, just return formatted retrieved chunks
    if not invoke_generative_llm:
        lambda_logger.info(
            "Generative LLM not invoked by client request. Returning retrieved context."
        )
        docs = retriever.invoke(query_text)  # Langchain 0.2.x uses invoke

        # Check if no documents were retrieved
        if not docs:
            return {
                "answer": (
                    "No specific information found to answer your query based on retrieval."
                ),
                "source": "retrieval_only",
            }

        # Format the retrieved documents into a string
        context_str = "\n\n---\n\n".join([doc.page_content for doc in docs])
        formatted_answer = (
            "Based on the retrieved SRD content for your query "
            f"'{query_text}':\n{context_str}"
        )
        return {"answer": formatted_answer, "source": "retrieval_only"}

    # Initialize LLM instance with dynamic config for this request
    current_llm_instance = get_llm_instance(generation_config_payload)
    if not current_llm_instance:
        lambda_logger.error(
            "Failed to initialize ChatBedrock instance with dynamic config."
        )
        return {
            "error": (
                "Internal server error: Generative LLM component could not be configured."
            )
        }

    # Define the prompt template for the generative LLM
    # This prompt template is crucial for guiding the LLM's response.
    prompt_template_str = """You are 'Arcane Scribe', a helpful TTRPG assistant.
Based *only* on the following context from the System Reference Document (SRD), provide a concise and direct answer to the question.
If the question (which might be formatted as 'User: ... Bot:') asks for advice, optimization (e.g., "min-max"), or creative ideas, you may synthesize or infer suggestions *grounded in the provided SRD context*.
Do not introduce rules, abilities, or concepts not present in or directly supported by the context.
If the context does not provide enough information for a comprehensive answer or suggestion, state that clearly.
Always be helpful and aim to directly address the user's intent.
If the question is not formatted as 'User: ... Bot:', you may assume it is a direct question and respond accordingly.

Context:
{context}

Question: {question}

Helpful Answer:"""

    # Create a PromptTemplate instance with the defined template
    PROMPT = PromptTemplate(
        template=prompt_template_str, input_variables=["context", "question"]
    )

    # Create a RetrievalQA chain. This chain will:
    #  1. Use the 'retriever' to fetch documents.
    #  2. Stuff them into the 'PROMPT'.
    #  3. Send that to the 'llm' (ChatBedrock).
    qa_chain = RetrievalQA.from_chain_type(
        llm=current_llm_instance,  # Use dynamically configured LLM
        chain_type="stuff",  # "stuff" is good for short contexts
        retriever=retriever,
        chain_type_kwargs={"prompt": PROMPT},
        return_source_documents=True,  # Optionally return source documents
    )

    # Invoke the RAG chain with the query text
    lambda_logger.info(
        f"Invoking RAG chain with Bedrock LLM for query: '{final_query_text}'"
    )
    try:
        # The 'query' key for invoke should contain what the {question}
        #   placeholder in PROMPT expects.
        result = qa_chain.invoke(
            {"query": final_query_text}
        )  # Langchain 0.2.x uses invoke
        answer = result.get("result", "No answer generated.")
        source_docs_content = [
            doc.page_content for doc in result.get("source_documents", [])
        ]

        # Cache the successful Bedrock response
        if (
            QUERY_CACHE_TABLE_NAME
            and dynamodb_client
            and answer != "No answer generated."
        ):
            try:
                # Store the response in DynamoDB cache
                ttl_value = int(time.time() + CACHE_TTL_SECONDS)
                dynamodb_client.put_item(
                    item={
                        "query_hash": query_hash,
                        "answer": answer,
                        "owner_id": owner_id,
                        "srd_id": srd_id,
                        "query_text": query_text,
                        "source_documents_summary": (
                            "; ".join(source_docs_content)
                        )[:1000],
                        "timestamp": str(time.time()),
                        "ttl": str(ttl_value),
                        "generation_config_used": json.dumps(
                            generation_config_payload
                        ),
                        "was_conversational": use_conversational_style,
                    },
                )
                lambda_logger.info(
                    f"Bedrock response cached for query_hash: {query_hash}"
                )
            # Catch DynamoDB client errors
            except ClientError as e:
                lambda_logger.warning(
                    f"DynamoDB cache put_item error: {e}. Response not cached."
                )

        # Return the answer and source documents
        lambda_logger.info(
            f"Successfully generated response from Bedrock LLM for query: '{query_text}'"
        )
        return {
            "answer": answer,
            "source_documents_retrieved": len(source_docs_content),
            "source": "bedrock_llm",
        }
    # Catch specific Bedrock client errors
    except ClientError as e:
        lambda_logger.exception(
            f"Bedrock API error during RAG chain execution: {e}"
        )
        return {
            "error": (
                "Error communicating with the AI model. Please try again."
            )
        }
    # Catch other exceptions that may occur during the chain execution
    except Exception as e:
        lambda_logger.exception(f"Error during RAG chain execution: {e}")
        return {"error": "Failed to generate an answer using the RAG chain."}
