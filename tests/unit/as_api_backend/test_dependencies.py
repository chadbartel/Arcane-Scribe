"""Unit tests for the dependencies module."""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException, Request, status

# Local Modules
# Local - Import directly from the dependencies module file
from api_backend.dependencies.dependencies import (
    get_allowed_ip_from_ssm,
    get_current_user,
    require_admin_user,
    verify_source_ip,
)
from api_backend.models.auth import User


class TestGetAllowedIpFromSsm:
    """Test cases for get_allowed_ip_from_ssm function."""

    @patch("api_backend.dependencies.dependencies.SsmClient")
    @patch(
        "api_backend.dependencies.dependencies.HOME_IP_SSM_PARAMETER_NAME",
        "/test/home-ip",
    )
    def test_get_allowed_ip_success(self, mock_ssm_client_class):
        """Test successful retrieval of allowed IP from SSM."""
        # Arrange
        mock_ssm_client = MagicMock()
        mock_ssm_client_class.return_value = mock_ssm_client
        mock_ssm_client.get_parameter.return_value = "192.168.1.100"

        # Act
        result = get_allowed_ip_from_ssm()

        # Assert
        assert result == "192.168.1.100"
        mock_ssm_client_class.assert_called_once()
        mock_ssm_client.get_parameter.assert_called_once_with(
            name="/test/home-ip"
        )

    @patch("api_backend.dependencies.dependencies.SsmClient")
    @patch(
        "api_backend.dependencies.dependencies.HOME_IP_SSM_PARAMETER_NAME",
        "/test/home-ip",
    )
    def test_get_allowed_ip_empty_value(self, mock_ssm_client_class):
        """Test handling of empty parameter value."""
        # Arrange
        mock_ssm_client = MagicMock()
        mock_ssm_client_class.return_value = mock_ssm_client
        mock_ssm_client.get_parameter.return_value = ""

        # Act
        result = get_allowed_ip_from_ssm()

        # Assert
        assert result is None

    @patch("api_backend.dependencies.dependencies.SsmClient")
    @patch(
        "api_backend.dependencies.dependencies.HOME_IP_SSM_PARAMETER_NAME",
        "/test/home-ip",
    )
    def test_get_allowed_ip_client_error(self, mock_ssm_client_class):
        """Test handling of SSM client error."""
        # Arrange
        mock_ssm_client = MagicMock()
        mock_ssm_client_class.return_value = mock_ssm_client
        client_error = ClientError(
            {
                "Error": {
                    "Code": "ParameterNotFound",
                    "Message": "Parameter not found",
                }
            },
            "GetParameter",
        )
        mock_ssm_client.get_parameter.side_effect = client_error

        # Act
        result = get_allowed_ip_from_ssm()

        # Assert
        assert result is None

    @patch("api_backend.dependencies.dependencies.SsmClient")
    @patch(
        "api_backend.dependencies.dependencies.HOME_IP_SSM_PARAMETER_NAME",
        "/test/home-ip",
    )
    @patch("api_backend.dependencies.dependencies.logger")
    def test_get_allowed_ip_logs_error_on_empty(
        self, mock_logger, mock_ssm_client_class
    ):
        """Test logging when parameter value is empty."""
        # Arrange
        mock_ssm_client = MagicMock()
        mock_ssm_client_class.return_value = mock_ssm_client
        mock_ssm_client.get_parameter.return_value = None

        # Act
        result = get_allowed_ip_from_ssm()

        # Assert
        assert result is None
        mock_logger.error.assert_called_once_with(
            "SSM parameter value is empty or not found."
        )

    @patch("api_backend.dependencies.dependencies.SsmClient")
    @patch(
        "api_backend.dependencies.dependencies.HOME_IP_SSM_PARAMETER_NAME",
        "/test/home-ip",
    )
    @patch("api_backend.dependencies.dependencies.logger")
    def test_get_allowed_ip_logs_exception(
        self, mock_logger, mock_ssm_client_class
    ):
        """Test logging when SSM client raises exception."""
        # Arrange
        mock_ssm_client = MagicMock()
        mock_ssm_client_class.return_value = mock_ssm_client
        client_error = ClientError(
            {
                "Error": {
                    "Code": "ParameterNotFound",
                    "Message": "Parameter not found",
                }
            },
            "GetParameter",
        )
        mock_ssm_client.get_parameter.side_effect = client_error

        # Act
        result = get_allowed_ip_from_ssm()

        # Assert
        assert result is None
        mock_logger.exception.assert_called_once_with(
            f"Error fetching IP from SSM parameter '/test/home-ip': {client_error}"
        )

    @patch("api_backend.dependencies.dependencies.SsmClient")
    @patch(
        "api_backend.dependencies.dependencies.HOME_IP_SSM_PARAMETER_NAME",
        "/test/home-ip",
    )
    @patch("api_backend.dependencies.dependencies.logger")
    def test_get_allowed_ip_non_string_value(
        self, mock_logger, mock_ssm_client_class
    ):
        """Test handling when parameter value is not a string."""
        # Arrange
        mock_ssm_client = MagicMock()
        mock_ssm_client_class.return_value = mock_ssm_client
        mock_ssm_client.get_parameter.return_value = 12345  # Non-string value

        # Act
        result = get_allowed_ip_from_ssm()

        # Assert
        assert result is None
        mock_logger.error.assert_called_once_with(
            "SSM parameter value is empty or not found."
        )


