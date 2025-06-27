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
    def test_verify_source_ip_success_x_forwarded_for(
        self, mock_get_allowed_ip
    ):
        """Test successful IP verification using X-Forwarded-For header."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "192.168.1.100, 10.0.0.1"}
        request.scope = {}

        # Act - Should not raise exception
        result = verify_source_ip(request)

        # Assert
        assert result is True
        mock_get_allowed_ip.assert_called_once()

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_success_api_gateway_fallback(
        self, mock_get_allowed_ip
    ):
        """Test successful IP verification using API Gateway fallback."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {}  # No X-Forwarded-For header
        request.scope = {
            "aws.event": {
                "requestContext": {"identity": {"sourceIp": "192.168.1.100"}}
            }
        }

        # Act - Should not raise exception
        result = verify_source_ip(request)

        # Assert
        assert result is True
        mock_get_allowed_ip.assert_called_once()

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_x_forwarded_for_multiple_ips(
        self, mock_get_allowed_ip
    ):
        """Test IP verification with multiple IPs in X-Forwarded-For header."""
        # Arrange
        mock_get_allowed_ip.return_value = "203.0.113.1"
        request = MagicMock(spec=Request)
        request.headers = {
            "x-forwarded-for": "203.0.113.1, 192.168.1.1, 10.0.0.1"
        }
        request.scope = {}

        # Act - Should not raise exception
        result = verify_source_ip(request)

        # Assert
        assert result is True
        mock_get_allowed_ip.assert_called_once()

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_forbidden_x_forwarded_for(
        self, mock_get_allowed_ip
    ):
        """Test IP verification with non-matching IP in X-Forwarded-For."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "192.168.1.200, 10.0.0.1"}
        request.scope = {}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_source_ip(request)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "Access from your IP address is not permitted"
            in exc_info.value.detail
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_forbidden_api_gateway(self, mock_get_allowed_ip):
        """Test IP verification with non-matching IP from API Gateway."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {}
        request.scope = {
            "aws.event": {
                "requestContext": {"identity": {"sourceIp": "192.168.1.200"}}
            }
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_source_ip(request)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "Access from your IP address is not permitted"
            in exc_info.value.detail
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_no_source_available(self, mock_get_allowed_ip):
        """Test IP verification when no source IP can be determined."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {}
        request.scope = {}  # No AWS event

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_source_ip(request)

        assert (
            exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        assert (
            "Server configuration error: Cannot determine source IP"
            in exc_info.value.detail
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_missing_request_context(
        self, mock_get_allowed_ip
    ):
        """Test IP verification when AWS event has no requestContext."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {}
        request.scope = {"aws.event": {}}  # Missing requestContext

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_source_ip(request)

        assert (
            exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        assert (
            "Server configuration error: Cannot determine source IP"
            in exc_info.value.detail
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_missing_identity(self, mock_get_allowed_ip):
        """Test IP verification when AWS event has no identity."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {}
        request.scope = {
            "aws.event": {"requestContext": {}}  # Missing identity
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_source_ip(request)

        assert (
            exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        assert (
            "Server configuration error: Cannot determine source IP"
            in exc_info.value.detail
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_missing_source_ip_key(self, mock_get_allowed_ip):
        """Test IP verification when AWS event identity has no sourceIp."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {}
        request.scope = {
            "aws.event": {
                "requestContext": {"identity": {}}  # Missing sourceIp
            }
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_source_ip(request)

        assert (
            exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        assert (
            "Server configuration error: Cannot determine source IP"
            in exc_info.value.detail
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    @patch("api_backend.dependencies.dependencies.logger")
    def test_verify_source_ip_logs_x_forwarded_for(
        self, mock_logger, mock_get_allowed_ip
    ):
        """Test logging when using X-Forwarded-For header."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "192.168.1.100, 10.0.0.1"}
        request.scope = {}

        # Act
        verify_source_ip(request)

        # Assert
        mock_logger.info.assert_any_call(
            "Found source IP in X-Forwarded-For header: 192.168.1.100"
        )
        mock_logger.info.assert_any_call(
            "Verifying request source IP '192.168.1.100' against whitelisted IP '192.168.1.100'."
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    @patch("api_backend.dependencies.dependencies.logger")
    def test_verify_source_ip_logs_api_gateway_fallback(
        self, mock_logger, mock_get_allowed_ip
    ):
        """Test logging when using API Gateway fallback."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {}
        request.scope = {
            "aws.event": {
                "requestContext": {"identity": {"sourceIp": "192.168.1.100"}}
            }
        }

        # Act
        verify_source_ip(request)

        # Assert
        mock_logger.info.assert_any_call(
            "Using source IP from requestContext: 192.168.1.100"
        )
        mock_logger.info.assert_any_call(
            "Verifying request source IP '192.168.1.100' against whitelisted IP '192.168.1.100'."
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    @patch("api_backend.dependencies.dependencies.logger")
    def test_verify_source_ip_logs_error_on_missing_source(
        self, mock_logger, mock_get_allowed_ip
    ):
        """Test logging when source IP cannot be determined."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {}
        request.scope = {}

        # Act & Assert
        with pytest.raises(HTTPException):
            verify_source_ip(request)

        mock_logger.error.assert_called_once_with(
            "Could not find 'sourceIp' in request context."
        )

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_whitespace_in_x_forwarded_for(
        self, mock_get_allowed_ip
    ):
        """Test IP verification handles whitespace in X-Forwarded-For header."""
        # Arrange
        mock_get_allowed_ip.return_value = "192.168.1.100"
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "  192.168.1.100  , 10.0.0.1"}
        request.scope = {}

        # Act - Should not raise exception
        result = verify_source_ip(request)

        # Assert
        assert result is True
        mock_get_allowed_ip.assert_called_once()

    @patch("api_backend.dependencies.dependencies.get_allowed_ip_from_ssm")
    def test_verify_source_ip_no_whitelisted_ip_available(
        self, mock_get_allowed_ip
    ):
        """Test IP verification when whitelisted IP cannot be retrieved."""
        # Arrange
        mock_get_allowed_ip.return_value = None  # SSM parameter fetch failed
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "192.168.1.100"}
        request.scope = {}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_source_ip(request)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "Access from your IP address is not permitted"
            in exc_info.value.detail
        )
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
            groups=["users", "admins", "moderators"],
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
            groups=["users", "Admins", "moderators"],  # uppercase "Admins"
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
                            "cognito:groups": ["admins"],
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
        assert "admins" in admin_user.groups
        mock_get_allowed_ip.assert_called_once()
