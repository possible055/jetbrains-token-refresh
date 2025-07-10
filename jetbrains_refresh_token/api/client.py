import json
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from jetbrains_refresh_token.constants import JWT_AUTH_URL, JWT_QUOTA_URL
from jetbrains_refresh_token.log_config import get_logger

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
        raise_on_status=False,  # Don't raise exceptions for HTTP error status codes
    )

    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

    try:
        logger.info("Sending request with up to 3 retries configured.")
        logger.debug("Request URL: %s", url)
        logger.debug("Request headers: %s", headers)
        logger.debug("Request data: %s", data)
        response = session.post(
            url,
            headers=headers,
            data=data,
            timeout=timeout,
        )
        logger.debug("Response status code: %s", response.status_code)
        logger.debug("Response headers: %s", dict(response.headers))
        if response.status_code >= 400:
            logger.debug("Response text: %s", response.text)
        return response
    except requests.RequestException as e:
        logger.error("Error persists after multiple retries: %s", e)
        logger.error("Exception type: %s", type(e).__name__)
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
    if response is None:
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

    # Try to parse error details from JSON response
    try:
        error_data = response.json()
        if "error" in error_data:
            logger.error("Error type: %s", error_data["error"])
        if "error_description" in error_data:
            logger.error("Error description: %s", error_data["error_description"])
        if "message" in error_data:
            logger.error("Error message: %s", error_data["message"])
    except (ValueError, json.JSONDecodeError):
        logger.debug("Could not parse error response as JSON")

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
    if response is None:
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

    # Try to parse error details from JSON response
    try:
        error_data = response.json()
        if "error" in error_data:
            logger.error("Error type: %s", error_data["error"])
        if "error_description" in error_data:
            logger.error("Error description: %s", error_data["error_description"])
        if "message" in error_data:
            logger.error("Error message: %s", error_data["message"])
    except (ValueError, json.JSONDecodeError):
        logger.debug("Could not parse error response as JSON")

    return None
