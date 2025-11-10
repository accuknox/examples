"""
AccuKnox Firewall Utility for LLM Applications
---------------------------------------------
This module provides safe wrappers to integrate AccuKnox LLM Defense
into chatbot or LLM-based applications.
"""

import os
from accuknox_llm_defense import LLMDefenseClient
from typing import NamedTuple, Optional
import json

# --- Configure ---
ENABLE_ACCUKNOX_FIREWALL = True  # set True to switch on the firewall
STRICT_MODE = False  # set True to never proceed with unsanitized prompt/response
STATIC_RESPONSE = "Your prompt violated our safety policies. Please rephrase."  # will be returned when prompt/response is blocked
VERBOSE = True  # set True to get more logs
# -----------------
_firewall_client: Optional[LLMDefenseClient] = None

import logging
logging.basicConfig(level=logging.DEBUG if VERBOSE else logging.WARNING)
logger = logging.getLogger(__name__)


class ScanResult(NamedTuple):
    """
    Response structure returned by the prompt or response scanner.

    Attributes:
        sanitized_content (str): A sanitized, safe version of the original prompt or model response.
            This content is suitable for forwarding or returning to the user.
        session_id (str): A unique identifier linking a scanned prompt with its corresponding response.
        block (bool): A flag indicating whether the original content should be blocked.
            If True, the application should prevent forwarding and instead use the fallback_response.
        fallback_response (str): A safe, preconstructed response to return to the user when
            block is True. This may be an explanatory message or an empty string if not applicable.

    Notes:
        - ScanResult is immutable (as a NamedTuple); it should be treated as read-only.
        - Always check the `block` flag before using `sanitized_content` in downstream processing 
          to ensure compliance with content policies.
    """
    sanitized_content: str
    session_id: str
    block: bool
    fallback_response: str



def initialize_firewall_client(user: Optional[str] = "") -> None:
    """
    Initialize or re-initialize the global firewall client.

    Args:
        user (Optional[str]): Optional user identifier passed as `user_info` 
            when constructing the LLMDefenseClient. Defaults to an empty string.

    Returns:
        None

    Raises:
        RuntimeError: If ACCUKNOX_API_KEY is missing and STRICT_MODE is enabled.

    Behavior:
        - If ENABLE_ACCUKNOX_FIREWALL is falsy, sets `_firewall_client` to None.
        - If ENABLE_ACCUKNOX_FIREWALL is truthy:
            - Reads ACCUKNOX_API_KEY from the environment.
            - If a key is found, constructs an LLMDefenseClient.
            - If missing, logs an error, resets `_firewall_client`, and possibly raises an error.

    Side Effects:
        Modifies the module-level `_firewall_client`, reads environment variables,
        and logs errors if configuration is invalid.
    """
    global _firewall_client
    if not ENABLE_ACCUKNOX_FIREWALL:
        _firewall_client = None
    else:
        accuknox_api_key = os.getenv("ACCUKNOX_API_KEY")
        if accuknox_api_key:
            _firewall_client = LLMDefenseClient(
                llm_defense_api_key = accuknox_api_key,
                user_info = user
            )
        else:
            logger.error("Missing required environment variable: ACCUKNOX_API_KEY")
            _firewall_client = None
            if STRICT_MODE:
                raise RuntimeError("Missing required environment variable: ACCUKNOX_API_KEY")


