"""Unit tests for the login router module."""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from fastapi import HTTPException, status

# Local Modules
from api_backend.models import LoginRequest


@pytest.fixture
def mock_cognito_client():
    """Create a mock Cognito IDP client for testing."""
    mock_client = MagicMock()
    # Default response should include AuthenticationResult for successful login
    mock_client.admin_initiate_auth.return_value = {
        "AuthenticationResult": {
            "AccessToken": "mock_access_token_12345",
            "ExpiresIn": 3600,
            "IdToken": "mock_id_token_67890",
            "RefreshToken": "mock_refresh_token_abcde",
            "TokenType": "Bearer",
        }
    }
    return mock_client


@pytest.fixture
def login_router_with_mocks(mock_cognito_client):
    """Create login router with mocked dependencies."""
    with patch(
        "api_backend.routers.auth.CognitoIdpClient"
    ) as mock_cognito_class:
        # Mock the dependency injection to return our mock client
        mock_cognito_class.return_value = mock_cognito_client

        # Mock the config values
        with patch("api_backend.routers.auth.USER_POOL_ID", "test_pool_id"):
            with patch(
                "api_backend.routers.auth.USER_POOL_CLIENT_ID",
                "test_client_id",
            ):
                # Local Modules
                from api_backend.routers import auth

                yield auth, mock_cognito_client


