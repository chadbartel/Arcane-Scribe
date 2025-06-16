# Standard Library
import base64
from typing import Optional

# Third Party
from aws_lambda_powertools import Logger

# Initialize logger
logger = Logger(service="helpers")


def extract_username_from_basic_auth(
    encoded_credentials: str,
) -> Optional[str]:
    """Extracts the username from a Base64 encoded Basic Authentication string.

    Parameters
    ----------
    encoded_credentials : str
        Base64 encoded string containing the credentials in the format
        "username:password".

    Returns
    -------
    Optional[str]
        The extracted username if successful, otherwise None.

    Raises
    ------
    ValueError
        If the encoded string is not in the expected format or cannot be
        decoded.
    """
    try:
        # Decode the Base64 encoded credentials
        decoded_bytes = base64.b64decode(encoded_credentials)
        decoded_string = decoded_bytes.decode("utf-8")

        # Check if the decoded string contains a colon
        if ":" not in decoded_string:
            raise ValueError(
                "Invalid credentials format: missing colon separator"
            )

        # Split the decoded string to extract the username
        username, _ = decoded_string.split(":", 1)
        return username

    except Exception:
        logger.error(
            "Failed to extract username from Basic Auth credentials",
            exc_info=True,
        )
        return None
