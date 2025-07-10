import base64
import json
import time
from typing import Optional

import jwt

from jetbrains_refresh_token.config import logger


def parse_jwt_expiration(token: str) -> Optional[int]:
    """
    Parse the expiration time from a JWT token.

    Args:
        jwt_token (str): JWT token string.

    Returns:
        Optional[int]: The expiration time as a UNIX timestamp, or None if it cannot be parsed.
    """
    try:
        # A JWT token consists of three parts separated by dots: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            logger.error("Invalid JWT token format: expected 3 parts")
            return None

        # Decode the payload part (base64url encoded)
        # Padding characters '=' may need to be added
        payload = parts[1]
        payload_padded = payload + '=' * (4 - len(payload) % 4) if len(payload) % 4 else payload

        try:
            decoded_bytes = base64.urlsafe_b64decode(payload_padded)
            payload_data = json.loads(decoded_bytes.decode('utf-8'))
        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.error("Failed to decode JWT payload: %s", e)
            return None

        # Extract the expiration time (exp claim) from the payload
        if 'exp' in payload_data:
            return payload_data['exp']

        logger.warning("JWT token does not contain expiration time (exp claim)")
        return None
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("Error parsing JWT token: %s", e)
        return None


def is_vaild_jwt_format(token):
    try:
        jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
        return True
    except jwt.InvalidTokenError:
        return False


def is_jwt_expired(token: str) -> bool:
    """
    Check whether the JWT token for the specified account has expired.

    Args:
        jwt (str): JWT string to check.

    Returns:
        bool: True if the token is expired, about to expire, or its expiration
            time cannot be determined; otherwise, False.
    """

    expires_at = parse_jwt_expiration(token)
    if expires_at is None:
        return True

    # Check if the token has expired or has less than 5 minutes (300 seconds) remaining
    current_time = int(time.time())
    return current_time >= expires_at or (expires_at - current_time) < 300
