import json
from typing import Any, Dict, Optional

import requests
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from jetbrains_refresh_token.log_config import get_logger

OAUTH_URL = "https://oauth.account.jetbrains.com/oauth2/token"
JWT_AUTH_URL = "https://api.jetbrains.ai/auth/jetbrains-jwt/provide-access/license/v2"
JWT_QUOTA_URL = "https://api.jetbrains.ai/user/v5/quota/get"
CLIENT_ID = "ide"


logger = get_logger("api.refresh_token")


def requests_post(
    url: str, headers: Dict[str, str], data: Optional[Any] = None, timeout: int = 10
) -> Optional[requests.Response]:
    """
    Send an HTTP POST request with a retry strategy.

    Args:
        url (str): Target URL.
        headers (Dict[str, str]): HTTP request headers.
        data (Any): Request payload.
        timeout (int, optional): Request timeout in seconds. Defaults to 10.

    Returns:
        Optional[requests.Response]: The Response object on success; otherwise, None.
    """
    # Configuring retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )

    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

    try:
        logger.info("Sending request with up to 3 retries configured.")
        response = session.post(
            url,
            headers=headers,
            data=data,
            timeout=timeout,
        )
        return response
    except requests.RequestException as e:
        logger.error("Error persists after multiple retries: %s", e)
        return None


def request_id_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    Obtain new JetBrains OAuth tokens using a refresh token.

    Args:
        refresh_token (str): The refresh token used for token renewal

    Returns:
        Optional[Dict[str, str]]:
            A dictionary containing "access_token", "id_token", and "refresh_token" on success;
            otherwise, None.

    Raises:
        requests.RequestException: When HTTP requests fail after multiple retry attempts
    """
    ua = UserAgent(browsers=['Edge', 'Chrome', 'Firefox'])
    random_ua = ua.random

    logger.info("Refreshing access token with refresh token.")
    logger.debug("User-Agent: %s", random_ua)

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": random_ua,
    }

    response = requests_post(OAUTH_URL, data, headers, 10)
    if not response:
        logger.error("Request failed: no response.")
        return None

    if response.status_code == 200:
        try:
            token_data = response.json()

            if not all(key in token_data for key in ["access_token", "id_token", "refresh_token"]):
                logger.error("Required token information is missing from the response.")
                return None

            access_token = token_data["access_token"]
            id_token = token_data["id_token"]
            refresh_token = token_data["refresh_token"]

            logger.info("Successfully obtained a new access token.")

            if access_token:
                logger.debug("access_token: %s***", access_token[:12])
            if id_token:
                logger.debug("id_token: %s***", id_token[:12])
            if refresh_token:
                logger.debug("refresh_token: %s***", refresh_token[:12])

            return {
                "access_token": access_token,
                "id_token": id_token,
                "refresh_token": refresh_token,
            }
        except (ValueError, json.JSONDecodeError) as e:
            logger.error("Failed to parse JSON: %s", e)
            return None
        except KeyError as e:
            logger.error("Required token field: %s", e)
            return None

    logger.error(
        "Request failed with status code: %s. Response: %s", response.status_code, response.text
    )
    return None


def request_access_token(id_token: str, license_id: str) -> Optional[Dict]:
    """
    Refreshes the JetBrains JWT token.

    Args:
        license_id (str): JetBrains license ID.
        id_token (str): Access token used for authorization.

    Returns:
        Optional[Dict]: JSON data containing the refreshed JWT on success; otherwise, None.
    """
    payload = {"licenseId": license_id}
    headers = {
        'Accept': "*/*",
        'Content-Type': "application/json",
        'Accept-Charset': "UTF-8",
        'authorization': f"Bearer {id_token}",
        'User-Agent': "ktor-client",
    }

    response = requests_post(JWT_AUTH_URL, headers=headers, data=json.dumps(payload), timeout=10)
    if not response:
        logger.error("Request failed: no response.")
        return None

    if response.status_code == 200:
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as e:
            logger.error("Failed to parse JSON: %s", e)
            return None

        if data['state'] == "PAID":
            access_token = data['token']
            return access_token

        logger.error("License: Non-Paid Version")
        return None

    logger.error(
        "Request failed with status code: %s. Response: %s", response.status_code, response.text
    )
    return None


def request_quota_info(access_token: str, grazie_agent: Optional[Dict] = None) -> Optional[Dict]:
    """
    Query the quota information of a JWT token.

    Args:
        access_token: The JWT access token.
        grazie_agent: Optional grazie-agent information.

    Returns:
        dict: A dictionary containing the quota information.
    """
    headers = {
        'Accept': "*/*",
        'Content-Type': "application/json",
        'Accept-Charset': "UTF-8",
        'grazie-authenticate-jwt': access_token,
        'User-Agent': "ktor-client",
    }

    # If grazie-agent information is provided, add it to the headers
    if grazie_agent:
        headers["grazie-agent"] = json.dumps(grazie_agent)
    else:
        default_grazie_agent = {"name": "aia:dataspell", "version": "251.26094.80.22:251.26927.75"}
        headers["grazie-agent"] = json.dumps(default_grazie_agent)

    response = requests_post(JWT_QUOTA_URL, headers=headers, timeout=10)
    if not response:
        logger.error("Request failed: no response.")
        return None

    if response.status_code == 200:
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as e:
            logger.error("Failed to parse JSON: %s", e)
            return None
        return data

    logger.error(
        "Request failed with status code: %s. Response: %s", response.status_code, response.text
    )
    return None
