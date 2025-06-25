"""Cognito client wrapper for AWS Cognito Identity Provider operations."""

# Standard Library
from typing import Dict, List, Optional, Any

# Third Party
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

# Initialize logger
logger = Logger(service="cognito-idp-client-wrapper")


class CognitoIdpClient:
    """A wrapper for the Boto3 Cognito Identity Provider client."""

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
    ) -> Dict[str, Any]:
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
        Dict[str, Any]
            A dictionary containing the authentication result, which may include
            access tokens, ID tokens, and refresh tokens.
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
            return response.get("AuthenticationResult", {})
        except ClientError as e:
            logger.error(f"Error initiating auth for user '{username}': {e}")
            raise e

    def admin_create_user(
        self,
        user_pool_id: str,
        username: str,
        email: str,
        temporary_password: str,
    ) -> Dict[str, Any]:
        """Creates a new user in a Cognito user pool.

        Parameters
        ----------
        user_pool_id : str
            The ID of the Cognito user pool.
        username : str
            The username for the new user.
        email : str
            The email address for the new user.
        temporary_password : str
            The temporary password for the new user.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the details of the created user.

        Raises
        ------
        ClientError
            If there is an error creating the user, such as user already exists
            or invalid parameters.
        """
        try:
            logger.info(
                f"Creating new user '{username}' in pool {user_pool_id}"
            )
            response = self.client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=username,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                ],
                TemporaryPassword=temporary_password,
                MessageAction="SUPPRESS",  # Don't send the default welcome email
            )
            return response.get("User", {})
        except ClientError as e:
            logger.error(f"Error creating user '{username}': {e}")
            raise e

    def list_users(self, user_pool_id: str) -> List[Dict[str, Any]]:
        """Lists all users in a Cognito user pool.

        Parameters
        ----------
        user_pool_id : str
            The ID of the Cognito user pool.

        Returns
        -------
        List[Dict[str, Any]]
            A list of users in the user pool.

        Raises
        ------
        ClientError
            If there is an error retrieving the list of users.
        """
        try:
            logger.info(f"Listing all users in user pool {user_pool_id}")
            response = self.client.list_users(UserPoolId=user_pool_id)
            return response.get("Users", [])
        except ClientError as e:
            logger.error(f"Error listing users: {e}")
            raise e

    def admin_delete_user(self, user_pool_id: str, username: str) -> None:
        """Deletes a user from the user pool."""
        try:
            logger.info(f"Deleting user '{username}' from pool {user_pool_id}")
            self.client.admin_delete_user(
                UserPoolId=user_pool_id,
                Username=username,
            )
        except ClientError as e:
            logger.error(f"Error deleting user '{username}': {e}")
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
            return response.get("Groups", [])
        except ClientError as e:
            logger.error(f"Error listing groups for user: {e}")
            raise e

    def get_current_user(self, access_token: str) -> Dict[str, Any]:
        """Retrieves the current authenticated user's information.

        Parameters
        ----------
        access_token : str
            The access token of the authenticated user.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the user's information, such as username,
            email, and groups.

        Raises
        ------
        ClientError
            If there is an error retrieving the current user's information.
        """
        try:
            logger.info("Retrieving current user information")
            response = self.client.get_user(AccessToken=access_token)

            # Parse email attribute from user attributes
            email = next(
                (
                    attr["Value"]
                    for attr in response.get("UserAttributes", [])
                    if attr["Name"] == "email"
                ),
                "",
            )

            # Get the groups for the user
            groups = self.admin_list_groups_for_user(
                user_pool_id=response["UserPoolId"],
                username=response["Username"],
            )

            # Construct the user info dictionary
            user_info = {
                "username": response.get("Username"),
                "groups": groups,
                "email": email,
            }
            return user_info
        except ClientError as e:
            logger.error(f"Error retrieving current user: {e}")
            raise e
