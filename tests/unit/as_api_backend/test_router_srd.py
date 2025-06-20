"""Unit tests for the srd router module."""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from fastapi import status

# Local Modules
from core.utils import DocumentProcessingStatus
from api_backend.models import (
    User,
    PresignedUrlRequest,
)


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return User(
        username="test_user", email="test@example.com", groups=["users"]
    )


@pytest.fixture
def mock_db_service():
    """Create a mock database service."""
    mock_service = MagicMock()
    mock_service.create_document_record.return_value = None
    mock_service.get_document_record.return_value = {
        "document_id": "test-doc-id",
        "s3_key": "test_user/test_srd/test-doc-id/test.pdf",
        "file_name": "test.pdf",
        "content_type": "application/pdf",
        "processing_status": DocumentProcessingStatus.completed.value,
    }
    mock_service.list_document_records.return_value = {
        "Items": [
            {
                "document_id": "test-doc-id-1",
                "file_name": "test1.pdf",
                "processing_status": DocumentProcessingStatus.completed.value,
            },
            {
                "document_id": "test-doc-id-2",
                "file_name": "test2.pdf",
                "processing_status": DocumentProcessingStatus.processing.value,
            },
        ]
    }
    mock_service.delete_document_record.return_value = None
    mock_service.delete_all_document_records.return_value = {"deleted": 2}
    return mock_service


@pytest.fixture
def mock_s3_client_docs():
    """Create a mock S3 client for documents."""
    mock_client = MagicMock()
    mock_client.generate_presigned_upload_url.return_value = (
        "https://test-bucket.s3.amazonaws.com/presigned-url"
    )
    mock_client.delete_object.return_value = None
    mock_client.list_objects.return_value = [
        {"Key": "test_user/test_srd/doc1/file1.pdf"},
        {"Key": "test_user/test_srd/doc2/file2.pdf"},
    ]
    return mock_client


@pytest.fixture
def mock_s3_client_vectors():
    """Create a mock S3 client for vector store."""
    mock_client = MagicMock()
    mock_client.delete_object.return_value = None
    mock_client.list_objects.return_value = [
        {"Key": "test_user/test_srd/vector_store/doc1.faiss"},
        {"Key": "test_user/test_srd/vector_store/doc1.pkl"},
        {"Key": "test_user/test_srd/vector_store/doc2.faiss"},
        {"Key": "test_user/test_srd/vector_store/doc2.pkl"},
    ]
    return mock_client


@pytest.fixture
def srd_router_with_mocks(
    mock_db_service, mock_s3_client_docs, mock_s3_client_vectors
):
    """Create SRD router with mocked dependencies."""
    with patch("api_backend.routers.srd.db_service", mock_db_service):
        with patch(
            "api_backend.routers.srd.s3_client_docs", mock_s3_client_docs
        ):
            with patch(
                "api_backend.routers.srd.s3_client_vectors",
                mock_s3_client_vectors,
            ):
                # Local Modules
                from api_backend.routers import srd

                yield srd


