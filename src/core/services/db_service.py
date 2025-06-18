# Standard Library
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Third Party
from boto3.dynamodb.conditions import Key

# Local Modules
from core.aws import DynamoDb
from core.utils import DocumentProcessingStatus


class DatabaseService:
    """Service for managing document records in a DynamoDB table."""

    def __init__(self, table_name: str):
        """Initialize the DatabaseService with a DynamoDB table.

        Parameters
        ----------
        table_name : str
            The name of the DynamoDB table where document records will be
            stored.
        """
        self.dynamodb = DynamoDb(table_name=table_name)

    def create_document_record(
        self,
        owner_id: str,
        srd_id: str,
        file_name: str,
        s3_key: str,
        content_type: str,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new document record in the DynamoDB table.

        Parameters
        ----------
        owner_id : str
            The Cognito username of the owner of the document.
        srd_id : str
            The ID of the SRD (System Requirements Document) associated with
            the document.
        file_name : str
            The original file name of the document being uploaded.
        s3_key : str
            The S3 key where the document is stored.
        content_type : str
            The content type of the document (e.g., 'application/pdf', 'image/png').
        document_id : Optional[str], optional
            A unique identifier for the document. If not provided, a new UUID
            will be generated.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the details of the created document record,
            including:
            - `owner_srd_composite`: A composite key combining owner_id and srd_id.
            - `document_id`: A unique identifier for the document.
            - `original_file_name`: The original file name of the uploaded document.
            - `s3_key`: The S3 key where the document is stored.
            - `content_type`: The content type of the document.
            - `upload_timestamp`: The timestamp when the document was uploaded.
            - `processing_status`: The initial processing status of the document (e.g., 'pending').
        """
        # Generate a unique document ID and composite key for the owner and SRD
        document_id = document_id or str(uuid.uuid4())
        owner_srd_composite = f"{owner_id}#{srd_id}"

        # Create the item to be stored in DynamoDB
        item = {
            "owner_srd_composite": owner_srd_composite,
            "document_id": document_id,
            "original_file_name": file_name,
            "s3_key": s3_key,
            "content_type": content_type,
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "processing_status": DocumentProcessingStatus.pending.value,
        }

        # Store the item in DynamoDB
        self.dynamodb.put_item(item=item)

        return item

    def get_document_record(
        self, owner_id: str, srd_id: str, document_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a document record from the DynamoDB table.

        Parameters
        ----------
        owner_id : str
            The Cognito username of the owner of the document.
        srd_id : str
            The ID of the SRD (System Requirements Document) associated with
            the document.
        document_id : str
            The unique identifier for the document.

        Returns
        -------
        Optional[Dict[str, Any]]
            A dictionary containing the document record if found, or None if
            the record does not exist. The dictionary includes:
            - `owner_srd_composite`: A composite key combining owner_id and srd_id.
            - `document_id`: The unique identifier for the document.
            - `original_file_name`: The original file name of the uploaded document.
            - `s3_key`: The S3 key where the document is stored.
            - `content_type`: The content type of the document.
            - `upload_timestamp`: The timestamp when the document was uploaded.
            - `processing_status`: The current processing status of the document.
        """
        # Construct the composite key for the owner and SRD
        owner_srd_composite = f"{owner_id}#{srd_id}"

        return self.dynamodb.get_item(
            key={
                "owner_srd_composite": owner_srd_composite,
                "document_id": document_id,
            }
        )

    def delete_document_record(
        self, owner_id: str, srd_id: str, document_id: str
    ) -> Dict[str, Any]:
        """Delete a document record from the DynamoDB table.

        Parameters
        ----------
        owner_id : str
            The Cognito username of the owner of the document.
        srd_id : str
            The ID of the SRD (System Requirements Document) associated with
            the document.
        document_id : str
            The unique identifier for the document.

        Returns
        -------
        bool
            True if the deletion was successful, False otherwise.
        """
        # Construct the composite key for the owner and SRD
        owner_srd_composite = f"{owner_id}#{srd_id}"

        return self.dynamodb.delete_item(
            key={
                "owner_srd_composite": owner_srd_composite,
                "document_id": document_id,
            }
        )

    def list_document_records(
        self, owner_id: str, srd_id: str
    ) -> Dict[str, Any]:
        """List all document records for a specific owner and SRD.

        Parameters
        ----------
        owner_id : str
            The Cognito username of the owner of the documents.
        srd_id : str
            The ID of the SRD (System Requirements Document) associated with
            the documents.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing a list of document records for the specified
            owner and SRD. Each record includes:
            - `owner_srd_composite`: A composite key combining owner_id and srd_id.
            - `document_id`: The unique identifier for the document.
            - `original_file_name`: The original file name of the uploaded document.
            - `s3_key`: The S3 key where the document is stored.
            - `content_type`: The content type of the document.
            - `upload_timestamp`: The timestamp when the document was uploaded.
            - `processing_status`: The current processing status of the document.
        """
        # Construct the composite key for the owner and SRD
        owner_srd_composite = f"{owner_id}#{srd_id}"

        return self.dynamodb.query(
            key_condition_expression=Key("owner_srd_composite").eq(
                owner_srd_composite
            )
        )

    def update_document_record(
        self,
        owner_id: str,
        srd_id: str,
        document_id: str,
        update_map: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a document record in the DynamoDB table.

        Parameters
        ----------
        owner_id : str
            The Cognito username of the owner of the document.
        srd_id : str
            The ID of the SRD (System Requirements Document) associated with
            the document.
        document_id : str
            The unique identifier for the document.
        update_map : Dict[str, Any]
            A dictionary containing the fields to update and their new values.
            The keys should match the attribute names in the DynamoDB table.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the updated document record.
        """
        # Construct the composite key for the owner and SRD
        owner_srd_composite = f"{owner_id}#{srd_id}"

        return self.dynamodb.update_item(
            key={
                "owner_srd_composite": owner_srd_composite,
                "document_id": document_id,
            },
            update_expression="SET "
            + ", ".join(f"{k} = :{k}" for k in update_map.keys()),
            expression_attribute_values={
                f":{k}": v for k, v in update_map.items()
            },
        )

    def delete_all_document_records(
        self, owner_id: str, srd_id: str
    ) -> Dict[str, Any]:
        """Delete all document records for a specific owner and SRD.

        Parameters
        ----------
        owner_id : str
            The Cognito username of the owner of the documents.
        srd_id : str
            The ID of the SRD (System Requirements Document) associated with
            the documents.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing a message indicating the result of the
            deletion operation.
        """
        # Construct the composite key for the owner and SRD
        owner_srd_composite = f"{owner_id}#{srd_id}"

        # Get all items for the owner and SRD
        items = self.list_document_records(
            owner_id=owner_id, srd_id=srd_id
        ).get("Items", [])

        # If no items found, return a message
        if not items:
            return {"message": "No document records found to delete."}

        # Delete each item
        for item in items:
            self.dynamodb.delete_item(
                key={
                    "owner_srd_composite": owner_srd_composite,
                    "document_id": item["document_id"],
                }
            )

        return {"message": "All document records deleted successfully."}
