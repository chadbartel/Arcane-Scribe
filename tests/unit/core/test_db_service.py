"""Unit tests for the db_service module."""

# Standard Library
from datetime import timezone
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from boto3.dynamodb.conditions import Key

# Local Modules
from core.services.db_service import DatabaseService
from core.utils import DocumentProcessingStatus


class TestDatabaseService:
    """Test cases for the DatabaseService class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.table_name = "test-documents-table"
        self.mock_dynamodb = MagicMock()

    @patch("core.services.db_service.DynamoDb")
    def test_init_success(self, mock_dynamodb_class):
        """Test successful initialization of DatabaseService."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance

        # Act
        db_service = DatabaseService(self.table_name)

        # Assert
        mock_dynamodb_class.assert_called_once_with(table_name=self.table_name)
        assert db_service.dynamodb == mock_dynamodb_instance

    @patch("core.services.db_service.DynamoDb")
    @patch("core.services.db_service.uuid.uuid4")
    @patch("core.services.db_service.datetime")
    def test_create_document_record_success_with_generated_id(
        self, mock_datetime, mock_uuid4, mock_dynamodb_class
    ):
        """Test successful creation of document record with generated document ID."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance

        mock_uuid = "test-uuid-123"
        mock_uuid4.return_value = MagicMock(spec=str)
        mock_uuid4.return_value.__str__ = lambda x: mock_uuid

        mock_timestamp = "2023-06-19T10:30:00.000000+00:00"
        mock_datetime_instance = MagicMock()
        mock_datetime_instance.isoformat.return_value = mock_timestamp
        mock_datetime.now.return_value = mock_datetime_instance

        db_service = DatabaseService(self.table_name)

        # Act
        result = db_service.create_document_record(
            owner_id="test_user",
            srd_id="test_srd",
            file_name="test.pdf",
            s3_key="documents/test.pdf",
            content_type="application/pdf",
        )

        # Assert
        expected_item = {
            "owner_srd_composite": "test_user#test_srd",
            "document_id": mock_uuid,
            "original_file_name": "test.pdf",
            "s3_key": "documents/test.pdf",
            "content_type": "application/pdf",
            "upload_timestamp": mock_timestamp,
            "processing_status": DocumentProcessingStatus.pending.value,
        }

        mock_dynamodb_instance.put_item.assert_called_once_with(
            item=expected_item
        )
        assert result == expected_item
        mock_datetime.now.assert_called_once_with(timezone.utc)

    @patch("core.services.db_service.DynamoDb")
    @patch("core.services.db_service.datetime")
    def test_create_document_record_success_with_provided_id(
        self, mock_datetime, mock_dynamodb_class
    ):
        """Test successful creation of document record with provided document ID."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance

        mock_timestamp = "2023-06-19T10:30:00.000000+00:00"
        mock_datetime_instance = MagicMock()
        mock_datetime_instance.isoformat.return_value = mock_timestamp
        mock_datetime.now.return_value = mock_datetime_instance

        db_service = DatabaseService(self.table_name)
        provided_document_id = "custom-document-id"

        # Act
        result = db_service.create_document_record(
            owner_id="test_user",
            srd_id="test_srd",
            file_name="test.pdf",
            s3_key="documents/test.pdf",
            content_type="application/pdf",
            document_id=provided_document_id,
        )

        # Assert
        expected_item = {
            "owner_srd_composite": "test_user#test_srd",
            "document_id": provided_document_id,
            "original_file_name": "test.pdf",
            "s3_key": "documents/test.pdf",
            "content_type": "application/pdf",
            "upload_timestamp": mock_timestamp,
            "processing_status": DocumentProcessingStatus.pending.value,
        }

        mock_dynamodb_instance.put_item.assert_called_once_with(
            item=expected_item
        )
        assert result == expected_item

    @patch("core.services.db_service.DynamoDb")
    def test_create_document_record_various_content_types(
        self, mock_dynamodb_class
    ):
        """Test creation with various content types."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance
        db_service = DatabaseService(self.table_name)

        test_cases = [
            "application/pdf",
            "image/png",
            "image/jpeg",
            "text/plain",
            "application/zip",
        ]

        for content_type in test_cases:
            # Act
            with patch("core.services.db_service.datetime") as mock_datetime:
                mock_datetime.now.return_value.isoformat.return_value = (
                    "test_timestamp"
                )
                result = db_service.create_document_record(
                    owner_id="test_user",
                    srd_id="test_srd",
                    file_name=f"test.{content_type.split('/')[-1]}",
                    s3_key=f"documents/test.{content_type.split('/')[-1]}",
                    content_type=content_type,
                )

            # Assert
            assert result["content_type"] == content_type

    @patch("core.services.db_service.DynamoDb")
    def test_get_document_record_success(self, mock_dynamodb_class):
        """Test successful retrieval of document record."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance

        expected_record = {
            "owner_srd_composite": "test_user#test_srd",
            "document_id": "test_doc_id",
            "original_file_name": "test.pdf",
            "s3_key": "documents/test.pdf",
            "content_type": "application/pdf",
            "upload_timestamp": "2023-06-19T10:30:00.000000+00:00",
            "processing_status": "pending",
        }
        mock_dynamodb_instance.get_item.return_value = expected_record

        db_service = DatabaseService(self.table_name)

        # Act
        result = db_service.get_document_record(
            owner_id="test_user", srd_id="test_srd", document_id="test_doc_id"
        )

        # Assert
        mock_dynamodb_instance.get_item.assert_called_once_with(
            key={
                "owner_srd_composite": "test_user#test_srd",
                "document_id": "test_doc_id",
            }
        )
        assert result == expected_record

    @patch("core.services.db_service.DynamoDb")
    def test_get_document_record_not_found(self, mock_dynamodb_class):
        """Test retrieval when document record is not found."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance
        mock_dynamodb_instance.get_item.return_value = None

        db_service = DatabaseService(self.table_name)

        # Act
        result = db_service.get_document_record(
            owner_id="test_user",
            srd_id="test_srd",
            document_id="nonexistent_doc",
        )

        # Assert
        assert result is None

    @patch("core.services.db_service.DynamoDb")
    def test_delete_document_record_success(self, mock_dynamodb_class):
        """Test successful deletion of document record."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance

        expected_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        mock_dynamodb_instance.delete_item.return_value = expected_response

        db_service = DatabaseService(self.table_name)

        # Act
        result = db_service.delete_document_record(
            owner_id="test_user", srd_id="test_srd", document_id="test_doc_id"
        )

        # Assert
        mock_dynamodb_instance.delete_item.assert_called_once_with(
            key={
                "owner_srd_composite": "test_user#test_srd",
                "document_id": "test_doc_id",
            }
        )
        assert result == expected_response

    @patch("core.services.db_service.DynamoDb")
    def test_list_document_records_success(self, mock_dynamodb_class):
        """Test successful listing of document records."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance

        expected_records = {
            "Items": [
                {
                    "owner_srd_composite": "test_user#test_srd",
                    "document_id": "doc1",
                    "original_file_name": "test1.pdf",
                },
                {
                    "owner_srd_composite": "test_user#test_srd",
                    "document_id": "doc2",
                    "original_file_name": "test2.pdf",
                },
            ],
            "Count": 2,
            "ScannedCount": 2,
        }
        mock_dynamodb_instance.query.return_value = expected_records

        db_service = DatabaseService(self.table_name)

        # Act
        result = db_service.list_document_records(
            owner_id="test_user", srd_id="test_srd"
        )

        # Assert
        mock_dynamodb_instance.query.assert_called_once_with(
            key_condition_expression=Key("owner_srd_composite").eq(
                "test_user#test_srd"
            )
        )
        assert result == expected_records

    @patch("core.services.db_service.DynamoDb")
    def test_list_document_records_empty(self, mock_dynamodb_class):
        """Test listing when no document records exist."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance

        empty_response = {"Items": [], "Count": 0, "ScannedCount": 0}
        mock_dynamodb_instance.query.return_value = empty_response

        db_service = DatabaseService(self.table_name)

        # Act
        result = db_service.list_document_records(
            owner_id="test_user", srd_id="test_srd"
        )

        # Assert
        assert result == empty_response

    @patch("core.services.db_service.DynamoDb")
    def test_update_document_record_success(self, mock_dynamodb_class):
        """Test successful update of document record."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance

        expected_response = {
            "Attributes": {
                "owner_srd_composite": "test_user#test_srd",
                "document_id": "test_doc_id",
                "processing_status": "completed",
            }
        }
        mock_dynamodb_instance.update_item.return_value = expected_response

        db_service = DatabaseService(self.table_name)
        update_map = {
            "processing_status": "completed",
            "processed_timestamp": "2023-06-19T11:00:00",
        }

        # Act
        result = db_service.update_document_record(
            owner_id="test_user",
            srd_id="test_srd",
            document_id="test_doc_id",
            update_map=update_map,
        )

        # Assert
        mock_dynamodb_instance.update_item.assert_called_once_with(
            key={
                "owner_srd_composite": "test_user#test_srd",
                "document_id": "test_doc_id",
            },
            update_expression="SET processing_status = :processing_status, processed_timestamp = :processed_timestamp",
            expression_attribute_values={
                ":processing_status": "completed",
                ":processed_timestamp": "2023-06-19T11:00:00",
            },
        )
        assert result == expected_response

    @patch("core.services.db_service.DynamoDb")
    def test_update_document_record_single_field(self, mock_dynamodb_class):
        """Test update with single field."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance
        mock_dynamodb_instance.update_item.return_value = {
            "UpdatedAttributes": {}
        }

        db_service = DatabaseService(self.table_name)
        update_map = {"processing_status": "failed"}

        # Act
        db_service.update_document_record(
            owner_id="test_user",
            srd_id="test_srd",
            document_id="test_doc_id",
            update_map=update_map,
        )

        # Assert
        mock_dynamodb_instance.update_item.assert_called_once_with(
            key={
                "owner_srd_composite": "test_user#test_srd",
                "document_id": "test_doc_id",
            },
            update_expression="SET processing_status = :processing_status",
            expression_attribute_values={":processing_status": "failed"},
        )

    @patch("core.services.db_service.DynamoDb")
    def test_update_document_record_empty_update_map(
        self, mock_dynamodb_class
    ):
        """Test update with empty update map."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance
        mock_dynamodb_instance.update_item.return_value = {}

        db_service = DatabaseService(self.table_name)
        update_map = {}

        # Act
        result = db_service.update_document_record(
            owner_id="test_user",
            srd_id="test_srd",
            document_id="test_doc_id",
            update_map=update_map,
        )

        # Assert
        mock_dynamodb_instance.update_item.assert_called_once_with(
            key={
                "owner_srd_composite": "test_user#test_srd",
                "document_id": "test_doc_id",
            },
            update_expression="SET ",
            expression_attribute_values={},
        )
        assert result == {}

    @patch("core.services.db_service.DynamoDb")
    def test_delete_all_document_records_success(self, mock_dynamodb_class):
        """Test successful deletion of all document records."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance

        # Mock the list_document_records call
        mock_records = {
            "Items": [
                {"document_id": "doc1"},
                {"document_id": "doc2"},
                {"document_id": "doc3"},
            ]
        }

        db_service = DatabaseService(self.table_name)
        # Mock the list_document_records method on the instance
        db_service.list_document_records = MagicMock(return_value=mock_records)

        # Act
        result = db_service.delete_all_document_records(
            owner_id="test_user", srd_id="test_srd"
        )

        # Assert
        db_service.list_document_records.assert_called_once_with(
            owner_id="test_user", srd_id="test_srd"
        )

        # Verify delete_item was called for each document
        assert mock_dynamodb_instance.delete_item.call_count == 3

        # Check all delete calls
        expected_calls = [
            {
                "key": {
                    "owner_srd_composite": "test_user#test_srd",
                    "document_id": "doc1",
                }
            },
            {
                "key": {
                    "owner_srd_composite": "test_user#test_srd",
                    "document_id": "doc2",
                }
            },
            {
                "key": {
                    "owner_srd_composite": "test_user#test_srd",
                    "document_id": "doc3",
                }
            },
        ]

        for expected_call in expected_calls:
            mock_dynamodb_instance.delete_item.assert_any_call(**expected_call)

        assert result == {
            "message": "All document records deleted successfully."
        }

    @patch("core.services.db_service.DynamoDb")
    def test_delete_all_document_records_no_records(self, mock_dynamodb_class):
        """Test deletion when no document records exist."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance

        # Mock empty list response
        empty_records = {"Items": []}

        db_service = DatabaseService(self.table_name)
        db_service.list_document_records = MagicMock(
            return_value=empty_records
        )

        # Act
        result = db_service.delete_all_document_records(
            owner_id="test_user", srd_id="test_srd"
        )

        # Assert
        db_service.list_document_records.assert_called_once_with(
            owner_id="test_user", srd_id="test_srd"
        )
        mock_dynamodb_instance.delete_item.assert_not_called()
        assert result == {"message": "No document records found to delete."}

    @pytest.mark.parametrize(
        "owner_id,srd_id,expected_composite",
        [
            ("user1", "srd1", "user1#srd1"),
            (
                "user@example.com",
                "project-123",
                "user@example.com#project-123",
            ),
            ("123", "456", "123#456"),
            (
                "user_with_underscores",
                "srd-with-hyphens",
                "user_with_underscores#srd-with-hyphens",
            ),
            ("", "srd", "#srd"),
            ("user", "", "user#"),
        ],
    )
    @patch("core.services.db_service.DynamoDb")
    def test_composite_key_generation(
        self, mock_dynamodb_class, owner_id, srd_id, expected_composite
    ):
        """Test composite key generation with various owner_id and srd_id combinations."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance
        db_service = DatabaseService(self.table_name)

        # Act
        db_service.get_document_record(
            owner_id=owner_id, srd_id=srd_id, document_id="test_doc"
        )

        # Assert
        mock_dynamodb_instance.get_item.assert_called_once_with(
            key={
                "owner_srd_composite": expected_composite,
                "document_id": "test_doc",
            }
        )

    @patch("core.services.db_service.DynamoDb")
    def test_document_processing_status_enum_usage(self, mock_dynamodb_class):
        """Test that DocumentProcessingStatus enum is used correctly."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance
        db_service = DatabaseService(self.table_name)

        # Act
        with patch("core.services.db_service.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = (
                "test_timestamp"
            )
            result = db_service.create_document_record(
                owner_id="test_user",
                srd_id="test_srd",
                file_name="test.pdf",
                s3_key="documents/test.pdf",
                content_type="application/pdf",
            )

        # Assert
        assert (
            result["processing_status"]
            == DocumentProcessingStatus.pending.value
        )
        assert result["processing_status"] == "pending"

    @patch("core.services.db_service.DynamoDb")
    def test_methods_preserve_parameters(self, mock_dynamodb_class):
        """Test that all methods correctly preserve and use their parameters."""
        # Arrange
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_class.return_value = mock_dynamodb_instance
        db_service = DatabaseService(self.table_name)

        test_params = {
            "owner_id": "special_user_123",
            "srd_id": "special_srd_456",
            "document_id": "special_doc_789",
            "file_name": "special_file.pdf",
            "s3_key": "special/path/file.pdf",
            "content_type": "application/pdf",
        }

        # Test each method preserves parameters correctly

        # Test create_document_record
        with patch("core.services.db_service.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = (
                "test_timestamp"
            )
            result = db_service.create_document_record(
                owner_id=test_params["owner_id"],
                srd_id=test_params["srd_id"],
                file_name=test_params["file_name"],
                s3_key=test_params["s3_key"],
                content_type=test_params["content_type"],
                document_id=test_params["document_id"],
            )
            assert (
                result["owner_srd_composite"]
                == f"{test_params['owner_id']}#{test_params['srd_id']}"
            )
            assert result["document_id"] == test_params["document_id"]
            assert result["original_file_name"] == test_params["file_name"]
            assert result["s3_key"] == test_params["s3_key"]
            assert result["content_type"] == test_params["content_type"]

        # Test get_document_record
        db_service.get_document_record(
            owner_id=test_params["owner_id"],
            srd_id=test_params["srd_id"],
            document_id=test_params["document_id"],
        )

        mock_dynamodb_instance.get_item.assert_called_with(
            key={
                "owner_srd_composite": f"{test_params['owner_id']}#{test_params['srd_id']}",
                "document_id": test_params["document_id"],
            }
        )
