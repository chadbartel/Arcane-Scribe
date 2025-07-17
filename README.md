# Arcane Scribe

The **Arcane Scribe** is a serverless application enabling users to pose natural language questions concerning TTRPG rules. The core of this system involves ingesting and processing TTRPG SRDs (System Reference Documents) to create a knowledge base that can be queried using natural language.

## Table of Contents

- [Requirements](#requirements)
- [Installation/Setup](#installationsetup)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Tests](#tests)
- [Debugging](#debugging)
- [Deployment](#deployment)
- [Cleanup](#cleanup)
- [License](#license)

## Requirements

### Local Development Requirements

- **Python**: 3.12+ (managed via Poetry)
- **Poetry**: For dependency management and packaging
- **Node.js**: 18+ (for AWS CDK)
- **AWS CDK**: 2.201.0+ (for infrastructure deployment)
- **AWS CLI**: Configured with appropriate credentials

### Required AWS Infrastructure

The application requires the following AWS services:

- **AWS Lambda**: For serverless compute functions
- **Amazon API Gateway**: HTTP API for REST endpoints
- **Amazon S3**: For document storage and vector embeddings
- **Amazon DynamoDB**: For metadata storage
- **Amazon Bedrock**: For AI/ML embeddings and text generation
- **Amazon Cognito**: For user authentication
- **AWS Secrets Manager**: For storing the admin password
- **Amazon Route 53**: For custom domain management
- **AWS Certificate Manager**: For SSL/TLS certificates
- **AWS IAM**: For permissions and access control

## Installation/Setup

### 1. Clone the Repository

```bash
git clone https://github.com/chadbartel/Arcane-Scribe.git
cd arcane-scribe
```

### 2. Install Python Dependencies

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 3. Install AWS CDK

```bash
npm install -g aws-cdk
```

### 4. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and default region
```

### 5. Bootstrap CDK (First Time Only)

```bash
cdk bootstrap
```

## Configuration

### Core Configuration (`cdk.context.json`)

The main configuration is stored in `cdk.context.json`. Update this file with your specific settings:

```json
{
  "stack_name_prefix": "arcane-scribe-stack",
  "api_prefix": "/api/v1",
  "domain_name": "your-domain.com",
  "subdomain_name": "arcane-scribe",
  "authorizer_header_name": "x-arcane-auth-token",
  "bedrock_embedding_model_id": "amazon.titan-embed-text-v2:0",
  "bedrock_text_generation_model_id": "anthropic.claude-3-5-haiku-20241022-v1:0",
  "admin_secret_name": "prod/arcane-scribe/admin",
  "admin_email": "your-email@example.com",
  "admin_username": "your-username"
}
```

### Environment Variables

Set the following environment variables for CDK deployment:

```bash
export CDK_DEFAULT_ACCOUNT="your-aws-account-id"
export CDK_DEFAULT_REGION="your-preferred-region"
```

### Poetry Configuration

The project uses Poetry for dependency management. Key configuration is in `pyproject.toml`:

- **Python Version**: ~3.12
- **Main Dependencies**: FastAPI, Boto3, LangChain, AWS CDK
- **Dev Dependencies**: pytest, black, flake8, isort, nox

## Usage

### Running the Application Locally

For local development and testing:

```bash
# Run unit tests
poetry run pytest tests/unit

# Run specific test harness
python dev_test_harness.py
```

### Deploying to AWS

```bash
# Deploy the full stack
cdk deploy

# Deploy with specific stack suffix (for feature branches)
cdk deploy -c stack-suffix=dev

# View what will be deployed (dry run)
cdk diff
```

## API Endpoints

### Authentication

All API endpoints require authentication using Cognito tokens or API keys.

### SRD Document Management

#### Upload Document

- **POST** `/api/v1/srd/{srd_id}/documents/upload-url`
- **Description**: Generate a presigned URL for uploading PDF documents
- **Parameters**:
  - `srd_id` (path): The SRD identifier
  - `file_name` (body): Name of the file to upload
  - `content_type` (body, optional): MIME type (defaults to "application/pdf")

#### List Documents

- **GET** `/api/v1/srd/{srd_id}/documents`
- **Description**: List all documents for a specific SRD

#### Get Document

- **GET** `/api/v1/srd/{srd_id}/documents/{document_id}`
- **Description**: Get details of a specific document

#### Delete Document

- **DELETE** `/api/v1/srd/{srd_id}/documents/{document_id}`
- **Description**: Delete a specific document

#### Delete All Documents

- **DELETE** `/api/v1/srd/{srd_id}/documents`
- **Description**: Delete all documents for a specific SRD

### Query Processing

#### RAG Query

- **POST** `/query`
- **Description**: Process natural language queries against TTRPG documents
- **Parameters**:
  - `query_text` (required): The natural language question
  - `srd_id` (optional): Specific SRD to query
  - `invoke_generative_llm` (optional): Whether to use generative AI
  - `use_conversational_style` (optional): Enable conversational responses
  - `generation_config` (optional): LLM configuration parameters

## Tests

### Running Tests with pytest

```bash
# Run all unit tests
poetry run pytest tests/unit

# Run tests with coverage
poetry run pytest tests/unit --cov=. --cov-report=term-missing

# Run specific test file
poetry run pytest tests/unit/as_api_backend/test_handler.py
```

### Running Tests with Nox

Nox provides automated testing across different environments:

```bash
# Run all configured sessions
nox

# Run specific session
nox -s test_and_lint

# List available sessions
nox -l
```

### Test Structure

- **Unit Tests**: `tests/unit/` - Fast, isolated tests for individual components
- **Integration Tests**: `tests/integration/` - End-to-end tests with AWS services
- **Test Configuration**: `tests/conftest.py` - Shared fixtures and test utilities

### Test Coverage

The project uses `pytest-cov` for coverage reporting. Minimum coverage targets:

- Unit tests: 80%+

## Debugging

### Running API Locally

#### Using the Development Test Harness

```bash
# Run the development test harness
python dev_test_harness.py
```

#### Using FastAPI Development Server

```bash
# Navigate to the API backend
cd src/as-api-backend

# Run with uvicorn
poetry run uvicorn api_backend.main:app --reload --host 0.0.0.0 --port 8000
```

Access the API at: `http://localhost:8000`

### Using Postman for API Testing

#### Import Collection

1. Create a new Postman collection
2. Set up environment variables:
   - `BASE_URL`: `http://localhost:8000` (local) or your deployed API URL
   - `AUTH_TOKEN`: Your Cognito JWT token or API key

#### Sample Requests

**Generate Upload URL:**

```http
POST {{BASE_URL}}/api/v1/srd/dnd5e/documents/upload-url
Content-Type: application/json
Authorization: Bearer {{AUTH_TOKEN}}

{
  "file_name": "players-handbook.pdf",
  "content_type": "application/pdf"
}
```

**Query Documents:**

```http
POST {{BASE_URL}}/query
Content-Type: application/json
Authorization: Bearer {{AUTH_TOKEN}}

{
  "query_text": "What are the spell components for Fireball?",
  "srd_id": "dnd5e",
  "invoke_generative_llm": true
}
```

### Debugging Lambda Functions

#### Local Lambda Testing

```bash
# Use AWS SAM CLI for local Lambda testing
sam local start-api

# Or use the Lambda powertools for local development
poetry run python -m aws_lambda_powertools.local
```

#### CloudWatch Logs

```bash
# View logs for specific Lambda function
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/arcane-scribe

# Tail logs in real-time
aws logs tail /aws/lambda/arcane-scribe-function --follow
```

## Deployment

### Development Deployment

```bash
# Deploy to development environment
cdk deploy -c stack-suffix=dev

# Deploy specific stack
cdk deploy ArcaneScribeStack-dev
```

### Production Deployment

```bash
# Deploy to production (no suffix)
cdk deploy

# Deploy with confirmation
cdk deploy --require-approval always
```

### CI/CD Pipeline

The project supports automated deployment through CI/CD:

1. **Feature Branch**: Deploys with branch name suffix
2. **Main Branch**: Deploys to production environment
3. **Pull Request**: Runs tests and validation

## Cleanup

### Destroy CDK Stack

```bash
# Destroy development stack
cdk destroy -c stack-suffix=dev

# Destroy production stack
cdk destroy

# Force destroy without confirmation
cdk destroy --force
```

### Manual Cleanup

Some resources may require manual cleanup:

1. **S3 Buckets**: Empty buckets before destruction
2. **Route 53 Records**: Remove custom DNS records
3. **Secrets Manager**: Delete stored secrets
4. **CloudWatch Logs**: Remove log groups if needed

```bash
# Empty S3 buckets
aws s3 rm s3://your-documents-bucket --recursive
aws s3 rm s3://your-vector-store-bucket --recursive

# Delete Secrets Manager secrets
aws secretsmanager delete-secret --secret-id prod/arcane-scribe/admin --force-delete-without-recovery
```

## License

This project is licensed under the CC0 1.0 Universal License - see the [LICENSE](LICENSE) file for details.

The CC0 license allows you to use, modify, and distribute this code freely without any restrictions. This is a public domain dedication, meaning you can use this project for any purpose without attribution.