def get_sanitized_prompt(prompt: str) -> ScanResult:
    """
    Scan and sanitize a prompt using the configured Prompt Firewall.

    Args:
        prompt (str): The raw user prompt to be scanned or sanitized.

    Returns:
        ScanResult: Contains the sanitized or original prompt, session ID, 
        a block flag, and a fallback response string.

    Behavior:
        - If _firewall_client is set, runs scan_prompt(content=prompt).
            - On scan error:
                - If STRICT_MODE is True, returns a blocking ScanResult.
                - Otherwise, logs a warning and returns a non-blocking result.
            - If query_status is "BLOCK", logs the event and returns a blocking ScanResult 
              with STATIC_RESPONSE.
            - For other statuses ("PASS", "MONITOR", etc.), returns a non-blocking result.
        - If _firewall_client is not set:
            - If STRICT_MODE is True, returns a blocking ScanResult.
            - Otherwise, logs a debug message and returns a non-blocking result.
    """
    if _firewall_client:
        sanitized_prompt_dict: dict = _firewall_client.scan_prompt(content=prompt)
        if "error" in sanitized_prompt_dict:
            if STRICT_MODE:
                return ScanResult(prompt, None, True, "")
            else:
                logger.warning("Prompt Firewall scanning got error, returning unsanitized prompt")
                return ScanResult(prompt, None, False, "")
        logger.info(f"The prompt was analyzed against following policies: \n{json.dumps(sanitized_prompt_dict.get('risk_score', {}))}")
        prompt_sanitization_action = sanitized_prompt_dict.get("query_status")
        if prompt_sanitization_action == "BLOCK":
            logger.info(f"Prompt '{prompt}' triggered BLOCK action")
            return ScanResult(
                sanitized_prompt_dict.get("sanitized_content"),
                sanitized_prompt_dict.get("session_id"),
                True,
                STATIC_RESPONSE,
            )
        else:  # prompt_sanitization_action in ("UNCHECKED", "PASS", "MONITOR")
            return ScanResult(
                sanitized_prompt_dict.get("sanitized_content"),
                sanitized_prompt_dict.get("session_id"),
                False,
                "",
            )
    else:
        if STRICT_MODE:
            return ScanResult(prompt, None, True, "")
        else:
            logger.debug("Firewall client not initialized, returning unsanitized prompt")
            return ScanResult(prompt, None, False, "")


def get_sanitized_response(prompt: str, response: str, session_id: Optional[str] = None) -> ScanResult:
    """
    Scan and sanitize a application's response using the configured firewall client.

    Args:
        prompt (str): The original user prompt that generated the response.
        response (str): The raw model response to be scanned or sanitized.
        session_id (Optional[str]): An optional identifier for the conversation.

    Returns:
        ScanResult: Contains sanitized or original text, session ID, a block flag, 
        and fallback response string.

    Behavior:
        - If _firewall_client is set:
            - Calls scan_response(prompt, content, session_id).
            - On error:
                - If STRICT_MODE is True, returns a blocking ScanResult.
                - Otherwise, logs a warning and returns the unsanitized response.
            - If query_status is "BLOCK", logs the event and returns a blocking ScanResult 
              with STATIC_RESPONSE.
            - For all others ("PASS", "MONITOR", etc.), returns a non-blocking result.
        - If _firewall_client is missing:
            - If STRICT_MODE is True, returns a blocking ScanResult.
            - Otherwise, logs a debug message and returns a non-blocking result.
    """
    if _firewall_client:
        sanitized_response_dict: dict = _firewall_client.scan_response(
            content=response,
            prompt=prompt,
            session_id=session_id
        )
        if "error" in sanitized_response_dict:
            if STRICT_MODE:
                return ScanResult(response, session_id, True, "")
            else:
                logger.warning("Response Firewall scanning got error, returning unsanitized response")
                return ScanResult(response, session_id, False, "")
        logger.info(f"The response was analyzed against following policies: \n{json.dumps(sanitized_response_dict.get('risk_score', {}))}")
        response_sanitization_action = sanitized_response_dict.get("query_status")
        if response_sanitization_action == "BLOCK":
            logger.info(f"Response '{response}' triggered BLOCK action")
            return ScanResult(
                sanitized_response_dict.get("sanitized_content"),
                session_id,
                True,
                STATIC_RESPONSE,
            )
        else:  # response_sanitization_action in ("UNCHECKED", "PASS", "MONITOR")
            return ScanResult(
                sanitized_response_dict.get("sanitized_content"),
                session_id,
                False,
                "",
            )
    else:
        if STRICT_MODE:
            return ScanResult(response, session_id, True, "")
        else:
            logger.debug("Firewall client initialization failed, returning unsanitized response")
            return ScanResult(response, session_id, False, "")