class TestVerifySourceIp:
    """Test cases for verify_source_ip function."""

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_success_api_gateway(self, mock_get_allowed_ip):
        """Test successful IP verification with API Gateway source."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.scope = {
            "aws.event": {
                "requestContext": {"identity": {"sourceIp": "192.168.1.100"}}
            }
        }

        # Act - Should not raise exception
        verify_source_ip(request)

        # Assert
        mock_get_allowed_ip.assert_called_once()

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_success_local_client(self, mock_get_allowed_ip):
        """Test successful IP verification with local client."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.scope = {}  # No AWS event
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        # Act - Should not raise exception
        verify_source_ip(request)

        # Assert
        mock_get_allowed_ip.assert_called_once()

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_no_source_ip_available(
        self, mock_get_allowed_ip
    ):
        """Test IP verification when no source IP can be determined."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.scope = {}  # No AWS event
        request.client = None  # No client info

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_source_ip(request)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Could not determine client IP address" in exc_info.value.detail

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_forbidden(self, mock_get_allowed_ip):
        """Test IP verification with non-matching IP."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.scope = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.200"  # Different IP

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_source_ip(request)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "Access from your IP address is not permitted"
            in exc_info.value.detail
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    @patch("api_backend.dependencies.dependencies.logger")
    def test_verify_source_ip_logs_success(
        self, mock_logger, mock_get_allowed_ip
    ):
        """Test logging on successful IP verification."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.scope = {
            "aws.event": {
                "requestContext": {"identity": {"sourceIp": "192.168.1.100"}}
            }
        }

        # Act
        verify_source_ip(request)

        # Assert
        mock_logger.append_keys.assert_called_once_with(
            source_ip="192.168.1.100"
        )
        mock_logger.info.assert_any_call("Executing IP whitelist check.")
        mock_logger.info.assert_any_call(
            "IP address 192.168.1.100 successfully verified against whitelist."
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    @patch("api_backend.dependencies.dependencies.logger")
    def test_verify_source_ip_logs_warning_on_missing_ip(
        self, mock_logger, mock_get_allowed_ip
    ):
        """Test logging when source IP cannot be determined."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.scope = {}
        request.client = None

        # Act & Assert
        with pytest.raises(HTTPException):
            verify_source_ip(request)

        mock_logger.warning.assert_called_once_with(
            "Source IP could not be determined from the request."
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    @patch("api_backend.dependencies.dependencies.logger")
    def test_verify_source_ip_logs_warning_on_forbidden(
        self, mock_logger, mock_get_allowed_ip
    ):
        """Test logging when IP is forbidden."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.scope = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.200"

        # Act & Assert
        with pytest.raises(HTTPException):
            verify_source_ip(request)

        mock_logger.warning.assert_called_once_with(
            "Forbidden access for IP: 192.168.1.200. Whitelisted IP is 192.168.1.100."
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    @patch("api_backend.dependencies.dependencies.logger")
    def test_verify_source_ip_service_unavailable_on_no_allowed_ip(
        self, mock_logger, mock_get_allowed_ip
    ):
        """Test 503 error when allowed IP cannot be loaded."""
        # Arrange
        mock_get_allowed_ip.return_value = None
        request = MagicMock(spec=Request)
        request.scope = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_source_ip(request)

        assert (
            exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        )
        assert "Service is temporarily unavailable" in exc_info.value.detail
        mock_logger.error.assert_called_once_with(
            "Whitelist IP could not be loaded from configuration. Denying access by default."
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_aws_event_no_identity(self, mock_get_allowed_ip):
        """Test IP verification when AWS event has no identity section."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.scope = {
            "aws.event": {
                "requestContext": {
                    # Missing identity section
                }
            }
        }
        request.client = MagicMock()
        request.client.host = "192.168.1.100"  # Falls back to client

        # Act - Should not raise exception (falls back to client IP)
        verify_source_ip(request)

        # Assert
        mock_get_allowed_ip.assert_called_once()

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_aws_event_no_source_ip_key(
        self, mock_get_allowed_ip
    ):
        """Test IP verification when AWS event identity has no sourceIp key."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.scope = {
            "aws.event": {
                "requestContext": {
                    "identity": {
                        # Missing sourceIp key
                        "userAgent": "test-agent"
                    }
                }
            }
        }
        request.client = MagicMock()
        request.client.host = "192.168.1.100"  # Falls back to client

        # Act - Should not raise exception (falls back to client IP)
        verify_source_ip(request)

        # Assert
        mock_get_allowed_ip.assert_called_once()


class TestGetCurrentUser:
    """Test cases for get_current_user function."""

    def test_get_current_user_success(self):
        """Test successful user retrieval from JWT claims."""
        # Arrange
        request = MagicMock(spec=Request)
        request.scope = {
            "aws.event": {
                "requestContext": {
                    "authorizer": {
                        "claims": {
                            "cognito:username": "testuser",
                            "email": "test@example.com",
                            "cognito:groups": ["users", "admin"],
                        }
                    }
                }
            }
        }

        # Act
        result = get_current_user(request)

        # Assert
        assert isinstance(result, User)
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        assert result.groups == ["users", "admin"]

    def test_get_current_user_single_group_as_string(self):
        """Test user retrieval with single group as string."""
        # Arrange
        request = MagicMock(spec=Request)
        request.scope = {
            "aws.event": {
                "requestContext": {
                    "authorizer": {
                        "claims": {
                            "cognito:username": "testuser",
                            "email": "test@example.com",
                            "cognito:groups": "admin",  # Single string
                        }
                    }
                }
            }
        }

        # Act
        result = get_current_user(request)

        # Assert
        assert isinstance(result, User)
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        assert result.groups == ["admin"]

    def test_get_current_user_missing_claims(self):
        """Test user retrieval with missing claims."""
        # Arrange
        request = MagicMock(spec=Request)
        request.scope = {
            "aws.event": {
                "requestContext": {
                    # Missing authorizer section
                }
            }
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            "Could not validate credentials. Claims missing."
            in exc_info.value.detail
        )

    def test_get_current_user_no_groups(self):
        """Test user retrieval with no groups claim."""
        # Arrange
        request = MagicMock(spec=Request)
        request.scope = {
            "aws.event": {
                "requestContext": {
                    "authorizer": {
                        "claims": {
                            "cognito:username": "testuser",
                            "email": "test@example.com",
                            # No cognito:groups claim
                        }
                    }
                }
            }
        }

        # Act
        result = get_current_user(request)

        # Assert
        assert isinstance(result, User)
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        assert result.groups == []  # Default empty list

    def test_get_current_user_missing_username(self):
        """Test user retrieval with missing username claim."""
        # Arrange
        request = MagicMock(spec=Request)
        request.scope = {
            "aws.event": {
                "requestContext": {
                    "authorizer": {
                        "claims": {
                            "email": "test@example.com",
                            "cognito:groups": ["users"],
                            # Missing cognito:username
                        }
                    }
                }
            }
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            "Could not validate credentials. Claims missing."
            in exc_info.value.detail
        )

    def test_get_current_user_missing_email(self):
        """Test user retrieval with missing email claim."""
        # Arrange
        request = MagicMock(spec=Request)
        request.scope = {
            "aws.event": {
                "requestContext": {
                    "authorizer": {
                        "claims": {
                            "cognito:username": "testuser",
                            "cognito:groups": ["users"],
                            # Missing email
                        }
                    }
                }
            }
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            "Could not validate credentials. Claims missing."
            in exc_info.value.detail
        )


class TestRequireAdminUser:
    """Test cases for require_admin_user function."""

    def test_require_admin_user_success(self):
        """Test successful admin user verification."""
        # Arrange
        user = User(
            username="admin",
            email="admin@example.com",
            groups=["users", "Admins", "moderators"],
        )

        # Act
        result = require_admin_user(user)

        # Assert
        assert result == user

    def test_require_admin_user_no_admin_group(self):
        """Test admin user verification without admin group."""
        # Arrange
        user = User(
            username="user",
            email="user@example.com",
            groups=["users", "moderators"],
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            require_admin_user(user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "User does not have admin privileges" in exc_info.value.detail

    def test_require_admin_user_empty_groups(self):
        """Test admin user verification with empty groups list."""
        # Arrange
        user = User(username="user", email="user@example.com", groups=[])

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            require_admin_user(user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "User does not have admin privileges" in exc_info.value.detail

    def test_require_admin_user_case_sensitive(self):
        """Test admin user verification is case sensitive."""
        # Arrange
        user = User(
            username="user",
            email="user@example.com",
            groups=["users", "admins", "moderators"],  # lowercase "admins"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            require_admin_user(user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "User does not have admin privileges" in exc_info.value.detail


class TestDependenciesIntegration:
    """Integration test cases for dependencies working together."""

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_full_authentication_flow(self, mock_get_allowed_ip):
        """Test full flow of IP verification and user authentication."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.scope = {
            "aws.event": {
                "requestContext": {
                    "identity": {"sourceIp": "192.168.1.100"},
                    "authorizer": {
                        "claims": {
                            "cognito:username": "admin",
                            "email": "admin@example.com",
                            "cognito:groups": ["Admins"],
                        }
                    },
                }
            }
        }

        # Act - IP verification
        verify_source_ip(request)  # Should pass
        user = get_current_user(request)
        admin_user = require_admin_user(user)

        # Assert
        assert user == admin_user
        assert admin_user.username == "admin"
        assert "Admins" in admin_user.groups
        mock_get_allowed_ip.assert_called_once()
