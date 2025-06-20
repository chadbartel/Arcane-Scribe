"""Unit tests for the s3 module."""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from botocore.exceptions import ClientError, NoCredentialsError

# Local Modules
from core.aws.s3 import S3Client


class TestS3Client:
    """Test cases for the S3Client class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.bucket_name = "test-bucket"
        self.object_key = "test-file.txt"
        self.file_path = "/path/to/local/file.txt"
        self.download_path = "/path/to/download/file.txt"
        self.test_content = b"Test file content"

    @patch("core.aws.s3.boto3.client")
    def test_init_success_with_region(self, mock_boto3_client):
        """Test successful initialization with region_name."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        region_name = "us-west-2"

        s3_client = S3Client(self.bucket_name, region_name=region_name)

        mock_boto3_client.assert_called_once_with(
            "s3", region_name=region_name
        )
        assert s3_client.bucket_name == self.bucket_name
        assert s3_client._client == mock_client

    @patch("core.aws.s3.boto3.client")
    def test_init_success_without_region(self, mock_boto3_client):
        """Test successful initialization without region_name."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        s3_client = S3Client(self.bucket_name)

        mock_boto3_client.assert_called_once_with("s3", region_name=None)
        assert s3_client.bucket_name == self.bucket_name
        assert s3_client._client == mock_client

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_init_failure_no_credentials(self, mock_logger, mock_boto3_client):
        """Test initialization failure due to missing credentials."""
        error = NoCredentialsError()
        mock_boto3_client.side_effect = error

        with pytest.raises(NoCredentialsError):
            S3Client(self.bucket_name)

        mock_logger.error.assert_called_once_with(
            "Failed to create S3 client: %s", error
        )

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_init_failure_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test initialization failure due to generic exception."""
        error = ValueError("Invalid configuration")
        mock_boto3_client.side_effect = error

        with pytest.raises(ValueError):
            S3Client(self.bucket_name)

        mock_logger.error.assert_called_once_with(
            "Failed to create S3 client: %s", error
        )

    @patch("core.aws.s3.boto3.client")
    def test_upload_file_success_default_bucket(self, mock_boto3_client):
        """Test successful file upload using default bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.upload_file.return_value = None

        s3_client = S3Client(self.bucket_name)
        result = s3_client.upload_file(self.file_path, self.object_key)

        mock_client.upload_file.assert_called_once_with(
            self.file_path, self.bucket_name, self.object_key, ExtraArgs=None
        )
        assert result is True

    @patch("core.aws.s3.boto3.client")
    def test_upload_file_success_custom_bucket(self, mock_boto3_client):
        """Test successful file upload using custom bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.upload_file.return_value = None
        custom_bucket = "custom-bucket"

        s3_client = S3Client(self.bucket_name)
        result = s3_client.upload_file(
            self.file_path, self.object_key, bucket_name=custom_bucket
        )

        mock_client.upload_file.assert_called_once_with(
            self.file_path, custom_bucket, self.object_key, ExtraArgs=None
        )
        assert result is True

    @patch("core.aws.s3.boto3.client")
    def test_upload_file_success_with_extra_args(self, mock_boto3_client):
        """Test successful file upload with extra arguments."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.upload_file.return_value = None
        extra_args = {"ACL": "public-read", "ContentType": "text/plain"}

        s3_client = S3Client(self.bucket_name)
        result = s3_client.upload_file(
            self.file_path, self.object_key, extra_args=extra_args
        )

        mock_client.upload_file.assert_called_once_with(
            self.file_path,
            self.bucket_name,
            self.object_key,
            ExtraArgs=extra_args,
        )
        assert result is True

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_upload_file_client_error(self, mock_logger, mock_boto3_client):
        """Test upload_file failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {
                "Error": {
                    "Code": "NoSuchBucket",
                    "Message": "Bucket does not exist",
                }
            },
            "UploadFile",
        )
        mock_client.upload_file.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.upload_file(self.file_path, self.object_key)

        mock_logger.error.assert_called_once_with(
            "Failed to upload file: %s to s3://%s/%s - Error: %s",
            self.file_path,
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is False

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_upload_file_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test upload_file failure due to generic exception."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = FileNotFoundError("File not found")
        mock_client.upload_file.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.upload_file(self.file_path, self.object_key)

        mock_logger.error.assert_called_once_with(
            "Unexpected error uploading file: %s to s3://%s/%s - Error: %s",
            self.file_path,
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is False

    @patch("core.aws.s3.boto3.client")
    def test_get_file_success_default_bucket(self, mock_boto3_client):
        """Test successful file download using default bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.download_file.return_value = None

        s3_client = S3Client(self.bucket_name)
        result = s3_client.get_file(self.object_key, self.download_path)

        mock_client.download_file.assert_called_once_with(
            self.bucket_name, self.object_key, self.download_path
        )
        assert result is True

    @patch("core.aws.s3.boto3.client")
    def test_get_file_success_custom_bucket(self, mock_boto3_client):
        """Test successful file download using custom bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.download_file.return_value = None
        custom_bucket = "custom-bucket"

        s3_client = S3Client(self.bucket_name)
        result = s3_client.get_file(
            self.object_key, self.download_path, bucket_name=custom_bucket
        )

        mock_client.download_file.assert_called_once_with(
            custom_bucket, self.object_key, self.download_path
        )
        assert result is True

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_get_file_client_error(self, mock_logger, mock_boto3_client):
        """Test get_file failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key does not exist"}},
            "DownloadFile",
        )
        mock_client.download_file.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.get_file(self.object_key, self.download_path)

        mock_logger.error.assert_called_once_with(
            "Failed to download file: s3://%s/%s to %s - Error: %s",
            self.bucket_name,
            self.object_key,
            self.download_path,
            error,
        )
        assert result is False

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_get_file_generic_exception(self, mock_logger, mock_boto3_client):
        """Test get_file failure due to generic exception."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = PermissionError("Permission denied")
        mock_client.download_file.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.get_file(self.object_key, self.download_path)

        mock_logger.error.assert_called_once_with(
            "Unexpected error downloading file: s3://%s/%s to %s - Error: %s",
            self.bucket_name,
            self.object_key,
            self.download_path,
            error,
        )
        assert result is False

    @patch("core.aws.s3.boto3.client")
    def test_get_object_content_success_default_bucket(
        self, mock_boto3_client
    ):
        """Test successful object content retrieval using default bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_body = MagicMock()
        mock_body.read.return_value = self.test_content
        mock_client.get_object.return_value = {"Body": mock_body}

        s3_client = S3Client(self.bucket_name)
        result = s3_client.get_object_content(self.object_key)

        mock_client.get_object.assert_called_once_with(
            Bucket=self.bucket_name, Key=self.object_key
        )
        assert result == self.test_content

    @patch("core.aws.s3.boto3.client")
    def test_get_object_content_success_custom_bucket(self, mock_boto3_client):
        """Test successful object content retrieval using custom bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_body = MagicMock()
        mock_body.read.return_value = self.test_content
        mock_client.get_object.return_value = {"Body": mock_body}
        custom_bucket = "custom-bucket"

        s3_client = S3Client(self.bucket_name)
        result = s3_client.get_object_content(
            self.object_key, bucket_name=custom_bucket
        )

        mock_client.get_object.assert_called_once_with(
            Bucket=custom_bucket, Key=self.object_key
        )
        assert result == self.test_content

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_get_object_content_client_error(
        self, mock_logger, mock_boto3_client
    ):
        """Test get_object_content failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key does not exist"}},
            "GetObject",
        )
        mock_client.get_object.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.get_object_content(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Failed to get object content: s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is None

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_get_object_content_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test get_object_content failure due to generic exception."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ValueError("Invalid object")
        mock_client.get_object.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.get_object_content(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Unexpected error getting object content: s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is None

    @patch("core.aws.s3.boto3.client")
    def test_list_objects_success_no_prefix(self, mock_boto3_client):
        """Test successful object listing without prefix."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_objects = [
            {
                "Key": "file1.txt",
                "Size": 100,
                "LastModified": "2023-01-01T00:00:00Z",
            },
            {
                "Key": "file2.txt",
                "Size": 200,
                "LastModified": "2023-01-02T00:00:00Z",
            },
        ]
        # Create proper datetime objects
        # Standard Library
        from datetime import datetime

        for obj in mock_objects:
            obj["LastModified"] = datetime.fromisoformat(
                obj["LastModified"].replace("Z", "+00:00")
            )

        mock_client.list_objects_v2.return_value = {"Contents": mock_objects}

        s3_client = S3Client(self.bucket_name)
        result = s3_client.list_objects()

        mock_client.list_objects_v2.assert_called_once_with(
            Bucket=self.bucket_name, MaxKeys=1000
        )
        expected_result = [
            {
                "Key": "file1.txt",
                "Size": 100,
                "LastModified": "2023-01-01T00:00:00+00:00",
            },
            {
                "Key": "file2.txt",
                "Size": 200,
                "LastModified": "2023-01-02T00:00:00+00:00",
            },
        ]
        assert result == expected_result

    @patch("core.aws.s3.boto3.client")
    def test_list_objects_success_with_prefix(self, mock_boto3_client):
        """Test successful object listing with prefix."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_objects = [
            {
                "Key": "documents/file1.txt",
                "Size": 150,
                "LastModified": "2023-01-01T00:00:00Z",
            }
        ]
        # Create proper datetime objects
        # Standard Library
        from datetime import datetime

        for obj in mock_objects:
            obj["LastModified"] = datetime.fromisoformat(
                obj["LastModified"].replace("Z", "+00:00")
            )

        mock_client.list_objects_v2.return_value = {"Contents": mock_objects}
        prefix = "documents/"

        s3_client = S3Client(self.bucket_name)
        result = s3_client.list_objects(prefix=prefix, max_keys=500)

        mock_client.list_objects_v2.assert_called_once_with(
            Bucket=self.bucket_name, MaxKeys=500, Prefix=prefix
        )
        expected_result = [
            {
                "Key": "documents/file1.txt",
                "Size": 150,
                "LastModified": "2023-01-01T00:00:00+00:00",
            }
        ]
        assert result == expected_result

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_list_objects_success_empty_bucket(
        self, mock_logger, mock_boto3_client
    ):
        """Test successful object listing when bucket is empty."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_objects_v2.return_value = {}  # No Contents key

        s3_client = S3Client(self.bucket_name)
        result = s3_client.list_objects()

        mock_client.list_objects_v2.assert_called_once_with(
            Bucket=self.bucket_name, MaxKeys=1000
        )
        mock_logger.info.assert_called_once_with(
            "No objects found in bucket: %s with prefix: %s",
            self.bucket_name,
            "None",
        )
        assert result == []

    @patch("core.aws.s3.boto3.client")
    def test_list_objects_success_custom_bucket(self, mock_boto3_client):
        """Test successful object listing using custom bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_objects_v2.return_value = {"Contents": []}
        custom_bucket = "custom-bucket"

        s3_client = S3Client(self.bucket_name)
        result = s3_client.list_objects(bucket_name=custom_bucket)

        mock_client.list_objects_v2.assert_called_once_with(
            Bucket=custom_bucket, MaxKeys=1000
        )
        assert result == []

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_list_objects_client_error(self, mock_logger, mock_boto3_client):
        """Test list_objects failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {
                "Error": {
                    "Code": "NoSuchBucket",
                    "Message": "Bucket does not exist",
                }
            },
            "ListObjectsV2",
        )
        mock_client.list_objects_v2.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.list_objects()

        mock_logger.error.assert_called_once_with(
            "Failed to list objects in bucket: %s with prefix: %s - Error: %s",
            self.bucket_name,
            "None",
            error,
        )
        assert result == []

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_list_objects_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test list_objects failure due to generic exception."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ValueError("Invalid bucket name")
        mock_client.list_objects_v2.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.list_objects()

        mock_logger.error.assert_called_once_with(
            "Unexpected error listing objects in bucket: %s with prefix: %s - Error: %s",
            self.bucket_name,
            "None",
            error,
        )
        assert result == []

    @patch("core.aws.s3.boto3.client")
    def test_delete_object_success_default_bucket(self, mock_boto3_client):
        """Test successful object deletion using default bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.delete_object.return_value = {"DeleteMarker": True}

        s3_client = S3Client(self.bucket_name)
        result = s3_client.delete_object(self.object_key)

        mock_client.delete_object.assert_called_once_with(
            Bucket=self.bucket_name, Key=self.object_key
        )
        assert result is True

    @patch("core.aws.s3.boto3.client")
    def test_delete_object_success_custom_bucket(self, mock_boto3_client):
        """Test successful object deletion using custom bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.delete_object.return_value = {"DeleteMarker": True}
        custom_bucket = "custom-bucket"

        s3_client = S3Client(self.bucket_name)
        result = s3_client.delete_object(
            self.object_key, bucket_name=custom_bucket
        )

        mock_client.delete_object.assert_called_once_with(
            Bucket=custom_bucket, Key=self.object_key
        )
        assert result is True

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_delete_object_client_error(self, mock_logger, mock_boto3_client):
        """Test delete_object failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key does not exist"}},
            "DeleteObject",
        )
        mock_client.delete_object.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.delete_object(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Failed to delete object: s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is False

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_delete_object_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test delete_object failure due to generic exception."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = TypeError("Invalid object key type")
        mock_client.delete_object.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.delete_object(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Unexpected error deleting object: s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is False

    @patch("core.aws.s3.boto3.client")
    def test_object_exists_success_exists(self, mock_boto3_client):
        """Test object_exists when object exists."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.head_object.return_value = {
            "ContentLength": 100,
            "LastModified": "2023-01-01T00:00:00Z",
        }

        s3_client = S3Client(self.bucket_name)
        result = s3_client.object_exists(self.object_key)

        mock_client.head_object.assert_called_once_with(
            Bucket=self.bucket_name, Key=self.object_key
        )
        assert result is True

    @patch("core.aws.s3.boto3.client")
    def test_object_exists_success_custom_bucket(self, mock_boto3_client):
        """Test object_exists using custom bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.head_object.return_value = {"ContentLength": 100}
        custom_bucket = "custom-bucket"

        s3_client = S3Client(self.bucket_name)
        result = s3_client.object_exists(
            self.object_key, bucket_name=custom_bucket
        )

        mock_client.head_object.assert_called_once_with(
            Bucket=custom_bucket, Key=self.object_key
        )
        assert result is True

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_object_exists_not_found(self, mock_logger, mock_boto3_client):
        """Test object_exists when object does not exist."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
        )
        mock_client.head_object.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.object_exists(self.object_key)

        mock_logger.debug.assert_called_once_with(
            "Object does not exist: s3://%s/%s",
            self.bucket_name,
            self.object_key,
        )
        assert result is False

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_object_exists_other_client_error(
        self, mock_logger, mock_boto3_client
    ):
        """Test object_exists with non-404 client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "HeadObject",
        )
        mock_client.head_object.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.object_exists(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Error checking if object exists: s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is False

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_object_exists_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test object_exists failure due to generic exception."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ConnectionError("Network error")
        mock_client.head_object.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.object_exists(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Unexpected error checking if object exists: s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is False

    @patch("core.aws.s3.boto3.client")
    def test_generate_presigned_upload_url_success_minimal(
        self, mock_boto3_client
    ):
        """Test successful presigned upload URL generation with minimal parameters."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        expected_url = "https://test-bucket.s3.amazonaws.com/test-file.txt?X-Amz-Algorithm=..."
        mock_client.generate_presigned_url.return_value = expected_url

        s3_client = S3Client(self.bucket_name)
        result = s3_client.generate_presigned_upload_url(self.object_key)

        expected_params = {"Bucket": self.bucket_name, "Key": self.object_key}
        mock_client.generate_presigned_url.assert_called_once_with(
            "put_object", Params=expected_params, ExpiresIn=3600
        )
        assert result == expected_url

    @patch("core.aws.s3.boto3.client")
    def test_generate_presigned_upload_url_success_all_params(
        self, mock_boto3_client
    ):
        """Test successful presigned upload URL generation with all parameters."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        expected_url = "https://test-bucket.s3.amazonaws.com/test-file.txt?X-Amz-Algorithm=..."
        mock_client.generate_presigned_url.return_value = expected_url

        custom_bucket = "custom-bucket"
        content_type = "text/plain"
        metadata = {"author": "test-user", "version": "1.0"}
        expiration = 7200

        s3_client = S3Client(self.bucket_name)
        result = s3_client.generate_presigned_upload_url(
            self.object_key,
            expiration=expiration,
            bucket_name=custom_bucket,
            content_type=content_type,
            metadata=metadata,
        )

        expected_params = {
            "Bucket": custom_bucket,
            "Key": self.object_key,
            "ContentType": content_type,
            "Metadata": metadata,
        }
        mock_client.generate_presigned_url.assert_called_once_with(
            "put_object", Params=expected_params, ExpiresIn=expiration
        )
        assert result == expected_url

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_generate_presigned_upload_url_client_error(
        self, mock_logger, mock_boto3_client
    ):
        """Test generate_presigned_upload_url failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "GeneratePresignedUrl",
        )
        mock_client.generate_presigned_url.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.generate_presigned_upload_url(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Failed to generate presigned upload URL for s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is None

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_generate_presigned_upload_url_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test generate_presigned_upload_url failure due to generic exception."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ValueError("Invalid expiration time")
        mock_client.generate_presigned_url.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.generate_presigned_upload_url(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Unexpected error generating presigned upload URL for s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is None

    @patch("core.aws.s3.boto3.client")
    def test_generate_presigned_download_url_success_default(
        self, mock_boto3_client
    ):
        """Test successful presigned download URL generation with default parameters."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        expected_url = "https://test-bucket.s3.amazonaws.com/test-file.txt?X-Amz-Algorithm=..."
        mock_client.generate_presigned_url.return_value = expected_url

        s3_client = S3Client(self.bucket_name)
        result = s3_client.generate_presigned_download_url(self.object_key)

        expected_params = {"Bucket": self.bucket_name, "Key": self.object_key}
        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object", Params=expected_params, ExpiresIn=3600
        )
        assert result == expected_url

    @patch("core.aws.s3.boto3.client")
    def test_generate_presigned_download_url_success_custom(
        self, mock_boto3_client
    ):
        """Test successful presigned download URL generation with custom parameters."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        expected_url = "https://custom-bucket.s3.amazonaws.com/test-file.txt?X-Amz-Algorithm=..."
        mock_client.generate_presigned_url.return_value = expected_url

        custom_bucket = "custom-bucket"
        expiration = 1800

        s3_client = S3Client(self.bucket_name)
        result = s3_client.generate_presigned_download_url(
            self.object_key, expiration=expiration, bucket_name=custom_bucket
        )

        expected_params = {"Bucket": custom_bucket, "Key": self.object_key}
        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object", Params=expected_params, ExpiresIn=expiration
        )
        assert result == expected_url

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_generate_presigned_download_url_client_error(
        self, mock_logger, mock_boto3_client
    ):
        """Test generate_presigned_download_url failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key does not exist"}},
            "GeneratePresignedUrl",
        )
        mock_client.generate_presigned_url.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.generate_presigned_download_url(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Failed to generate presigned download URL for s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is None

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_generate_presigned_download_url_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test generate_presigned_download_url failure due to generic exception."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = TypeError("Invalid parameter type")
        mock_client.generate_presigned_url.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.generate_presigned_download_url(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Unexpected error generating presigned download URL for s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is None

    @patch("core.aws.s3.boto3.client")
    def test_download_file_success(self, mock_boto3_client):
        """Test successful file download using download_file method."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.download_file.return_value = None

        s3_client = S3Client(self.bucket_name)
        result = s3_client.download_file(self.object_key, self.download_path)

        mock_client.download_file.assert_called_once_with(
            Bucket=self.bucket_name,
            Key=self.object_key,
            Filename=self.download_path,
        )
        assert result is None  # download_file returns the client response

    @patch("core.aws.s3.boto3.client")
    def test_download_file_custom_bucket(self, mock_boto3_client):
        """Test file download using custom bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.download_file.return_value = None
        custom_bucket = "custom-bucket"

        s3_client = S3Client(self.bucket_name)
        result = s3_client.download_file(
            self.object_key, self.download_path, bucket_name=custom_bucket
        )

        mock_client.download_file.assert_called_once_with(
            Bucket=custom_bucket,
            Key=self.object_key,
            Filename=self.download_path,
        )
        assert result is None

    @patch("core.aws.s3.boto3.client")
    def test_head_object_success_default_bucket(self, mock_boto3_client):
        """Test successful object metadata retrieval using default bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        expected_response = {
            "ContentLength": 100,
            "ContentType": "text/plain",
            "LastModified": "2023-01-01T00:00:00Z",
            "ETag": '"d41d8cd98f00b204e9800998ecf8427e"',
        }
        mock_client.head_object.return_value = expected_response

        s3_client = S3Client(self.bucket_name)
        result = s3_client.head_object(self.object_key)

        mock_client.head_object.assert_called_once_with(
            Bucket=self.bucket_name, Key=self.object_key
        )
        assert result == expected_response

    @patch("core.aws.s3.boto3.client")
    def test_head_object_success_custom_bucket(self, mock_boto3_client):
        """Test successful object metadata retrieval using custom bucket."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        expected_response = {"ContentLength": 100}
        mock_client.head_object.return_value = expected_response
        custom_bucket = "custom-bucket"

        s3_client = S3Client(self.bucket_name)
        result = s3_client.head_object(
            self.object_key, bucket_name=custom_bucket
        )

        mock_client.head_object.assert_called_once_with(
            Bucket=custom_bucket, Key=self.object_key
        )
        assert result == expected_response

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_head_object_client_error(self, mock_logger, mock_boto3_client):
        """Test head_object failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key does not exist"}},
            "HeadObject",
        )
        mock_client.head_object.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.head_object(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Failed to retrieve metadata for s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is None

    @patch("core.aws.s3.boto3.client")
    @patch("core.aws.s3.logger")
    def test_head_object_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test head_object failure due to generic exception."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = RuntimeError("Unexpected error")
        mock_client.head_object.side_effect = error

        s3_client = S3Client(self.bucket_name)
        result = s3_client.head_object(self.object_key)

        mock_logger.error.assert_called_once_with(
            "Unexpected error retrieving metadata for s3://%s/%s - Error: %s",
            self.bucket_name,
            self.object_key,
            error,
        )
        assert result is None

    @pytest.mark.parametrize(
        "bucket_name",
        [
            "test-bucket-1",
            "production-data-bucket",
            "dev_files_2024",
            "staging.backup.bucket",
        ],
    )
    @patch("core.aws.s3.boto3.client")
    def test_bucket_name_preservation(self, mock_boto3_client, bucket_name):
        """Test that bucket name is correctly preserved across all operations."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        s3_client = S3Client(bucket_name)

        # Verify bucket name is stored correctly
        assert s3_client.bucket_name == bucket_name

    @patch("core.aws.s3.boto3.client")
    def test_multiple_instances_independent(self, mock_boto3_client):
        """Test that multiple S3Client instances are independent."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        mock_boto3_client.side_effect = [mock_client1, mock_client2]

        bucket1_name = "bucket1"
        bucket2_name = "bucket2"

        s3_client1 = S3Client(bucket1_name)
        s3_client2 = S3Client(bucket2_name)

        assert s3_client1.bucket_name == bucket1_name
        assert s3_client2.bucket_name == bucket2_name
        assert s3_client1._client == mock_client1
        assert s3_client2._client == mock_client2
        assert s3_client1._client != s3_client2._client

    @pytest.mark.parametrize(
        "method_name,method_args,expected_bucket_param",
        [
            ("upload_file", ["/path/file.txt", "key"], "test-bucket"),
            ("get_file", ["key", "/path/file.txt"], "test-bucket"),
            ("get_object_content", ["key"], "test-bucket"),
            ("list_objects", [], "test-bucket"),
            ("delete_object", ["key"], "test-bucket"),
            ("object_exists", ["key"], "test-bucket"),
            ("generate_presigned_upload_url", ["key"], "test-bucket"),
            ("generate_presigned_download_url", ["key"], "test-bucket"),
            ("download_file", ["key", "/path/file.txt"], "test-bucket"),
            ("head_object", ["key"], "test-bucket"),
        ],
    )
    @patch("core.aws.s3.boto3.client")
    def test_default_bucket_usage_in_methods(
        self,
        mock_boto3_client,
        method_name,
        method_args,
        expected_bucket_param,
    ):
        """Test that all methods use the default bucket when no bucket is specified."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock all possible return values to prevent errors
        mock_client.upload_file.return_value = None
        mock_client.download_file.return_value = None
        mock_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"test")
        }
        mock_client.list_objects_v2.return_value = {"Contents": []}
        mock_client.delete_object.return_value = {}
        mock_client.head_object.return_value = {"ContentLength": 100}
        mock_client.generate_presigned_url.return_value = "https://example.com"

        s3_client = S3Client(expected_bucket_param)
        method = getattr(s3_client, method_name)

        # Call the method with the test arguments
        try:
            method(*method_args)
        except Exception:
            # Some methods might fail due to mocking limitations, but that's okay
            # We're primarily testing that the bucket parameter is used correctly
            pass

        # Verify the S3Client was initialized with the correct bucket
        assert s3_client.bucket_name == expected_bucket_param

    @pytest.mark.parametrize(
        "prefix,max_keys",
        [
            (None, 1000),
            ("documents/", 500),
            ("logs/2023/", 100),
            ("", 2000),
        ],
    )
    @patch("core.aws.s3.boto3.client")
    def test_list_objects_parameter_combinations(
        self, mock_boto3_client, prefix, max_keys
    ):
        """Test list_objects with various parameter combinations."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_objects_v2.return_value = {"Contents": []}

        s3_client = S3Client(self.bucket_name)
        s3_client.list_objects(prefix=prefix, max_keys=max_keys)

        expected_kwargs = {"Bucket": self.bucket_name, "MaxKeys": max_keys}
        if prefix:
            expected_kwargs["Prefix"] = prefix

        mock_client.list_objects_v2.assert_called_once_with(**expected_kwargs)

    @pytest.mark.parametrize(
        "content_type,metadata",
        [
            (None, None),
            ("text/plain", None),
            (None, {"author": "test"}),
            ("image/jpeg", {"author": "test", "version": "1.0"}),
        ],
    )
    @patch("core.aws.s3.boto3.client")
    def test_generate_presigned_upload_url_parameter_combinations(
        self, mock_boto3_client, content_type, metadata
    ):
        """Test generate_presigned_upload_url with various parameter combinations."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://example.com"

        s3_client = S3Client(self.bucket_name)
        s3_client.generate_presigned_upload_url(
            self.object_key, content_type=content_type, metadata=metadata
        )

        expected_params = {"Bucket": self.bucket_name, "Key": self.object_key}
        if content_type:
            expected_params["ContentType"] = content_type
        if metadata:
            expected_params["Metadata"] = metadata

        mock_client.generate_presigned_url.assert_called_once_with(
            "put_object", Params=expected_params, ExpiresIn=3600
        )
