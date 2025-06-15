# Arcane Scribe

The **Arcane Scribe** is a serverless application enabling users to pose natural language questions concerning TTRPG rules. The core of this system will involve ingesting and processing TTRPG SRDs (System Reference Documents) to create a knowledge base that can be queried using natural language.

## System Flow

1. Client requests an upload URL via the `as-presigned-url-generator`
2. Client uploads a PDF document using the presigned URL
3. S3 upload event triggers the `as-pdf-ingestor`
4. Client submits a query to the `as-rag-query` endpoint
5. The query Lambda processes the question and returns an answer
6. All API endpoints are protected by the `as-authorizer` Lambda