class TestLoginForAccessToken:
    """Test cases for the login_for_access_token endpoint."""

    def test_login_success(self, login_router_with_mocks):
        """Test successful user login without challenge."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        # Mock successful authentication response without challenge
        mock_cognito_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": {
                "AccessToken": "mock_access_token_12345",
                "ExpiresIn": 3600,
                "IdToken": "mock_id_token_67890",
                "RefreshToken": "mock_refresh_token_abcde",
                "TokenType": "Bearer",
            }
        }

        login_request = LoginRequest(
            username="testuser", password="testpassword123"
        )

        # Act
        response = login_router.login_for_access_token(
            login_request=login_request, cognito_client=mock_cognito_client
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Verify cognito client was called with correct parameters
        mock_cognito_client.admin_initiate_auth.assert_called_once_with(
            user_pool_id="test_pool_id",
            client_id="test_client_id",
            username="testuser",
            password="testpassword123",
        )

        # Check response content - should contain AuthenticationResult
        response_content = eval(response.body.decode())
        assert response_content["AccessToken"] == "mock_access_token_12345"
        assert response_content["ExpiresIn"] == 3600
        assert response_content["IdToken"] == "mock_id_token_67890"
        assert response_content["RefreshToken"] == "mock_refresh_token_abcde"
        assert response_content["TokenType"] == "Bearer"

    def test_login_success_with_special_characters(
        self, login_router_with_mocks
    ):
        """Test successful login with special characters in credentials."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        # Ensure the mock returns the correct format
        mock_cognito_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": {
                "AccessToken": "mock_access_token_12345",
                "ExpiresIn": 3600,
                "IdToken": "mock_id_token_67890",
                "RefreshToken": "mock_refresh_token_abcde",
                "TokenType": "Bearer",
            }
        }

        login_request = LoginRequest(
            username="user@example.com",  # Email as username
            password="P@ssw0rd!#$%",  # Complex password
        )

        # Act
        response = login_router.login_for_access_token(
            login_request=login_request, cognito_client=mock_cognito_client
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Verify cognito client was called with special characters
        mock_cognito_client.admin_initiate_auth.assert_called_once_with(
            user_pool_id="test_pool_id",
            client_id="test_client_id",
            username="user@example.com",
            password="P@ssw0rd!#$%",
        )

    def test_login_cognito_authentication_error(self, login_router_with_mocks):
        """Test login failure due to Cognito authentication error."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        # Mock Cognito to raise an exception
        mock_cognito_client.admin_initiate_auth.side_effect = Exception(
            "Invalid username or password"
        )

        login_request = LoginRequest(
            username="baduser", password="wrongpassword"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            login_router.login_for_access_token(
                login_request=login_request, cognito_client=mock_cognito_client
            )

        # Verify exception details
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password:" in str(exc_info.value.detail)
        assert "Invalid username or password" in str(exc_info.value.detail)
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    def test_login_cognito_user_not_found(self, login_router_with_mocks):
        """Test login failure when user does not exist."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        # Mock Cognito to raise a user not found exception
        mock_cognito_client.admin_initiate_auth.side_effect = Exception(
            "User does not exist"
        )

        login_request = LoginRequest(
            username="nonexistentuser", password="somepassword"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            login_router.login_for_access_token(
                login_request=login_request, cognito_client=mock_cognito_client
            )

        # Verify exception details
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User does not exist" in str(exc_info.value.detail)

    def test_login_cognito_user_not_confirmed(self, login_router_with_mocks):
        """Test login failure when user account is not confirmed."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        # Mock Cognito to raise a user not confirmed exception
        mock_cognito_client.admin_initiate_auth.side_effect = Exception(
            "User is not confirmed"
        )

        login_request = LoginRequest(
            username="unconfirmeduser", password="correctpassword"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            login_router.login_for_access_token(
                login_request=login_request, cognito_client=mock_cognito_client
            )

        # Verify exception details
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User is not confirmed" in str(exc_info.value.detail)

    def test_login_with_empty_username(self, login_router_with_mocks):
        """Test login with empty username."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        # Ensure the mock returns the correct format
        mock_cognito_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": {
                "AccessToken": "mock_access_token_12345",
                "ExpiresIn": 3600,
                "IdToken": "mock_id_token_67890",
                "RefreshToken": "mock_refresh_token_abcde",
                "TokenType": "Bearer",
            }
        }

        login_request = LoginRequest(username="", password="somepassword")

        # Act
        response = login_router.login_for_access_token(
            login_request=login_request, cognito_client=mock_cognito_client
        )

        # Assert - Should still work as Cognito will handle the validation
        assert response.status_code == status.HTTP_200_OK

        # Verify cognito client was called with empty username
        mock_cognito_client.admin_initiate_auth.assert_called_once_with(
            user_pool_id="test_pool_id",
            client_id="test_client_id",
            username="",
            password="somepassword",
        )

    def test_login_with_empty_password(self, login_router_with_mocks):
        """Test login with empty password."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        # Ensure the mock returns the correct format
        mock_cognito_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": {
                "AccessToken": "mock_access_token_12345",
                "ExpiresIn": 3600,
                "IdToken": "mock_id_token_67890",
                "RefreshToken": "mock_refresh_token_abcde",
                "TokenType": "Bearer",
            }
        }

        login_request = LoginRequest(username="testuser", password="")

        # Act
        response = login_router.login_for_access_token(
            login_request=login_request, cognito_client=mock_cognito_client
        )

        # Assert - Should still work as Cognito will handle the validation
        assert response.status_code == status.HTTP_200_OK

        # Verify cognito client was called with empty password
        mock_cognito_client.admin_initiate_auth.assert_called_once_with(
            user_pool_id="test_pool_id",
            client_id="test_client_id",
            username="testuser",
            password="",
        )

    def test_login_logging_success(self, login_router_with_mocks):
        """Test that successful login generates appropriate log messages."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        login_request = LoginRequest(
            username="testuser", password="testpassword"
        )

        # Act
        with patch.object(login_router.logger, "info") as mock_log_info:
            response = login_router.login_for_access_token(
                login_request=login_request, cognito_client=mock_cognito_client
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Verify logging was called correctly
        assert mock_log_info.call_count == 2

        # Check log messages
        call_args_list = mock_log_info.call_args_list
        assert "Attempting to log in user: testuser" in call_args_list[0][0][0]
        assert (
            "User testuser logged in successfully" in call_args_list[1][0][0]
        )

    def test_login_logging_failure(self, login_router_with_mocks):
        """Test that failed login generates appropriate log messages."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        # Mock Cognito to raise an exception
        mock_cognito_client.admin_initiate_auth.side_effect = Exception(
            "Authentication failed"
        )

        login_request = LoginRequest(
            username="testuser", password="wrongpassword"
        )

        # Act
        with patch.object(login_router.logger, "info") as mock_log_info:
            with patch.object(login_router.logger, "error") as mock_log_error:
                with pytest.raises(HTTPException):
                    login_router.login_for_access_token(
                        login_request=login_request,
                        cognito_client=mock_cognito_client,
                    )

        # Assert logging was called correctly
        mock_log_info.assert_called_once_with(
            "Attempting to log in user: testuser"
        )
        mock_log_error.assert_called_once()

        # Check error log message
        error_call_args = mock_log_error.call_args[0][0]
        assert "Login failed for user testuser:" in error_call_args
        assert "Authentication failed" in error_call_args

    def test_login_different_cognito_errors(self, login_router_with_mocks):
        """Test various types of Cognito errors are handled consistently."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        cognito_errors = [
            "NotAuthorizedException",
            "UserNotFoundException",
            "UserNotConfirmedException",
            "PasswordResetRequiredException",
            "TooManyRequestsException",
        ]

        for error_message in cognito_errors:
            # Reset the mock
            mock_cognito_client.reset_mock()
            mock_cognito_client.admin_initiate_auth.side_effect = Exception(
                error_message
            )

            login_request = LoginRequest(
                username="testuser", password="testpassword"
            )

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                login_router.login_for_access_token(
                    login_request=login_request,
                    cognito_client=mock_cognito_client,
                )

            # All should result in 401 Unauthorized
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert error_message in str(exc_info.value.detail)
            assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    def test_login_response_contains_all_token_fields(
        self, login_router_with_mocks
    ):
        """Test that login response contains all expected token fields."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        # Mock a more complete token response
        mock_cognito_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": {
                "AccessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "ExpiresIn": 7200,
                "IdToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "RefreshToken": "eyJjdHkiOiJKV1QiLCJlbmMiOiJBMjU2R0NNIiwiYWxnIjoiUlNBLU9BRVAifQ...",
                "TokenType": "Bearer",
            }
        }

        login_request = LoginRequest(
            username="testuser", password="testpassword"
        )

        # Act
        response = login_router.login_for_access_token(
            login_request=login_request, cognito_client=mock_cognito_client
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        response_content = eval(response.body.decode())

        # Verify all expected fields are present
        assert "AccessToken" in response_content
        assert "ExpiresIn" in response_content
        assert "IdToken" in response_content
        assert "RefreshToken" in response_content
        assert "TokenType" in response_content

        # Verify field values
        assert response_content["ExpiresIn"] == 7200
        assert response_content["TokenType"] == "Bearer"
        assert len(response_content["AccessToken"]) > 0
        assert len(response_content["IdToken"]) > 0
        assert len(response_content["RefreshToken"]) > 0

    def test_login_new_password_required_challenge(
        self, login_router_with_mocks
    ):
        """Test login when user needs to set a new password."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        # Mock Cognito response with NEW_PASSWORD_REQUIRED challenge
        mock_cognito_client.admin_initiate_auth.return_value = {
            "ChallengeName": "NEW_PASSWORD_REQUIRED",
            "Session": "mock-session-token-12345",
            "ChallengeParameters": {
                "USER_ID_FOR_SRP": "testuser",
                "requiredAttributes": "[]",
                "userAttributes": '{"email":"test@example.com"}',
            },
        }

        login_request = LoginRequest(
            username="testuser", password="temporarypassword"
        )

        # Act
        response = login_router.login_for_access_token(
            login_request=login_request, cognito_client=mock_cognito_client
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Check response content - should contain challenge information
        response_content = eval(response.body.decode())
        assert response_content["ChallengeName"] == "NEW_PASSWORD_REQUIRED"
        assert response_content["Session"] == "mock-session-token-12345"
        assert response_content["username"] == "testuser"

        # Verify cognito client was called correctly
        mock_cognito_client.admin_initiate_auth.assert_called_once_with(
            user_pool_id="test_pool_id",
            client_id="test_client_id",
            username="testuser",
            password="temporarypassword",
        )


class TestRouterIntegration:
    """Integration tests for the login router."""

    def test_router_endpoint_exists(self, login_router_with_mocks):
        """Test that the expected endpoint exists in the router."""
        # Get the router instance
        login_router, _ = login_router_with_mocks
        router = login_router.router

        # Check that router has the expected route
        route_paths = [route.path for route in router.routes]
        assert "/auth/login" in route_paths

    def test_router_methods(self, login_router_with_mocks):
        """Test that route has correct HTTP method."""
        login_router, _ = login_router_with_mocks
        router = login_router.router

        # Find the route and check method
        for route in router.routes:
            if route.path == "/auth/login":
                assert "POST" in route.methods
                break
        else:
            pytest.fail("Route /auth/login not found")

    def test_router_prefix(self, login_router_with_mocks):
        """Test that router has correct prefix."""
        login_router, _ = login_router_with_mocks
        router = login_router.router
        assert router.prefix == "/auth"

    def test_router_tags(self, login_router_with_mocks):
        """Test that router has correct tags."""
        login_router, _ = login_router_with_mocks
        router = login_router.router
        assert "Authentication" in router.tags

    def test_cognito_dependency_injection(self, login_router_with_mocks):
        """Test that Cognito client dependency injection works correctly."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        login_request = LoginRequest(
            username="testuser", password="testpassword"
        )

        # Act
        response = login_router.login_for_access_token(
            login_request=login_request, cognito_client=mock_cognito_client
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Verify the dependency was used
        mock_cognito_client.admin_initiate_auth.assert_called_once()

    def test_config_values_usage(self, login_router_with_mocks):
        """Test that USER_POOL_ID and USER_POOL_CLIENT_ID config values are used."""
        # Arrange
        login_router, mock_cognito_client = login_router_with_mocks

        login_request = LoginRequest(
            username="testuser", password="testpassword"
        )

        # Act
        login_router.login_for_access_token(
            login_request=login_request, cognito_client=mock_cognito_client
        )

        # Assert - Verify the config values were passed to Cognito
        call_args = mock_cognito_client.admin_initiate_auth.call_args
        assert call_args[1]["user_pool_id"] == "test_pool_id"
        assert call_args[1]["client_id"] == "test_client_id"

    def test_login_request_body_validation(self, login_router_with_mocks):
        """Test that LoginRequest model validation works correctly."""
        # This test verifies the Pydantic model validation

        # Valid request should work
        valid_request = LoginRequest(
            username="testuser", password="testpassword"
        )
        assert valid_request.username == "testuser"
        assert valid_request.password == "testpassword"

        # Test that empty strings are allowed (Cognito will handle validation)
        empty_request = LoginRequest(username="", password="")
        assert empty_request.username == ""
        assert empty_request.password == ""

        # Note: FastAPI will validate the request body at the endpoint level
