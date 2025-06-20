"""Unit tests for the dynamodb module."""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from botocore.exceptions import ClientError, NoCredentialsError

# Local Modules
from core.aws.dynamodb import DynamoDb


class TestDynamoDb:
    """Test cases for the DynamoDb class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.table_name = "test-table"
        self.test_item = {
            "id": "test-id-123",
            "name": "Test Item",
            "value": 42,
            "active": True,
        }
        self.test_key = {"id": "test-id-123"}

    @patch("core.aws.dynamodb.boto3.resource")
    def test_init_success(self, mock_boto3_resource):
        """Test successful initialization of DynamoDb."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        dynamodb = DynamoDb(self.table_name)

        mock_boto3_resource.assert_called_once_with("dynamodb")
        mock_dynamodb_resource.Table.assert_called_once_with(self.table_name)
        assert dynamodb.table_name == self.table_name
        assert dynamodb._dynamodb == mock_dynamodb_resource
        assert dynamodb._table == mock_table

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_init_failure_no_credentials(
        self, mock_logger, mock_boto3_resource
    ):
        """Test initialization failure due to missing credentials."""
        error = NoCredentialsError()
        mock_boto3_resource.side_effect = error

        with pytest.raises(NoCredentialsError):
            DynamoDb(self.table_name)

        mock_logger.error.assert_called_once_with(
            "Failed to create DynamoDB client for table %s: %s",
            self.table_name,
            error,
        )

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_init_failure_generic_exception(
        self, mock_logger, mock_boto3_resource
    ):
        """Test initialization failure due to generic exception."""
        error = ValueError("Invalid configuration")
        mock_boto3_resource.side_effect = error

        with pytest.raises(ValueError):
            DynamoDb(self.table_name)

        mock_logger.error.assert_called_once_with(
            "Failed to create DynamoDB client for table %s: %s",
            self.table_name,
            error,
        )

    @patch("core.aws.dynamodb.boto3.resource")
    def test_put_item_success(self, mock_boto3_resource):
        """Test successful item insertion."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        expected_response = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "ConsumedCapacity": {
                "TableName": self.table_name,
                "CapacityUnits": 1,
            },
        }
        mock_table.put_item.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.put_item(self.test_item)

        mock_table.put_item.assert_called_once_with(Item=self.test_item)
        assert result == expected_response

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_put_item_client_error(self, mock_logger, mock_boto3_resource):
        """Test put_item failure due to client error."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = ClientError(
            {
                "Error": {
                    "Code": "ValidationException",
                    "Message": "Invalid item",
                }
            },
            "PutItem",
        )
        mock_table.put_item.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(ClientError):
            dynamodb.put_item(self.test_item)

        mock_logger.error.assert_called_once_with(
            "Failed to put item in table %s: %s",
            self.table_name,
            "Invalid item",
        )

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_put_item_generic_exception(
        self, mock_logger, mock_boto3_resource
    ):
        """Test put_item failure due to generic exception."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = ValueError("Invalid data type")
        mock_table.put_item.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(ValueError):
            dynamodb.put_item(self.test_item)

        mock_logger.error.assert_called_once_with(
            "Unexpected error putting item in table %s: %s",
            self.table_name,
            str(error),
        )

    @patch("core.aws.dynamodb.boto3.resource")
    def test_get_item_success_found(self, mock_boto3_resource):
        """Test successful item retrieval when item exists."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        expected_response = {
            "Item": self.test_item,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.get_item.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.get_item(self.test_key)

        mock_table.get_item.assert_called_once_with(Key=self.test_key)
        assert result == self.test_item

    @patch("core.aws.dynamodb.boto3.resource")
    def test_get_item_success_not_found(self, mock_boto3_resource):
        """Test successful item retrieval when item does not exist."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        expected_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        mock_table.get_item.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.get_item(self.test_key)

        mock_table.get_item.assert_called_once_with(Key=self.test_key)
        assert result is None

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_get_item_client_error(self, mock_logger, mock_boto3_resource):
        """Test get_item failure due to client error."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = ClientError(
            {
                "Error": {
                    "Code": "ResourceNotFoundException",
                    "Message": "Table not found",
                }
            },
            "GetItem",
        )
        mock_table.get_item.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(ClientError):
            dynamodb.get_item(self.test_key)

        mock_logger.error.assert_called_once_with(
            "Failed to get item from table %s: %s",
            self.table_name,
            "Table not found",
        )

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_get_item_generic_exception(
        self, mock_logger, mock_boto3_resource
    ):
        """Test get_item failure due to generic exception."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = TypeError("Invalid key type")
        mock_table.get_item.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(TypeError):
            dynamodb.get_item(self.test_key)

        mock_logger.error.assert_called_once_with(
            "Unexpected error getting item from table %s: %s",
            self.table_name,
            str(error),
        )

    @patch("core.aws.dynamodb.boto3.resource")
    def test_update_item_success_with_all_parameters(
        self, mock_boto3_resource
    ):
        """Test successful item update with all optional parameters."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        update_expression = "SET #name = :name, #value = :value"
        expression_attribute_values = {":name": "Updated Name", ":value": 100}
        expression_attribute_names = {"#name": "name", "#value": "value"}

        expected_response = {
            "Attributes": {
                "id": "test-id-123",
                "name": "Updated Name",
                "value": 100,
            },
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.update_item.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.update_item(
            key=self.test_key,
            update_expression=update_expression,
            expression_attribute_values=expression_attribute_values,
            expression_attribute_names=expression_attribute_names,
        )

        expected_params = {
            "Key": self.test_key,
            "UpdateExpression": update_expression,
            "ReturnValues": "ALL_NEW",
            "ExpressionAttributeValues": expression_attribute_values,
            "ExpressionAttributeNames": expression_attribute_names,
        }
        mock_table.update_item.assert_called_once_with(**expected_params)
        assert result == expected_response

    @patch("core.aws.dynamodb.boto3.resource")
    def test_update_item_success_minimal_parameters(self, mock_boto3_resource):
        """Test successful item update with only required parameters."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        update_expression = "SET #name = :name"
        expected_response = {
            "Attributes": {"id": "test-id-123", "name": "Updated Name"},
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.update_item.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.update_item(
            key=self.test_key,
            update_expression=update_expression,
        )

        expected_params = {
            "Key": self.test_key,
            "UpdateExpression": update_expression,
            "ReturnValues": "ALL_NEW",
        }
        mock_table.update_item.assert_called_once_with(**expected_params)
        assert result == expected_response

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_update_item_client_error(self, mock_logger, mock_boto3_resource):
        """Test update_item failure due to client error."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = ClientError(
            {
                "Error": {
                    "Code": "ConditionalCheckFailedException",
                    "Message": "Condition failed",
                }
            },
            "UpdateItem",
        )
        mock_table.update_item.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(ClientError):
            dynamodb.update_item(
                key=self.test_key,
                update_expression="SET #name = :name",
            )

        mock_logger.error.assert_called_once_with(
            "Failed to update item in table %s: %s",
            self.table_name,
            "Condition failed",
        )

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_update_item_generic_exception(
        self, mock_logger, mock_boto3_resource
    ):
        """Test update_item failure due to generic exception."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = ValueError("Invalid update expression")
        mock_table.update_item.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(ValueError):
            dynamodb.update_item(
                key=self.test_key,
                update_expression="INVALID EXPRESSION",
            )

        mock_logger.error.assert_called_once_with(
            "Unexpected error updating item in table %s: %s",
            self.table_name,
            str(error),
        )

    @patch("core.aws.dynamodb.boto3.resource")
    def test_delete_item_success(self, mock_boto3_resource):
        """Test successful item deletion."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        expected_response = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "ConsumedCapacity": {
                "TableName": self.table_name,
                "CapacityUnits": 1,
            },
        }
        mock_table.delete_item.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.delete_item(self.test_key)

        mock_table.delete_item.assert_called_once_with(Key=self.test_key)
        assert result == expected_response

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_delete_item_client_error(self, mock_logger, mock_boto3_resource):
        """Test delete_item failure due to client error."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = ClientError(
            {
                "Error": {
                    "Code": "ItemNotFoundException",
                    "Message": "Item not found",
                }
            },
            "DeleteItem",
        )
        mock_table.delete_item.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(ClientError):
            dynamodb.delete_item(self.test_key)

        mock_logger.error.assert_called_once_with(
            "Failed to delete item from table %s: %s",
            self.table_name,
            "Item not found",
        )

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_delete_item_generic_exception(
        self, mock_logger, mock_boto3_resource
    ):
        """Test delete_item failure due to generic exception."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = KeyError("Missing required key")
        mock_table.delete_item.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(KeyError):
            dynamodb.delete_item(self.test_key)

        mock_logger.error.assert_called_once_with(
            "Unexpected error deleting item from table %s: %s",
            self.table_name,
            str(error),
        )

    @patch("core.aws.dynamodb.boto3.resource")
    def test_scan_success_no_parameters(self, mock_boto3_resource):
        """Test successful table scan with no optional parameters."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        expected_response = {
            "Items": [
                self.test_item,
                {"id": "test-id-456", "name": "Another Item"},
            ],
            "Count": 2,
            "ScannedCount": 2,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.scan.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.scan()

        mock_table.scan.assert_called_once_with()
        assert result == expected_response

    @patch("core.aws.dynamodb.boto3.resource")
    def test_scan_success_with_filter_expression(self, mock_boto3_resource):
        """Test successful table scan with filter expression."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        filter_expression = (
            MagicMock()
        )  # Simulating boto3.dynamodb.conditions.Attr
        expected_response = {
            "Items": [self.test_item],
            "Count": 1,
            "ScannedCount": 5,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.scan.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.scan(filter_expression=filter_expression)

        mock_table.scan.assert_called_once_with(
            FilterExpression=filter_expression
        )
        assert result == expected_response

    @patch("core.aws.dynamodb.boto3.resource")
    def test_scan_success_with_projection_expression(
        self, mock_boto3_resource
    ):
        """Test successful table scan with projection expression."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        projection_expression = "id, #name"
        expected_response = {
            "Items": [{"id": "test-id-123", "name": "Test Item"}],
            "Count": 1,
            "ScannedCount": 1,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.scan.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.scan(projection_expression=projection_expression)

        mock_table.scan.assert_called_once_with(
            ProjectionExpression=projection_expression
        )
        assert result == expected_response

    @patch("core.aws.dynamodb.boto3.resource")
    def test_scan_success_with_all_parameters(self, mock_boto3_resource):
        """Test successful table scan with all optional parameters."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        filter_expression = MagicMock()
        projection_expression = "id, #name"
        expected_response = {
            "Items": [{"id": "test-id-123", "name": "Test Item"}],
            "Count": 1,
            "ScannedCount": 3,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.scan.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.scan(
            filter_expression=filter_expression,
            projection_expression=projection_expression,
        )

        expected_params = {
            "FilterExpression": filter_expression,
            "ProjectionExpression": projection_expression,
        }
        mock_table.scan.assert_called_once_with(**expected_params)
        assert result == expected_response

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_scan_client_error(self, mock_logger, mock_boto3_resource):
        """Test scan failure due to client error."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = ClientError(
            {
                "Error": {
                    "Code": "ProvisionedThroughputExceededException",
                    "Message": "Rate exceeded",
                }
            },
            "Scan",
        )
        mock_table.scan.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(ClientError):
            dynamodb.scan()

        mock_logger.error.assert_called_once_with(
            "Failed to scan table %s: %s",
            self.table_name,
            "Rate exceeded",
        )

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_scan_generic_exception(self, mock_logger, mock_boto3_resource):
        """Test scan failure due to generic exception."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = MemoryError("Out of memory")
        mock_table.scan.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(MemoryError):
            dynamodb.scan()

        mock_logger.error.assert_called_once_with(
            "Unexpected error scanning table %s: %s",
            self.table_name,
            str(error),
        )

    @patch("core.aws.dynamodb.boto3.resource")
    def test_query_success_minimal_parameters(self, mock_boto3_resource):
        """Test successful table query with only required parameters."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        key_condition_expression = (
            MagicMock()
        )  # Simulating Key('id').eq('test-id')
        expected_response = {
            "Items": [self.test_item],
            "Count": 1,
            "ScannedCount": 1,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.query.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.query(
            key_condition_expression=key_condition_expression
        )

        expected_params = {"KeyConditionExpression": key_condition_expression}
        mock_table.query.assert_called_once_with(**expected_params)
        assert result == expected_response

    @patch("core.aws.dynamodb.boto3.resource")
    def test_query_success_with_all_parameters(self, mock_boto3_resource):
        """Test successful table query with all optional parameters."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        key_condition_expression = MagicMock()
        filter_expression = MagicMock()
        projection_expression = "id, #name, #value"
        limit = 10
        exclusive_start_key = {"id": "last-evaluated-key"}

        expected_response = {
            "Items": [self.test_item],
            "Count": 1,
            "ScannedCount": 1,
            "LastEvaluatedKey": {"id": "test-id-123"},
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.query.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.query(
            key_condition_expression=key_condition_expression,
            filter_expression=filter_expression,
            projection_expression=projection_expression,
            limit=limit,
            exclusive_start_key=exclusive_start_key,
        )

        expected_params = {
            "KeyConditionExpression": key_condition_expression,
            "ExclusiveStartKey": exclusive_start_key,
            "FilterExpression": filter_expression,
            "ProjectionExpression": projection_expression,
            "Limit": limit,
        }
        mock_table.query.assert_called_once_with(**expected_params)
        assert result == expected_response

    @patch("core.aws.dynamodb.boto3.resource")
    def test_query_success_with_some_parameters(self, mock_boto3_resource):
        """Test successful table query with some optional parameters."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        key_condition_expression = MagicMock()
        limit = 5
        expected_response = {
            "Items": [self.test_item],
            "Count": 1,
            "ScannedCount": 1,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.query.return_value = expected_response

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.query(
            key_condition_expression=key_condition_expression,
            limit=limit,
        )

        expected_params = {
            "KeyConditionExpression": key_condition_expression,
            "Limit": limit,
        }
        mock_table.query.assert_called_once_with(**expected_params)
        assert result == expected_response

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_query_client_error(self, mock_logger, mock_boto3_resource):
        """Test query failure due to client error."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = ClientError(
            {
                "Error": {
                    "Code": "ValidationException",
                    "Message": "Invalid key condition",
                }
            },
            "Query",
        )
        mock_table.query.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(ClientError):
            dynamodb.query(key_condition_expression=MagicMock())

        mock_logger.error.assert_called_once_with(
            "Failed to query table %s: %s",
            self.table_name,
            "Invalid key condition",
        )

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_query_generic_exception(self, mock_logger, mock_boto3_resource):
        """Test query failure due to generic exception."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = AttributeError("Invalid attribute")
        mock_table.query.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(AttributeError):
            dynamodb.query(key_condition_expression=MagicMock())

        mock_logger.error.assert_called_once_with(
            "Unexpected error querying table %s: %s",
            self.table_name,
            str(error),
        )

    @patch("core.aws.dynamodb.boto3.resource")
    def test_batch_write_success(self, mock_boto3_resource):
        """Test successful batch write operation."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_batch_writer = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table
        mock_table.batch_writer.return_value.__enter__.return_value = (
            mock_batch_writer
        )

        items = [
            {"id": "item1", "name": "Item 1"},
            {"id": "item2", "name": "Item 2"},
            {"id": "item3", "name": "Item 3"},
        ]

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.batch_write(items)

        # Verify batch writer was used correctly
        mock_table.batch_writer.assert_called_once()
        assert mock_batch_writer.put_item.call_count == 3
        mock_batch_writer.put_item.assert_any_call(Item=items[0])
        mock_batch_writer.put_item.assert_any_call(Item=items[1])
        mock_batch_writer.put_item.assert_any_call(Item=items[2])

        # Verify return value indicates no unprocessed items
        assert result == {"UnprocessedItems": {}}

    @patch("core.aws.dynamodb.boto3.resource")
    def test_batch_write_success_empty_list(self, mock_boto3_resource):
        """Test successful batch write with empty items list."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_batch_writer = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table
        mock_table.batch_writer.return_value.__enter__.return_value = (
            mock_batch_writer
        )

        items = []

        dynamodb = DynamoDb(self.table_name)
        result = dynamodb.batch_write(items)

        # Verify batch writer was used but no items were added
        mock_table.batch_writer.assert_called_once()
        mock_batch_writer.put_item.assert_not_called()

        assert result == {"UnprocessedItems": {}}

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_batch_write_client_error(self, mock_logger, mock_boto3_resource):
        """Test batch_write failure due to client error."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = ClientError(
            {
                "Error": {
                    "Code": "ProvisionedThroughputExceededException",
                    "Message": "Throughput exceeded",
                }
            },
            "BatchWriteItem",
        )
        mock_table.batch_writer.side_effect = error

        items = [{"id": "item1", "name": "Item 1"}]

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(ClientError):
            dynamodb.batch_write(items)

        mock_logger.error.assert_called_once_with(
            "Failed to batch write to table %s: %s",
            self.table_name,
            "Throughput exceeded",
        )

    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_batch_write_generic_exception(
        self, mock_logger, mock_boto3_resource
    ):
        """Test batch_write failure due to generic exception."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = RuntimeError("Unexpected runtime error")
        mock_table.batch_writer.side_effect = error

        items = [{"id": "item1", "name": "Item 1"}]

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(RuntimeError):
            dynamodb.batch_write(items)

        mock_logger.error.assert_called_once_with(
            "Unexpected error during batch write to table %s: %s",
            self.table_name,
            str(error),
        )

    @pytest.mark.parametrize(
        "table_name",
        [
            "test-table-1",
            "production-users-table",
            "dev_documents_2024",
            "staging.events.table",
        ],
    )
    @patch("core.aws.dynamodb.boto3.resource")
    def test_table_name_preservation(self, mock_boto3_resource, table_name):
        """Test that table name is correctly preserved across all operations."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        # Mock responses for all methods
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }
        mock_table.get_item.return_value = {"Item": self.test_item}
        mock_table.update_item.return_value = {"Attributes": self.test_item}
        mock_table.delete_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }
        mock_table.scan.return_value = {"Items": [self.test_item]}
        mock_table.query.return_value = {"Items": [self.test_item]}

        dynamodb = DynamoDb(table_name)

        # Verify table name is stored correctly
        assert dynamodb.table_name == table_name

        # Verify boto3 resource was called with correct table name
        mock_dynamodb_resource.Table.assert_called_once_with(table_name)

    @patch("core.aws.dynamodb.boto3.resource")
    def test_multiple_instances_independent(self, mock_boto3_resource):
        """Test that multiple DynamoDb instances are independent."""
        mock_dynamodb_resource1 = MagicMock()
        mock_dynamodb_resource2 = MagicMock()
        mock_table1 = MagicMock()
        mock_table2 = MagicMock()

        mock_boto3_resource.side_effect = [
            mock_dynamodb_resource1,
            mock_dynamodb_resource2,
        ]
        mock_dynamodb_resource1.Table.return_value = mock_table1
        mock_dynamodb_resource2.Table.return_value = mock_table2

        table1_name = "table1"
        table2_name = "table2"

        dynamodb1 = DynamoDb(table1_name)
        dynamodb2 = DynamoDb(table2_name)

        assert dynamodb1.table_name == table1_name
        assert dynamodb2.table_name == table2_name
        assert dynamodb1._table == mock_table1
        assert dynamodb2._table == mock_table2
        assert dynamodb1._table != dynamodb2._table

        mock_dynamodb_resource1.Table.assert_called_once_with(table1_name)
        mock_dynamodb_resource2.Table.assert_called_once_with(table2_name)

    @pytest.mark.parametrize(
        "error_response,expected_message",
        [
            (
                {
                    "Error": {
                        "Code": "ValidationException",
                        "Message": "Validation failed",
                    }
                },
                "Validation failed",
            ),
            ({"Error": {"Code": "ResourceNotFoundException"}}, ""),
            ({"Error": {}}, ""),
            ({}, ""),
        ],
    )
    @patch("core.aws.dynamodb.boto3.resource")
    @patch("core.aws.dynamodb.logger")
    def test_client_error_message_extraction(
        self,
        mock_logger,
        mock_boto3_resource,
        error_response,
        expected_message,
    ):
        """Test proper extraction of error messages from ClientError responses."""
        mock_dynamodb_resource = MagicMock()
        mock_table = MagicMock()
        mock_boto3_resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.Table.return_value = mock_table

        error = ClientError(error_response, "PutItem")
        mock_table.put_item.side_effect = error

        dynamodb = DynamoDb(self.table_name)

        with pytest.raises(ClientError):
            dynamodb.put_item(self.test_item)

        # Check that the error message extraction works correctly
        if expected_message:
            mock_logger.error.assert_called_with(
                "Failed to put item in table %s: %s",
                self.table_name,
                expected_message,
            )
        else:
            # When no message is available, should fall back to str(error)
            mock_logger.error.assert_called_with(
                "Failed to put item in table %s: %s",
                self.table_name,
                str(error),
            )
