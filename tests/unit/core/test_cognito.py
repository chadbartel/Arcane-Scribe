"""Unit tests for the cognito module."""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from botocore.exceptions import ClientError, NoCredentialsError

# Local Modules
from core.aws.cognito import CognitoIdpClient


class TestCognitoIdpClient:
    """Test cases for the CognitoIdpClient class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.user_pool_id = "us-east-1_testpool123"
        self.client_id = "test-client-id-123"
        self.username = "testuser"
        self.password = "TestPassword123!"
        self.email = "testuser@example.com"
        self.temporary_password = "TempPass123!"

    @patch("core.aws.cognito.boto3.client")
    def test_init_success_with_region(self, mock_boto3_client):
        """Test successful initialization with region_name."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        region_name = "us-west-2"

        cognito_client = CognitoIdpClient(region_name=region_name)

        mock_boto3_client.assert_called_once_with(
            "cognito-idp", region_name=region_name
        )
        assert cognito_client.client == mock_client

    @patch("core.aws.cognito.boto3.client")
    def test_init_success_without_region(self, mock_boto3_client):
        """Test successful initialization without region_name."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        cognito_client = CognitoIdpClient()

        mock_boto3_client.assert_called_once_with(
            "cognito-idp", region_name=None
        )
        assert cognito_client.client == mock_client

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_init_failure_no_credentials(self, mock_logger, mock_boto3_client):
        """Test initialization failure due to missing credentials."""
        error = NoCredentialsError()
        mock_boto3_client.side_effect = error

        with pytest.raises(NoCredentialsError):
            CognitoIdpClient()

        mock_logger.exception.assert_called_once_with(
            f"Failed to initialize Boto3 Cognito IDP client: {error}"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_init_failure_client_error(self, mock_logger, mock_boto3_client):
        """Test initialization failure due to AWS client error."""
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "CreateClient",
        )
        mock_boto3_client.side_effect = error

        with pytest.raises(ClientError):
            CognitoIdpClient()

        mock_logger.exception.assert_called_once_with(
            f"Failed to initialize Boto3 Cognito IDP client: {error}"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_initiate_auth_success_without_metadata(
        self, mock_logger, mock_boto3_client
    ):
        """Test successful authentication without client metadata."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        auth_result = {
            "AccessToken": "test-access-token",
            "IdToken": "test-id-token",
            "RefreshToken": "test-refresh-token",
            "TokenType": "Bearer",
            "ExpiresIn": 3600,
        }
        mock_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": auth_result
        }

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_initiate_auth(
            user_pool_id=self.user_pool_id,
            client_id=self.client_id,
            username=self.username,
            password=self.password,
        )

        mock_client.admin_initiate_auth.assert_called_once_with(
            UserPoolId=self.user_pool_id,
            ClientId=self.client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": self.username,
                "PASSWORD": self.password,
            },
        )
        assert result == auth_result
        mock_logger.info.assert_called_once_with(
            f"Initiating auth for user {self.username} in user pool {self.user_pool_id}"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_initiate_auth_success_with_metadata(
        self, mock_logger, mock_boto3_client
    ):
        """Test successful authentication with client metadata."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        auth_result = {"AccessToken": "test-token"}
        mock_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": auth_result
        }

        client_metadata = {"device": "mobile", "version": "1.0"}
        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_initiate_auth(
            user_pool_id=self.user_pool_id,
            client_id=self.client_id,
            username=self.username,
            password=self.password,
            client_metadata=client_metadata,
        )

        mock_client.admin_initiate_auth.assert_called_once_with(
            UserPoolId=self.user_pool_id,
            ClientId=self.client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": self.username,
                "PASSWORD": self.password,
            },
            ClientMetadata=client_metadata,
        )
        assert result == auth_result

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_initiate_auth_success_custom_auth_flow(
        self, mock_logger, mock_boto3_client
    ):
        """Test successful authentication with custom auth flow."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        auth_result = {"AccessToken": "test-token"}
        mock_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": auth_result
        }

        custom_auth_flow = "CUSTOM_AUTH"
        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_initiate_auth(
            user_pool_id=self.user_pool_id,
            client_id=self.client_id,
            username=self.username,
            password=self.password,
            auth_flow=custom_auth_flow,
        )

        mock_client.admin_initiate_auth.assert_called_once_with(
            UserPoolId=self.user_pool_id,
            ClientId=self.client_id,
            AuthFlow=custom_auth_flow,
            AuthParameters={
                "USERNAME": self.username,
                "PASSWORD": self.password,
            },
        )
        assert result == auth_result

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_initiate_auth_client_error(
        self, mock_logger, mock_boto3_client
    ):
        """Test authentication failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        error = ClientError(
            {
                "Error": {
                    "Code": "NotAuthorizedException",
                    "Message": "Incorrect username or password",
                }
            },
            "AdminInitiateAuth",
        )
        mock_client.admin_initiate_auth.side_effect = error

        cognito_client = CognitoIdpClient()

        with pytest.raises(ClientError):
            cognito_client.admin_initiate_auth(
                user_pool_id=self.user_pool_id,
                client_id=self.client_id,
                username=self.username,
                password="wrong_password",
            )

        mock_logger.error.assert_called_once_with(
            f"Error initiating auth for user '{self.username}': {error}"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_initiate_auth_empty_response(
        self, mock_logger, mock_boto3_client
    ):
        """Test authentication with empty authentication result."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        mock_client.admin_initiate_auth.return_value = {}

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_initiate_auth(
            user_pool_id=self.user_pool_id,
            client_id=self.client_id,
            username=self.username,
            password=self.password,
        )

        assert result == {}

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_create_user_success(self, mock_logger, mock_boto3_client):
        """Test successful user creation."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        user_data = {
            "Username": self.username,
            "UserStatus": "FORCE_CHANGE_PASSWORD",
            "Enabled": True,
            "UserCreateDate": "2023-06-19T10:30:00Z",
            "UserLastModifiedDate": "2023-06-19T10:30:00Z",
            "Attributes": [
                {"Name": "email", "Value": self.email},
                {"Name": "email_verified", "Value": "true"},
            ],
        }
        mock_client.admin_create_user.return_value = {"User": user_data}

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_create_user(
            user_pool_id=self.user_pool_id,
            username=self.username,
            email=self.email,
            temporary_password=self.temporary_password,
        )

        mock_client.admin_create_user.assert_called_once_with(
            UserPoolId=self.user_pool_id,
            Username=self.username,
            UserAttributes=[
                {"Name": "email", "Value": self.email},
                {"Name": "email_verified", "Value": "true"},
            ],
            TemporaryPassword=self.temporary_password,
            MessageAction="SUPPRESS",
        )
        assert result == user_data
        mock_logger.info.assert_called_once_with(
            f"Creating new user '{self.username}' in pool {self.user_pool_id}"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_create_user_client_error(
        self, mock_logger, mock_boto3_client
    ):
        """Test user creation failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        error = ClientError(
            {
                "Error": {
                    "Code": "UsernameExistsException",
                    "Message": "User already exists",
                }
            },
            "AdminCreateUser",
        )
        mock_client.admin_create_user.side_effect = error

        cognito_client = CognitoIdpClient()

        with pytest.raises(ClientError):
            cognito_client.admin_create_user(
                user_pool_id=self.user_pool_id,
                username=self.username,
                email=self.email,
                temporary_password=self.temporary_password,
            )

        mock_logger.error.assert_called_once_with(
            f"Error creating user '{self.username}': {error}"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_create_user_empty_response(
        self, mock_logger, mock_boto3_client
    ):
        """Test user creation with empty user data."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        mock_client.admin_create_user.return_value = {}

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_create_user(
            user_pool_id=self.user_pool_id,
            username=self.username,
            email=self.email,
            temporary_password=self.temporary_password,
        )

        assert result == {}

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_list_users_success(self, mock_logger, mock_boto3_client):
        """Test successful user listing."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        users_data = [
            {
                "Username": "user1",
                "UserStatus": "CONFIRMED",
                "Enabled": True,
                "Attributes": [
                    {"Name": "email", "Value": "user1@example.com"}
                ],
            },
            {
                "Username": "user2",
                "UserStatus": "CONFIRMED",
                "Enabled": True,
                "Attributes": [
                    {"Name": "email", "Value": "user2@example.com"}
                ],
            },
        ]
        mock_client.list_users.return_value = {"Users": users_data}

        cognito_client = CognitoIdpClient()
        result = cognito_client.list_users(user_pool_id=self.user_pool_id)

        mock_client.list_users.assert_called_once_with(
            UserPoolId=self.user_pool_id
        )
        assert result == users_data
        mock_logger.info.assert_called_once_with(
            f"Listing all users in user pool {self.user_pool_id}"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_list_users_empty(self, mock_logger, mock_boto3_client):
        """Test user listing with no users."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        mock_client.list_users.return_value = {"Users": []}

        cognito_client = CognitoIdpClient()
        result = cognito_client.list_users(user_pool_id=self.user_pool_id)

        assert result == []

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_list_users_client_error(self, mock_logger, mock_boto3_client):
        """Test user listing failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        error = ClientError(
            {
                "Error": {
                    "Code": "ResourceNotFoundException",
                    "Message": "User pool not found",
                }
            },
            "ListUsers",
        )
        mock_client.list_users.side_effect = error

        cognito_client = CognitoIdpClient()

        with pytest.raises(ClientError):
            cognito_client.list_users(user_pool_id=self.user_pool_id)

        mock_logger.error.assert_called_once_with(
            f"Error listing users: {error}"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_delete_user_success(self, mock_logger, mock_boto3_client):
        """Test successful user deletion."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        mock_client.admin_delete_user.return_value = {}

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_delete_user(
            user_pool_id=self.user_pool_id,
            username=self.username,
        )

        mock_client.admin_delete_user.assert_called_once_with(
            UserPoolId=self.user_pool_id,
            Username=self.username,
        )
        assert result is None
        mock_logger.info.assert_called_once_with(
            f"Deleting user '{self.username}' from pool {self.user_pool_id}"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_delete_user_client_error(
        self, mock_logger, mock_boto3_client
    ):
        """Test user deletion failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        error = ClientError(
            {
                "Error": {
                    "Code": "UserNotFoundException",
                    "Message": "User not found",
                }
            },
            "AdminDeleteUser",
        )
        mock_client.admin_delete_user.side_effect = error

        cognito_client = CognitoIdpClient()

        with pytest.raises(ClientError):
            cognito_client.admin_delete_user(
                user_pool_id=self.user_pool_id,
                username=self.username,
            )

        mock_logger.error.assert_called_once_with(
            f"Error deleting user '{self.username}': {error}"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_list_groups_for_user_success(
        self, mock_logger, mock_boto3_client
    ):
        """Test successful group listing for user."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        groups_data = [
            {
                "GroupName": "admin",
                "UserPoolId": self.user_pool_id,
                "Description": "Administrator group",
                "Precedence": 1,
            },
            {
                "GroupName": "user",
                "UserPoolId": self.user_pool_id,
                "Description": "Regular user group",
                "Precedence": 2,
            },
        ]
        mock_client.admin_list_groups_for_user.return_value = {
            "Groups": groups_data
        }

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_list_groups_for_user(
            user_pool_id=self.user_pool_id,
            username=self.username,
        )

        mock_client.admin_list_groups_for_user.assert_called_once_with(
            UserPoolId=self.user_pool_id,
            Username=self.username,
        )
        assert result == groups_data
        mock_logger.info.assert_called_once_with(
            f"Listing groups for user {self.username} in user pool {self.user_pool_id}"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_list_groups_for_user_empty(
        self, mock_logger, mock_boto3_client
    ):
        """Test group listing for user with no groups."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        mock_client.admin_list_groups_for_user.return_value = {"Groups": []}

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_list_groups_for_user(
            user_pool_id=self.user_pool_id,
            username=self.username,
        )

        assert result == []

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_list_groups_for_user_client_error(
        self, mock_logger, mock_boto3_client
    ):
        """Test group listing failure due to client error."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        error = ClientError(
            {
                "Error": {
                    "Code": "UserNotFoundException",
                    "Message": "User not found",
                }
            },
            "AdminListGroupsForUser",
        )
        mock_client.admin_list_groups_for_user.side_effect = error

        cognito_client = CognitoIdpClient()

        with pytest.raises(ClientError):
            cognito_client.admin_list_groups_for_user(
                user_pool_id=self.user_pool_id,
                username=self.username,
            )

        mock_logger.error.assert_called_once_with(
            f"Error listing groups for user: {error}"
        )

    @pytest.mark.parametrize(
        "user_pool_id,client_id,username,password",
        [
            ("us-east-1_ABC123", "client123", "user1", "Pass123!"),
            (
                "us-west-2_XYZ789",
                "client789",
                "user@example.com",
                "SecurePass456!",
            ),
            ("eu-west-1_DEF456", "clientABC", "testuser", "MyPassword789!"),
        ],
    )
    @patch("core.aws.cognito.boto3.client")
    def test_parameter_preservation(
        self, mock_boto3_client, user_pool_id, client_id, username, password
    ):
        """Test that all methods correctly preserve and use their parameters."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock responses
        mock_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": {"AccessToken": "token"}
        }
        mock_client.admin_create_user.return_value = {
            "User": {"Username": username}
        }
        mock_client.list_users.return_value = {"Users": []}
        mock_client.admin_delete_user.return_value = {}
        mock_client.admin_list_groups_for_user.return_value = {"Groups": []}

        cognito_client = CognitoIdpClient()

        # Test admin_initiate_auth parameter preservation
        cognito_client.admin_initiate_auth(
            user_pool_id=user_pool_id,
            client_id=client_id,
            username=username,
            password=password,
        )

        mock_client.admin_initiate_auth.assert_called_with(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
        )

        # Test admin_create_user parameter preservation
        email = f"{username}@example.com"
        temp_password = "TempPass123!"
        cognito_client.admin_create_user(
            user_pool_id=user_pool_id,
            username=username,
            email=email,
            temporary_password=temp_password,
        )

        mock_client.admin_create_user.assert_called_with(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
            ],
            TemporaryPassword=temp_password,
            MessageAction="SUPPRESS",
        )

        # Test list_users parameter preservation
        cognito_client.list_users(user_pool_id=user_pool_id)
        mock_client.list_users.assert_called_with(UserPoolId=user_pool_id)

        # Test admin_delete_user parameter preservation
        cognito_client.admin_delete_user(
            user_pool_id=user_pool_id,
            username=username,
        )
        mock_client.admin_delete_user.assert_called_with(
            UserPoolId=user_pool_id,
            Username=username,
        )

        # Test admin_list_groups_for_user parameter preservation
        cognito_client.admin_list_groups_for_user(
            user_pool_id=user_pool_id,
            username=username,
        )
        mock_client.admin_list_groups_for_user.assert_called_with(
            UserPoolId=user_pool_id,
            Username=username,
        )

    @patch("core.aws.cognito.boto3.client")
    def test_client_attribute_persistence(self, mock_boto3_client):
        """Test that the client attribute persists across method calls."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        cognito_client = CognitoIdpClient()

        # Verify client is stored correctly
        assert cognito_client.client == mock_client

        # Make multiple method calls and verify same client is used
        mock_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": {}
        }
        mock_client.list_users.return_value = {"Users": []}

        cognito_client.admin_initiate_auth(
            user_pool_id=self.user_pool_id,
            client_id=self.client_id,
            username=self.username,
            password=self.password,
        )
        cognito_client.list_users(user_pool_id=self.user_pool_id)

        # Verify both calls used the same client instance
        assert mock_client.admin_initiate_auth.called
        assert mock_client.list_users.called

    @patch("core.aws.cognito.boto3.client")
    def test_multiple_instances_independent(self, mock_boto3_client):
        """Test that multiple client instances are independent."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        mock_boto3_client.side_effect = [mock_client1, mock_client2]

        client1 = CognitoIdpClient(region_name="us-east-1")
        client2 = CognitoIdpClient(region_name="us-west-2")

        assert client1.client == mock_client1
        assert client2.client == mock_client2
        assert client1.client != client2.client

        # Verify both clients were created with correct regions
        assert mock_boto3_client.call_count == 2
        mock_boto3_client.assert_any_call(
            "cognito-idp", region_name="us-east-1"
        )
        mock_boto3_client.assert_any_call(
            "cognito-idp", region_name="us-west-2"
        )

    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_init_failure_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test initialization failure due to generic exception."""
        error = ValueError("Invalid configuration")
        mock_boto3_client.side_effect = error

        with pytest.raises(ValueError):
            CognitoIdpClient()

        mock_logger.exception.assert_called_once_with(
            f"Failed to initialize Boto3 Cognito IDP client: {error}"
        )

    @pytest.mark.parametrize(
        "auth_flow",
        [
            "ADMIN_NO_SRP_AUTH",
            "CUSTOM_AUTH",
            "USER_SRP_AUTH",
            "ALLOW_CUSTOM_AUTH",
        ],
    )
    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_admin_initiate_auth_various_auth_flows(
        self, mock_logger, mock_boto3_client, auth_flow
    ):
        """Test authentication with various auth flows."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        auth_result = {"AccessToken": "test-token"}
        mock_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": auth_result
        }

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_initiate_auth(
            user_pool_id=self.user_pool_id,
            client_id=self.client_id,
            username=self.username,
            password=self.password,
            auth_flow=auth_flow,
        )

        mock_client.admin_initiate_auth.assert_called_once_with(
            UserPoolId=self.user_pool_id,
            ClientId=self.client_id,
            AuthFlow=auth_flow,
            AuthParameters={
                "USERNAME": self.username,
                "PASSWORD": self.password,
            },
        )
        assert result == auth_result

    @pytest.mark.parametrize(
        "error_code,error_message,operation",
        [
            (
                "NotAuthorizedException",
                "Incorrect username or password",
                "AdminInitiateAuth",
            ),
            (
                "UserNotFoundException",
                "User does not exist",
                "AdminInitiateAuth",
            ),
            (
                "InvalidParameterException",
                "Invalid parameters",
                "AdminInitiateAuth",
            ),
            (
                "UsernameExistsException",
                "User already exists",
                "AdminCreateUser",
            ),
            (
                "InvalidPasswordException",
                "Invalid password",
                "AdminCreateUser",
            ),
            ("ResourceNotFoundException", "User pool not found", "ListUsers"),
            (
                "TooManyRequestsException",
                "Too many requests",
                "AdminDeleteUser",
            ),
        ],
    )
    @patch("core.aws.cognito.boto3.client")
    @patch("core.aws.cognito.logger")
    def test_various_client_errors(
        self,
        mock_logger,
        mock_boto3_client,
        error_code,
        error_message,
        operation,
    ):
        """Test various AWS client error scenarios."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        error = ClientError(
            {"Error": {"Code": error_code, "Message": error_message}},
            operation,
        )

        cognito_client = CognitoIdpClient()

        if operation == "AdminInitiateAuth":
            mock_client.admin_initiate_auth.side_effect = error
            with pytest.raises(ClientError) as exc_info:
                cognito_client.admin_initiate_auth(
                    user_pool_id=self.user_pool_id,
                    client_id=self.client_id,
                    username=self.username,
                    password=self.password,
                )
        elif operation == "AdminCreateUser":
            mock_client.admin_create_user.side_effect = error
            with pytest.raises(ClientError) as exc_info:
                cognito_client.admin_create_user(
                    user_pool_id=self.user_pool_id,
                    username=self.username,
                    email=self.email,
                    temporary_password=self.temporary_password,
                )
        elif operation == "ListUsers":
            mock_client.list_users.side_effect = error
            with pytest.raises(ClientError) as exc_info:
                cognito_client.list_users(user_pool_id=self.user_pool_id)
        elif operation == "AdminDeleteUser":
            mock_client.admin_delete_user.side_effect = error
            with pytest.raises(ClientError) as exc_info:
                cognito_client.admin_delete_user(
                    user_pool_id=self.user_pool_id,
                    username=self.username,
                )

        assert exc_info.value.response["Error"]["Code"] == error_code
        assert exc_info.value.response["Error"]["Message"] == error_message

    @patch("core.aws.cognito.boto3.client")
    def test_list_users_response_without_users_key(self, mock_boto3_client):
        """Test list_users when response doesn't contain Users key."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Response without Users key
        mock_client.list_users.return_value = {"Count": 0}

        cognito_client = CognitoIdpClient()
        result = cognito_client.list_users(user_pool_id=self.user_pool_id)

        assert result == []

    @patch("core.aws.cognito.boto3.client")
    def test_admin_create_user_response_without_user_key(
        self, mock_boto3_client
    ):
        """Test admin_create_user when response doesn't contain User key."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Response without User key
        mock_client.admin_create_user.return_value = {"ResponseMetadata": {}}

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_create_user(
            user_pool_id=self.user_pool_id,
            username=self.username,
            email=self.email,
            temporary_password=self.temporary_password,
        )

        assert result == {}

    @patch("core.aws.cognito.boto3.client")
    def test_admin_list_groups_for_user_response_without_groups_key(
        self, mock_boto3_client
    ):
        """Test admin_list_groups_for_user when response doesn't contain Groups key."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Response without Groups key
        mock_client.admin_list_groups_for_user.return_value = {
            "ResponseMetadata": {}
        }

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_list_groups_for_user(
            user_pool_id=self.user_pool_id,
            username=self.username,
        )

        assert result == []

    @patch("core.aws.cognito.boto3.client")
    def test_admin_initiate_auth_response_without_auth_result_key(
        self, mock_boto3_client
    ):
        """Test admin_initiate_auth when response doesn't contain AuthenticationResult key."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Response without AuthenticationResult key
        mock_client.admin_initiate_auth.return_value = {
            "ChallengeName": "NEW_PASSWORD_REQUIRED"
        }

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_initiate_auth(
            user_pool_id=self.user_pool_id,
            client_id=self.client_id,
            username=self.username,
            password=self.password,
        )

        assert result == {}

    @pytest.mark.parametrize(
        "client_metadata",
        [
            None,
            {},
            {"device": "mobile"},
            {"device": "desktop", "version": "2.0", "platform": "web"},
        ],
    )
    @patch("core.aws.cognito.boto3.client")
    def test_admin_initiate_auth_client_metadata_variations(
        self, mock_boto3_client, client_metadata
    ):
        """Test admin_initiate_auth with various client metadata scenarios."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        auth_result = {"AccessToken": "test-token"}
        mock_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": auth_result
        }

        cognito_client = CognitoIdpClient()
        result = cognito_client.admin_initiate_auth(
            user_pool_id=self.user_pool_id,
            client_id=self.client_id,
            username=self.username,
            password=self.password,
            client_metadata=client_metadata,
        )

        # Build expected call arguments
        expected_args = {
            "UserPoolId": self.user_pool_id,
            "ClientId": self.client_id,
            "AuthFlow": "ADMIN_NO_SRP_AUTH",
            "AuthParameters": {
                "USERNAME": self.username,
                "PASSWORD": self.password,
            },
        }

        # Add ClientMetadata only if it's not None and not empty
        if client_metadata:
            expected_args["ClientMetadata"] = client_metadata

        mock_client.admin_initiate_auth.assert_called_once_with(
            **expected_args
        )
        assert result == auth_result
