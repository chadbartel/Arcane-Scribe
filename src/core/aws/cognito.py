"""Cognito client wrapper for AWS Cognito Identity Provider operations."""

# Standard Library
from typing import Dict, List, Optional, Union

# Third Party
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

# Initialize logger
logger = Logger(service="cognito-idp-client-wrapper")


class CognitoIdpClient:

    def __init__(self, region_name: Optional[str] = None) -> None:
        try:
            self.client = boto3.client("cognito-idp", region_name=region_name)
        except Exception as e:
            logger.exception(
                f"Failed to initialize Boto3 Cognito IDP client: {e}"
            )
            raise e

    def admin_initiate_auth(
        self,
        user_pool_id: str,
        client_id: str,
        username: str,
        password: str,
        auth_flow: Optional[str] = "ADMIN_NO_SRP_AUTH",
        client_metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """Initiates the authentication process for a user in a Cognito user
        pool.

        Parameters
        ----------
        user_pool_id : str
            The ID of the Cognito user pool.
        client_id : str
            The client ID of the Cognito app client.
        username : str
            The username of the user to authenticate.
        password : str
            The password of the user to authenticate.
        auth_flow : Optional[str], default "ADMIN_NO_SRP_AUTH"
            The authentication flow to use. Defaults to "ADMIN_NO_SRP_AUTH".
        client_metadata : Optional[Dict[str, str]], default None
            Additional metadata to pass to the client. Defaults to None.

        Returns
        -------
        Dict[str, Union[str, List[Dict[str, str]]]]
            The response from the Cognito service containing authentication
            tokens and other information.

        Raises
        ------
        ClientError
            If there is an error during the authentication process, such as
            invalid credentials or user not found.
        """

        # Construct parameters for the auth flow
        parameters = {
            "UserPoolId": user_pool_id,
            "ClientId": client_id,
            "AuthFlow": auth_flow,
            "AuthParameters": {
                "USERNAME": username,
                "PASSWORD": password,
            },
        }

        # Add client metadata if provided
        if client_metadata:
            parameters["ClientMetadata"] = client_metadata

        # Attempt to initiate authentication
        try:
            logger.info(
                f"Initiating auth for user {username} in user pool {user_pool_id}"
            )
            response = self.client.admin_initiate_auth(**parameters)
            return response
        except ClientError as e:
            logger.error(f"Error initiating auth: {e}")
            raise e

    def admin_list_groups_for_user(
        self, user_pool_id: str, username: str
    ) -> Dict[str, List[Dict[str, str]]]:
        """Lists the groups that a user belongs to in a Cognito user pool.

        Parameters
        ----------
        user_pool_id : str
            The ID of the Cognito user pool.
        username : str
            The username of the user.

        Returns
        -------
        Dict[str, List[Dict[str, str]]]
            A dictionary containing the groups the user belongs to.

        Raises
        ------
        ClientError
            If there is an error retrieving the groups for the user.
        """

        try:
            logger.info(
                f"Listing groups for user {username} in user pool {user_pool_id}"
            )
            response = self.client.admin_list_groups_for_user(
                UserPoolId=user_pool_id, Username=username
            )
            return response
        except ClientError as e:
            logger.error(f"Error listing groups for user: {e}")
            raise e
