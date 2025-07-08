import time

import jwt

from jetbrain_refresh_token.config.config import parse_jwt_expiration


def is_vaild_jwt_format(token):
    try:
        jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
        return True
    except jwt.InvalidTokenError:
        return False


def is_id_token_expired(expired_at: int) -> bool:
    """
    Check whether the ID token has expired.

    Args:
        expired_at (int): Expiration time as a UNIX timestamp.

    Returns:
        bool: True if the token is expired, False otherwise.
    """
    current_time = int(time.time())
    return current_time >= expired_at or (expired_at - current_time) < 300


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
