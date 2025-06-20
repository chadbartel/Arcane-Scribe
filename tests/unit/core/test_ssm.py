"""Unit tests for the ssm module."""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from botocore.exceptions import ClientError, NoCredentialsError

# Local Modules
from core.aws.ssm import SsmClient


class TestSsmClient:
    """Test cases for the SsmClient class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.parameter_name = "/app/config/database_url"
        self.parameter_value = "postgresql://user:pass@localhost:5432/db"
        self.encrypted_parameter_name = "/app/secrets/api_key"
        self.encrypted_parameter_value = "super-secret-api-key-12345"
        self.parameter_names = [
            "/app/config/debug_mode",
            "/app/config/log_level",
            "/app/config/timeout",
        ]
        self.parameter_values = {
            "/app/config/debug_mode": "true",
            "/app/config/log_level": "INFO",
            "/app/config/timeout": "30",
        }

    @patch("core.aws.ssm.boto3.client")
    def test_init_success_with_region(self, mock_boto3_client):
        """Test successful initialization with region_name."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        region_name = "us-west-2"

        ssm_client = SsmClient(region_name=region_name)

        mock_boto3_client.assert_called_once_with(
            "ssm", region_name=region_name
        )
        assert ssm_client.client == mock_client

    @patch("core.aws.ssm.boto3.client")
    def test_init_success_without_region(self, mock_boto3_client):
        """Test successful initialization without region_name."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        ssm_client = SsmClient()

        mock_boto3_client.assert_called_once_with("ssm", region_name=None)
        assert ssm_client.client == mock_client

    @patch("core.aws.ssm.boto3.client")
    @patch("core.aws.ssm.logger")
    def test_init_failure_no_credentials(self, mock_logger, mock_boto3_client):
        """Test initialization failure due to missing credentials."""
        error = NoCredentialsError()
        mock_boto3_client.side_effect = error

        with pytest.raises(NoCredentialsError):
            SsmClient()

        mock_logger.error.assert_called_once_with(
            "Failed to create SSM client: %s", error
        )

    @patch("core.aws.ssm.boto3.client")
    @patch("core.aws.ssm.logger")
    def test_init_failure_client_error(self, mock_logger, mock_boto3_client):
        """Test initialization failure due to AWS client error."""
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "CreateClient",
        )
        mock_boto3_client.side_effect = error

        with pytest.raises(ClientError):
            SsmClient()

        mock_logger.error.assert_called_once_with(
            "Failed to create SSM client: %s", error
        )

    @patch("core.aws.ssm.boto3.client")
    @patch("core.aws.ssm.logger")
    def test_init_failure_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test initialization failure due to generic exception."""
        error = ValueError("Invalid configuration")
        mock_boto3_client.side_effect = error

        with pytest.raises(ValueError):
            SsmClient()

        mock_logger.error.assert_called_once_with(
            "Failed to create SSM client: %s", error
        )

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameter_success_without_decryption(self, mock_boto3_client):
        """Test successful parameter retrieval without decryption."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_response = {
            "Parameter": {
                "Name": self.parameter_name,
                "Type": "String",
                "Value": self.parameter_value,
                "Version": 1,
            }
        }
        mock_client.get_parameter.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameter(self.parameter_name)

        mock_client.get_parameter.assert_called_once_with(
            Name=self.parameter_name, WithDecryption=False
        )
        assert result == self.parameter_value

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameter_success_with_decryption(self, mock_boto3_client):
        """Test successful parameter retrieval with decryption."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_response = {
            "Parameter": {
                "Name": self.encrypted_parameter_name,
                "Type": "SecureString",
                "Value": self.encrypted_parameter_value,
                "Version": 1,
            }
        }
        mock_client.get_parameter.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameter(
            self.encrypted_parameter_name, with_decryption=True
        )

        mock_client.get_parameter.assert_called_once_with(
            Name=self.encrypted_parameter_name, WithDecryption=True
        )
        assert result == self.encrypted_parameter_value

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameter_success_empty_response(self, mock_boto3_client):
        """Test parameter retrieval with empty response."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_response = {}  # Empty response
        mock_client.get_parameter.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameter(self.parameter_name)

        mock_client.get_parameter.assert_called_once_with(
            Name=self.parameter_name, WithDecryption=False
        )
        assert result is None

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameter_success_missing_parameter_key(
        self, mock_boto3_client
    ):
        """Test parameter retrieval with missing Parameter key."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_response = {"SomeOtherKey": "value"}  # Missing Parameter key
        mock_client.get_parameter.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameter(self.parameter_name)

        mock_client.get_parameter.assert_called_once_with(
            Name=self.parameter_name, WithDecryption=False
        )
        assert result is None

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameter_success_missing_value_key(self, mock_boto3_client):
        """Test parameter retrieval with missing Value key."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_response = {
            "Parameter": {
                "Name": self.parameter_name,
                "Type": "String",
                # Missing Value key
            }
        }
        mock_client.get_parameter.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameter(self.parameter_name)

        mock_client.get_parameter.assert_called_once_with(
            Name=self.parameter_name, WithDecryption=False
        )
        assert result is None

    @patch("core.aws.ssm.boto3.client")
    @patch("core.aws.ssm.logger")
    def test_get_parameter_client_error_parameter_not_found(
        self, mock_logger, mock_boto3_client
    ):
        """Test get_parameter failure due to parameter not found."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {
                "Error": {
                    "Code": "ParameterNotFound",
                    "Message": "Parameter not found",
                }
            },
            "GetParameter",
        )
        mock_client.get_parameter.side_effect = error

        ssm_client = SsmClient()
        result = ssm_client.get_parameter(self.parameter_name)

        mock_client.get_parameter.assert_called_once_with(
            Name=self.parameter_name, WithDecryption=False
        )
        mock_logger.error.assert_called_once_with(
            f"Failed to get parameter {self.parameter_name}: {error}"
        )
        assert result is None

    @patch("core.aws.ssm.boto3.client")
    @patch("core.aws.ssm.logger")
    def test_get_parameter_client_error_access_denied(
        self, mock_logger, mock_boto3_client
    ):
        """Test get_parameter failure due to access denied."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "GetParameter",
        )
        mock_client.get_parameter.side_effect = error

        ssm_client = SsmClient()
        result = ssm_client.get_parameter(
            self.encrypted_parameter_name, with_decryption=True
        )

        mock_client.get_parameter.assert_called_once_with(
            Name=self.encrypted_parameter_name, WithDecryption=True
        )
        mock_logger.error.assert_called_once_with(
            f"Failed to get parameter {self.encrypted_parameter_name}: {error}"
        )
        assert result is None

    @patch("core.aws.ssm.boto3.client")
    @patch("core.aws.ssm.logger")
    def test_get_parameter_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test get_parameter failure due to generic exception."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ValueError("Invalid parameter name")
        mock_client.get_parameter.side_effect = error

        ssm_client = SsmClient()

        with pytest.raises(ValueError):
            ssm_client.get_parameter(self.parameter_name)

        mock_client.get_parameter.assert_called_once_with(
            Name=self.parameter_name, WithDecryption=False
        )

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameters_success_without_decryption(
        self, mock_boto3_client
    ):
        """Test successful multiple parameters retrieval without decryption."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_response = {
            "Parameters": [
                {
                    "Name": "/app/config/debug_mode",
                    "Type": "String",
                    "Value": "true",
                    "Version": 1,
                },
                {
                    "Name": "/app/config/log_level",
                    "Type": "String",
                    "Value": "INFO",
                    "Version": 1,
                },
                {
                    "Name": "/app/config/timeout",
                    "Type": "String",
                    "Value": "30",
                    "Version": 1,
                },
            ],
            "InvalidParameters": [],
        }
        mock_client.get_parameters.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameters(self.parameter_names)

        mock_client.get_parameters.assert_called_once_with(
            Names=self.parameter_names, WithDecryption=False
        )
        assert result == self.parameter_values

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameters_success_with_decryption(self, mock_boto3_client):
        """Test successful multiple parameters retrieval with decryption."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        encrypted_names = ["/app/secrets/db_password", "/app/secrets/api_key"]
        mock_response = {
            "Parameters": [
                {
                    "Name": "/app/secrets/db_password",
                    "Type": "SecureString",
                    "Value": "encrypted-db-password",
                    "Version": 1,
                },
                {
                    "Name": "/app/secrets/api_key",
                    "Type": "SecureString",
                    "Value": "encrypted-api-key",
                    "Version": 1,
                },
            ],
            "InvalidParameters": [],
        }
        mock_client.get_parameters.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameters(
            encrypted_names, with_decryption=True
        )

        mock_client.get_parameters.assert_called_once_with(
            Names=encrypted_names, WithDecryption=True
        )
        expected_result = {
            "/app/secrets/db_password": "encrypted-db-password",
            "/app/secrets/api_key": "encrypted-api-key",
        }
        assert result == expected_result

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameters_success_partial_response(self, mock_boto3_client):
        """Test multiple parameters retrieval with partial response."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_response = {
            "Parameters": [
                {
                    "Name": "/app/config/debug_mode",
                    "Type": "String",
                    "Value": "true",
                    "Version": 1,
                },
                # Missing other parameters
            ],
            "InvalidParameters": [
                "/app/config/log_level",
                "/app/config/timeout",
            ],
        }
        mock_client.get_parameters.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameters(self.parameter_names)

        mock_client.get_parameters.assert_called_once_with(
            Names=self.parameter_names, WithDecryption=False
        )
        expected_result = {"/app/config/debug_mode": "true"}
        assert result == expected_result

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameters_success_empty_response(self, mock_boto3_client):
        """Test multiple parameters retrieval with empty response."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_response = {}  # Empty response
        mock_client.get_parameters.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameters(self.parameter_names)

        mock_client.get_parameters.assert_called_once_with(
            Names=self.parameter_names, WithDecryption=False
        )
        assert result == {}

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameters_success_missing_parameters_key(
        self, mock_boto3_client
    ):
        """Test multiple parameters retrieval with missing Parameters key."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_response = {"InvalidParameters": []}  # Missing Parameters key
        mock_client.get_parameters.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameters(self.parameter_names)

        mock_client.get_parameters.assert_called_once_with(
            Names=self.parameter_names, WithDecryption=False
        )
        assert result == {}

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameters_success_empty_list(self, mock_boto3_client):
        """Test multiple parameters retrieval with empty parameter list."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_response = {"Parameters": [], "InvalidParameters": []}
        mock_client.get_parameters.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameters([])

        mock_client.get_parameters.assert_called_once_with(
            Names=[], WithDecryption=False
        )
        assert result == {}

    @patch("core.aws.ssm.boto3.client")
    def test_get_parameters_success_missing_value_in_parameter(
        self, mock_boto3_client
    ):
        """Test multiple parameters retrieval with missing Value in parameter."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_response = {
            "Parameters": [
                {
                    "Name": "/app/config/debug_mode",
                    "Type": "String",
                    "Value": "true",
                    "Version": 1,
                },
                {
                    "Name": "/app/config/log_level",
                    "Type": "String",
                    # Missing Value key
                    "Version": 1,
                },
            ],
            "InvalidParameters": [],
        }
        mock_client.get_parameters.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameters(self.parameter_names[:2])

        mock_client.get_parameters.assert_called_once_with(
            Names=self.parameter_names[:2], WithDecryption=False
        )
        expected_result = {
            "/app/config/debug_mode": "true",
            "/app/config/log_level": None,
        }
        assert result == expected_result

    @patch("core.aws.ssm.boto3.client")
    @patch("core.aws.ssm.logger")
    def test_get_parameters_client_error_access_denied(
        self, mock_logger, mock_boto3_client
    ):
        """Test get_parameters failure due to access denied."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "GetParameters",
        )
        mock_client.get_parameters.side_effect = error

        ssm_client = SsmClient()
        result = ssm_client.get_parameters(self.parameter_names)

        mock_client.get_parameters.assert_called_once_with(
            Names=self.parameter_names, WithDecryption=False
        )
        mock_logger.error.assert_called_once_with(
            f"Failed to get parameters {self.parameter_names}: {error}"
        )
        expected_result = {name: None for name in self.parameter_names}
        assert result == expected_result

    @patch("core.aws.ssm.boto3.client")
    @patch("core.aws.ssm.logger")
    def test_get_parameters_client_error_invalid_parameter_name(
        self, mock_logger, mock_boto3_client
    ):
        """Test get_parameters failure due to invalid parameter name."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {
                "Error": {
                    "Code": "ParameterNotFound",
                    "Message": "Parameter not found",
                }
            },
            "GetParameters",
        )
        mock_client.get_parameters.side_effect = error

        ssm_client = SsmClient()
        result = ssm_client.get_parameters(
            self.parameter_names, with_decryption=True
        )

        mock_client.get_parameters.assert_called_once_with(
            Names=self.parameter_names, WithDecryption=True
        )
        mock_logger.error.assert_called_once_with(
            f"Failed to get parameters {self.parameter_names}: {error}"
        )
        expected_result = {name: None for name in self.parameter_names}
        assert result == expected_result

    @patch("core.aws.ssm.boto3.client")
    @patch("core.aws.ssm.logger")
    def test_get_parameters_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test get_parameters failure due to generic exception."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = TypeError("Invalid parameter list type")
        mock_client.get_parameters.side_effect = error

        ssm_client = SsmClient()

        with pytest.raises(TypeError):
            ssm_client.get_parameters(self.parameter_names)

        mock_client.get_parameters.assert_called_once_with(
            Names=self.parameter_names, WithDecryption=False
        )

    @pytest.mark.parametrize(
        "parameter_name,with_decryption",
        [
            ("/app/config/database_url", False),
            ("/app/secrets/api_key", True),
            ("/prod/config/timeout", False),
            ("/dev/secrets/password", True),
        ],
    )
    @patch("core.aws.ssm.boto3.client")
    def test_get_parameter_various_combinations(
        self, mock_boto3_client, parameter_name, with_decryption
    ):
        """Test get_parameter with various parameter combinations."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        parameter_value = f"value-for-{parameter_name.split('/')[-1]}"
        mock_response = {
            "Parameter": {
                "Name": parameter_name,
                "Type": "SecureString" if with_decryption else "String",
                "Value": parameter_value,
                "Version": 1,
            }
        }
        mock_client.get_parameter.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameter(
            parameter_name, with_decryption=with_decryption
        )

        mock_client.get_parameter.assert_called_once_with(
            Name=parameter_name, WithDecryption=with_decryption
        )
        assert result == parameter_value

    @pytest.mark.parametrize(
        "parameter_names,with_decryption",
        [
            (["/app/config/debug"], False),
            (["/app/secrets/key1", "/app/secrets/key2"], True),
            (
                [
                    "/prod/config/val1",
                    "/prod/config/val2",
                    "/prod/config/val3",
                ],
                False,
            ),
            ([], False),
        ],
    )
    @patch("core.aws.ssm.boto3.client")
    def test_get_parameters_various_combinations(
        self, mock_boto3_client, parameter_names, with_decryption
    ):
        """Test get_parameters with various parameter combinations."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_parameters = [
            {
                "Name": name,
                "Type": "SecureString" if with_decryption else "String",
                "Value": f"value-{name.split('/')[-1]}",
                "Version": 1,
            }
            for name in parameter_names
        ]
        mock_response = {
            "Parameters": mock_parameters,
            "InvalidParameters": [],
        }
        mock_client.get_parameters.return_value = mock_response

        ssm_client = SsmClient()
        result = ssm_client.get_parameters(
            parameter_names, with_decryption=with_decryption
        )

        mock_client.get_parameters.assert_called_once_with(
            Names=parameter_names, WithDecryption=with_decryption
        )
        expected_result = {
            name: f"value-{name.split('/')[-1]}" for name in parameter_names
        }
        assert result == expected_result

    @patch("core.aws.ssm.boto3.client")
    def test_multiple_instances_independent(self, mock_boto3_client):
        """Test that multiple SsmClient instances are independent."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        mock_boto3_client.side_effect = [mock_client1, mock_client2]

        ssm_client1 = SsmClient(region_name="us-east-1")
        ssm_client2 = SsmClient(region_name="us-west-2")

        assert ssm_client1.client == mock_client1
        assert ssm_client2.client == mock_client2
        assert ssm_client1.client != ssm_client2.client

        # Verify boto3.client was called with correct regions
        assert mock_boto3_client.call_count == 2
        mock_boto3_client.assert_any_call("ssm", region_name="us-east-1")
        mock_boto3_client.assert_any_call("ssm", region_name="us-west-2")

    @pytest.mark.parametrize(
        "error_code,error_message,operation",
        [
            ("ParameterNotFound", "Parameter not found", "GetParameter"),
            ("AccessDenied", "Access denied", "GetParameter"),
            ("InvalidKeyId.NotFound", "KMS key not found", "GetParameter"),
            (
                "ParameterMaxVersionLimitExceeded",
                "Version limit exceeded",
                "GetParameter",
            ),
            ("TooManyUpdates", "Too many updates", "GetParameters"),
            (
                "ParameterLimitExceeded",
                "Parameter limit exceeded",
                "GetParameters",
            ),
            ("InvalidFilterKey", "Invalid filter key", "GetParameters"),
        ],
    )
    @patch("core.aws.ssm.boto3.client")
    @patch("core.aws.ssm.logger")
    def test_various_client_errors(
        self,
        mock_logger,
        mock_boto3_client,
        error_code,
        error_message,
        operation,
    ):
        """Test various AWS SSM client errors."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": error_code, "Message": error_message}},
            operation,
        )

        if operation == "GetParameter":
            mock_client.get_parameter.side_effect = error
        else:
            mock_client.get_parameters.side_effect = error

        ssm_client = SsmClient()

        if operation == "GetParameter":
            result = ssm_client.get_parameter(self.parameter_name)
            mock_logger.error.assert_called_once_with(
                f"Failed to get parameter {self.parameter_name}: {error}"
            )
            assert result is None
        else:
            result = ssm_client.get_parameters(self.parameter_names)
            mock_logger.error.assert_called_once_with(
                f"Failed to get parameters {self.parameter_names}: {error}"
            )
            expected_result = {name: None for name in self.parameter_names}
            assert result == expected_result

    @patch("core.aws.ssm.boto3.client")
    def test_client_attribute_persistence(self, mock_boto3_client):
        """Test that the client attribute persists correctly."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        ssm_client = SsmClient()

        # Verify client attribute is set and persistent
        assert ssm_client.client == mock_client
        assert ssm_client.client is mock_client

        # Call methods to ensure client is used consistently
        mock_client.get_parameter.return_value = {
            "Parameter": {"Name": "test", "Value": "value"}
        }
        ssm_client.get_parameter("test")

        mock_client.get_parameters.return_value = {"Parameters": []}
        ssm_client.get_parameters(["test"])

        # Verify the same client instance was used
        assert ssm_client.client == mock_client

    @pytest.mark.parametrize(
        "region_name",
        [
            None,
            "us-east-1",
            "us-west-2",
            "eu-west-1",
            "ap-southeast-1",
        ],
    )
    @patch("core.aws.ssm.boto3.client")
    def test_region_name_handling(self, mock_boto3_client, region_name):
        """Test initialization with various region names."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        if region_name is None:
            ssm_client = SsmClient()
        else:
            ssm_client = SsmClient(region_name=region_name)

        mock_boto3_client.assert_called_once_with(
            "ssm", region_name=region_name
        )
        assert ssm_client.client == mock_client
