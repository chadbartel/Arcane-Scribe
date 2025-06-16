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
        try:
            response = self.client.admin_initiate_auth(
                UserPoolId=user_pool_id,
                ClientId=client_id,
                AuthFlow=auth_flow,
                AuthParameters={"USERNAME": username, "PASSWORD": password},
            )
            return response
        except ClientError as e:
            logger.error(f"Error initiating auth: {e}")
            raise e