class TestGetPresignedUploadUrl:
    """Test cases for the get_presigned_upload_url endpoint."""

    def test_get_presigned_upload_url_success(
        self,
        srd_router_with_mocks,
        mock_user,
        mock_db_service,
        mock_s3_client_docs,
    ):
        """Test successful presigned URL generation."""
        # Arrange
        srd_id = "test_srd"
        request = PresignedUrlRequest(
            file_name="test_document.pdf", content_type="application/pdf"
        )

        # Act
        with patch("api_backend.routers.srd.uuid4") as mock_uuid:
            mock_uuid.return_value = "test-doc-uuid"
            response = srd_router_with_mocks.get_presigned_upload_url(
                srd_id=srd_id, current_user=mock_user, request=request
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "presigned_url" in response.body.decode()
        assert "test-doc-uuid" in response.body.decode()

        # Verify S3 client was called correctly
        mock_s3_client_docs.generate_presigned_upload_url.assert_called_once()
        call_args = mock_s3_client_docs.generate_presigned_upload_url.call_args
        assert (
            call_args[1]["object_key"]
            == "test_user/test_srd/test-doc-uuid/test_document.pdf"
        )
        assert call_args[1]["content_type"] == "application/pdf"
        assert call_args[1]["expiration"] == 900

        # Verify database record creation
        mock_db_service.create_document_record.assert_called_once()
        db_call_args = mock_db_service.create_document_record.call_args
        assert db_call_args[1]["owner_id"] == "test_user"
        assert db_call_args[1]["srd_id"] == "test_srd"
        assert db_call_args[1]["file_name"] == "test_document.pdf"
        assert db_call_args[1]["document_id"] == "test-doc-uuid"

    def test_get_presigned_upload_url_with_default_content_type(
        self, srd_router_with_mocks, mock_user, mock_s3_client_docs
    ):
        """Test presigned URL generation with default content type."""
        # Arrange
        srd_id = "test_srd"
        request = PresignedUrlRequest(file_name="test_document.pdf")

        # Act
        with patch("api_backend.routers.srd.uuid4") as mock_uuid:
            mock_uuid.return_value = "test-doc-uuid"
            response = srd_router_with_mocks.get_presigned_upload_url(
                srd_id=srd_id, current_user=mock_user, request=request
            )  # Assert
        assert response.status_code == status.HTTP_200_OK
        call_args = mock_s3_client_docs.generate_presigned_upload_url.call_args
        assert call_args[1]["content_type"] == "application/pdf"

    def test_get_presigned_upload_url_empty_filename(
        self, srd_router_with_mocks, mock_user, mock_s3_client_docs
    ):
        """Test presigned URL generation with empty filename (should succeed)."""
        # Arrange
        srd_id = "test_srd"
        request = PresignedUrlRequest(
            file_name="", content_type="application/pdf"  # Empty filename
        )

        # Act
        with patch("api_backend.routers.srd.uuid4") as mock_uuid:
            mock_uuid.return_value = "test-doc-uuid"
            response = srd_router_with_mocks.get_presigned_upload_url(
                srd_id=srd_id, current_user=mock_user, request=request
            )

        # Assert - Empty filename is allowed, it gets stripped and passed to S3
        assert response.status_code == status.HTTP_200_OK
        assert "presigned_url" in response.body.decode()

        # Verify S3 client was called with empty filename
        mock_s3_client_docs.generate_presigned_upload_url.assert_called_once()
        call_args = mock_s3_client_docs.generate_presigned_upload_url.call_args
        assert (
            call_args[1]["object_key"] == "test_user/test_srd/test-doc-uuid/"
        )

    def test_get_presigned_upload_url_s3_error(
        self, srd_router_with_mocks, mock_user, mock_s3_client_docs
    ):
        """Test presigned URL generation with S3 error."""  # Arrange
        srd_id = "test_srd"
        request = PresignedUrlRequest(
            file_name="test_document.pdf", content_type="application/pdf"
        )
        mock_s3_client_docs.generate_presigned_upload_url.side_effect = (
            Exception("S3 error")
        )

        # Act
        with patch("api_backend.routers.srd.uuid4") as mock_uuid:
            mock_uuid.return_value = "test-doc-uuid"
            response = srd_router_with_mocks.get_presigned_upload_url(
                srd_id=srd_id, current_user=mock_user, request=request
            )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.body.decode()

    def test_get_presigned_upload_url_db_error(
        self, srd_router_with_mocks, mock_user, mock_db_service
    ):
        """Test presigned URL generation with database error."""  # Arrange
        srd_id = "test_srd"
        request = PresignedUrlRequest(
            file_name="test_document.pdf", content_type="application/pdf"
        )
        mock_db_service.create_document_record.side_effect = Exception(
            "DB error"
        )

        # Act
        with patch("api_backend.routers.srd.uuid4") as mock_uuid:
            mock_uuid.return_value = "test-doc-uuid"
            response = srd_router_with_mocks.get_presigned_upload_url(
                srd_id=srd_id, current_user=mock_user, request=request
            )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.body.decode()


class TestDeleteDocumentRecord:
    """Test cases for the delete_document_record endpoint."""

    def test_delete_document_record_success(
        self,
        srd_router_with_mocks,
        mock_user,
        mock_db_service,
        mock_s3_client_docs,
        mock_s3_client_vectors,
    ):
        """Test successful document deletion."""
        # Arrange
        srd_id = "test_srd"
        document_id = "test-doc-id"

        # Act
        response = srd_router_with_mocks.delete_document_record(
            srd_id=srd_id, document_id=document_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify database calls
        mock_db_service.get_document_record.assert_called_once_with(
            owner_id="test_user", srd_id="test_srd", document_id="test-doc-id"
        )
        mock_db_service.delete_document_record.assert_called_once_with(
            owner_id="test_user", srd_id="test_srd", document_id="test-doc-id"
        )

        # Verify S3 deletions
        mock_s3_client_docs.delete_object.assert_called_once_with(
            object_key="test_user/test_srd/test-doc-id/test.pdf"
        )
        assert mock_s3_client_vectors.delete_object.call_count == 2
        mock_s3_client_vectors.delete_object.assert_any_call(
            object_key="test_user/test_srd/vector_store/test-doc-id.faiss"
        )
        mock_s3_client_vectors.delete_object.assert_any_call(
            object_key="test_user/test_srd/vector_store/test-doc-id.pkl"
        )

    def test_delete_document_record_not_found(
        self, srd_router_with_mocks, mock_user, mock_db_service
    ):
        """Test deletion of non-existent document."""
        # Arrange
        srd_id = "test_srd"
        document_id = "nonexistent-doc-id"
        mock_db_service.get_document_record.return_value = None

        # Act
        response = srd_router_with_mocks.delete_document_record(
            srd_id=srd_id, document_id=document_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.body.decode()
        assert "Document not found" in response.body.decode()

    def test_delete_document_record_s3_docs_error(
        self, srd_router_with_mocks, mock_user, mock_s3_client_docs
    ):
        """Test deletion with S3 documents error."""
        # Arrange
        srd_id = "test_srd"
        document_id = "test-doc-id"
        mock_s3_client_docs.delete_object.side_effect = Exception("S3 error")

        # Act
        response = srd_router_with_mocks.delete_document_record(
            srd_id=srd_id, document_id=document_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.body.decode()

    def test_delete_document_record_s3_vectors_error(
        self, srd_router_with_mocks, mock_user, mock_s3_client_vectors
    ):
        """Test deletion with S3 vectors error."""
        # Arrange
        srd_id = "test_srd"
        document_id = "test-doc-id"
        mock_s3_client_vectors.delete_object.side_effect = Exception(
            "S3 vectors error"
        )

        # Act
        response = srd_router_with_mocks.delete_document_record(
            srd_id=srd_id, document_id=document_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.body.decode()

    def test_delete_document_record_db_error(
        self, srd_router_with_mocks, mock_user, mock_db_service
    ):
        """Test deletion with database error."""
        # Arrange
        srd_id = "test_srd"
        document_id = "test-doc-id"
        mock_db_service.delete_document_record.side_effect = Exception(
            "DB error"
        )

        # Act
        response = srd_router_with_mocks.delete_document_record(
            srd_id=srd_id, document_id=document_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.body.decode()


class TestDeleteAllDocumentRecords:
    """Test cases for the delete_all_document_records endpoint."""

    def test_delete_all_document_records_success(
        self,
        srd_router_with_mocks,
        mock_user,
        mock_db_service,
        mock_s3_client_docs,
        mock_s3_client_vectors,
    ):
        """Test successful deletion of all documents."""
        # Arrange
        srd_id = "test_srd"

        # Act
        response = srd_router_with_mocks.delete_all_document_records(
            srd_id=srd_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify S3 list operations
        mock_s3_client_docs.list_objects.assert_called_once_with(
            prefix="test_user/test_srd/"
        )
        mock_s3_client_vectors.list_objects.assert_called_once_with(
            prefix="test_user/test_srd/vector_store/"
        )

        # Verify S3 deletions - should delete all listed objects
        assert mock_s3_client_docs.delete_object.call_count == 2
        mock_s3_client_docs.delete_object.assert_any_call(
            object_key="test_user/test_srd/doc1/file1.pdf"
        )
        mock_s3_client_docs.delete_object.assert_any_call(
            object_key="test_user/test_srd/doc2/file2.pdf"
        )

        assert mock_s3_client_vectors.delete_object.call_count == 4

        # Verify database deletion
        mock_db_service.delete_all_document_records.assert_called_once_with(
            owner_id="test_user", srd_id="test_srd"
        )

    def test_delete_all_document_records_s3_docs_error(
        self, srd_router_with_mocks, mock_user, mock_s3_client_docs
    ):
        """Test deletion with S3 documents error."""
        # Arrange
        srd_id = "test_srd"
        mock_s3_client_docs.delete_object.side_effect = Exception("S3 error")

        # Act
        response = srd_router_with_mocks.delete_all_document_records(
            srd_id=srd_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.body.decode()

    def test_delete_all_document_records_s3_vectors_error(
        self, srd_router_with_mocks, mock_user, mock_s3_client_vectors
    ):
        """Test deletion with S3 vectors error."""
        # Arrange
        srd_id = "test_srd"
        mock_s3_client_vectors.delete_object.side_effect = Exception(
            "S3 vectors error"
        )

        # Act
        response = srd_router_with_mocks.delete_all_document_records(
            srd_id=srd_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.body.decode()

    def test_delete_all_document_records_db_error(
        self, srd_router_with_mocks, mock_user, mock_db_service
    ):
        """Test deletion with database error."""
        # Arrange
        srd_id = "test_srd"
        mock_db_service.delete_all_document_records.side_effect = Exception(
            "DB error"
        )

        # Act
        response = srd_router_with_mocks.delete_all_document_records(
            srd_id=srd_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.body.decode()

    def test_delete_all_document_records_no_objects(
        self,
        srd_router_with_mocks,
        mock_user,
        mock_s3_client_docs,
        mock_s3_client_vectors,
    ):
        """Test deletion when no objects exist."""
        # Arrange
        srd_id = "test_srd"
        mock_s3_client_docs.list_objects.return_value = []
        mock_s3_client_vectors.list_objects.return_value = []

        # Act
        response = srd_router_with_mocks.delete_all_document_records(
            srd_id=srd_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Should not call delete_object when no objects to delete
        mock_s3_client_docs.delete_object.assert_not_called()
        mock_s3_client_vectors.delete_object.assert_not_called()


class TestListDocumentRecords:
    """Test cases for the list_document_records endpoint."""

    def test_list_document_records_success(
        self, srd_router_with_mocks, mock_user, mock_db_service
    ):
        """Test successful listing of document records."""
        # Arrange
        srd_id = "test_srd"

        # Act
        response = srd_router_with_mocks.list_document_records(
            srd_id=srd_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Verify database call
        mock_db_service.list_document_records.assert_called_once_with(
            owner_id="test_user", srd_id="test_srd"
        )

        # Check response contains document records
        response_content = eval(
            response.body.decode()
        )  # Convert JSON string to dict
        assert len(response_content) == 2
        assert response_content[0]["document_id"] == "test-doc-id-1"
        assert response_content[1]["document_id"] == "test-doc-id-2"

    def test_list_document_records_no_documents_found(
        self, srd_router_with_mocks, mock_user, mock_db_service
    ):
        """Test listing when no documents exist."""
        # Arrange
        srd_id = "test_srd"
        mock_db_service.list_document_records.return_value = {"Items": []}

        # Act
        response = srd_router_with_mocks.list_document_records(
            srd_id=srd_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.body.decode()
        assert "No documents found" in response.body.decode()

    def test_list_document_records_missing_items_key(
        self, srd_router_with_mocks, mock_user, mock_db_service
    ):
        """Test listing when database response has no Items key."""
        # Arrange
        srd_id = "test_srd"
        mock_db_service.list_document_records.return_value = {}

        # Act
        response = srd_router_with_mocks.list_document_records(
            srd_id=srd_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.body.decode()


class TestGetDocumentRecord:
    """Test cases for the get_document_record endpoint."""

    def test_get_document_record_success(
        self, srd_router_with_mocks, mock_user, mock_db_service
    ):
        """Test successful retrieval of a document record."""
        # Arrange
        srd_id = "test_srd"
        document_id = "test-doc-id"

        # Act
        response = srd_router_with_mocks.get_document_record(
            srd_id=srd_id, document_id=document_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Verify database call
        mock_db_service.get_document_record.assert_called_once_with(
            owner_id="test_user", srd_id="test_srd", document_id="test-doc-id"
        )

        # Check response contains document record
        response_content = eval(response.body.decode())
        assert response_content["document_id"] == "test-doc-id"
        assert response_content["file_name"] == "test.pdf"

    def test_get_document_record_not_found(
        self, srd_router_with_mocks, mock_user, mock_db_service
    ):
        """Test retrieval of non-existent document record."""
        # Arrange
        srd_id = "test_srd"
        document_id = "nonexistent-doc-id"
        mock_db_service.get_document_record.return_value = None

        # Act
        response = srd_router_with_mocks.get_document_record(
            srd_id=srd_id, document_id=document_id, current_user=mock_user
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.body.decode()
        assert "Document not found" in response.body.decode()


class TestRouterIntegration:
    """Integration tests for the SRD router."""

    def test_router_endpoints_exist(self, srd_router_with_mocks):
        """Test that all expected endpoints exist in the router."""  # Get the router instance
        router = srd_router_with_mocks.router

        # Check that router has expected routes (including the /srd prefix)
        route_paths = [route.path for route in router.routes]

        assert "/srd/{srd_id}/documents/upload-url" in route_paths
        assert "/srd/{srd_id}/documents/{document_id}" in route_paths
        assert "/srd/{srd_id}/documents" in route_paths

    def test_router_methods(self, srd_router_with_mocks):
        """Test that routes have correct HTTP methods."""
        router = srd_router_with_mocks.router

        # Collect methods for each path
        path_methods = {}
        for route in router.routes:
            path = route.path
            if path not in path_methods:
                path_methods[path] = set()
            path_methods[path].update(route.methods)

        # Check expected methods for each path
        assert "POST" in path_methods.get(
            "/srd/{srd_id}/documents/upload-url", set()
        )

        # The same path can have multiple routes with different methods
        document_path = "/srd/{srd_id}/documents/{document_id}"
        assert "DELETE" in path_methods.get(document_path, set())
        assert "GET" in path_methods.get(document_path, set())

        documents_path = "/srd/{srd_id}/documents"
        assert "DELETE" in path_methods.get(documents_path, set())
        assert "GET" in path_methods.get(documents_path, set())

    def test_uuid_generation_in_upload_url(
        self, srd_router_with_mocks, mock_user
    ):
        """Test that UUID is properly generated for document uploads."""
        # Arrange
        srd_id = "test_srd"
        request = PresignedUrlRequest(
            file_name="test.pdf", content_type="application/pdf"
        )

        # Act & Assert - UUID should be different each time
        with patch("api_backend.routers.srd.uuid4") as mock_uuid:
            mock_uuid.side_effect = ["uuid-1", "uuid-2"]

            response1 = srd_router_with_mocks.get_presigned_upload_url(
                srd_id=srd_id, current_user=mock_user, request=request
            )
            response2 = srd_router_with_mocks.get_presigned_upload_url(
                srd_id=srd_id, current_user=mock_user, request=request
            )

            # Both should succeed but have different UUIDs
            assert response1.status_code == status.HTTP_200_OK
            assert response2.status_code == status.HTTP_200_OK
            assert "uuid-1" in response1.body.decode()
            assert "uuid-2" in response2.body.decode()

    def test_file_name_sanitization(self, srd_router_with_mocks, mock_user):
        """Test that file names are properly handled."""
        # Arrange
        srd_id = "test_srd"
        request = PresignedUrlRequest(
            file_name="  test document with spaces.pdf  ",
            content_type="application/pdf",
        )

        # Act
        with patch("api_backend.routers.srd.uuid4") as mock_uuid:
            mock_uuid.return_value = "test-uuid"
            response = srd_router_with_mocks.get_presigned_upload_url(
                srd_id=srd_id, current_user=mock_user, request=request
            )

        # Assert - should handle the filename correctly
        assert response.status_code == status.HTTP_200_OK
