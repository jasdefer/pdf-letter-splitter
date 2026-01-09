#!/usr/bin/env python3
"""
LLM-based letter boundary detection for merged PDF documents.

Uses a local llama.cpp server to classify adjacent page pairs and determine
whether the second page starts a new letter.
"""

import json
import logging
from typing import Dict, List, Any, Tuple
import requests

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MAX_PAGE_TEXT_LENGTH = 350  # Maximum characters to send per page to LLM
DEFAULT_LLM_TIMEOUT = 300  # Default timeout for LLM requests in seconds


class BoundaryDecision:
    """Represents a boundary detection decision from the LLM."""
    
    def __init__(self, is_boundary: bool, confidence: float, reason: str):
        """
        Initialize a boundary decision.
        
        Args:
            is_boundary: Whether page i+1 starts a new letter
            confidence: Confidence score (0.0 to 1.0)
            reason: Explanation for the decision
        """
        self.is_boundary = is_boundary
        self.confidence = confidence
        self.reason = reason
    
    def __repr__(self):
        return f"BoundaryDecision(boundary={self.is_boundary}, confidence={self.confidence:.2f}, reason='{self.reason}')"


class LLMClient:
    """Client for communicating with llama.cpp server."""
    
    def __init__(self, host: str = "llm", port: int = 8080, temperature: float = 0.0, 
                 timeout: int = DEFAULT_LLM_TIMEOUT):
        """
        Initialize the LLM client.
        
        Args:
            host: LLM server hostname (default: "llm" for Docker Compose)
            port: LLM server port (default: 8080)
            temperature: Sampling temperature (0.0 for fully deterministic responses)
            timeout: Request timeout in seconds (default: 60)
        """
        self.base_url = f"http://{host}:{port}"
        self.temperature = temperature
        self.timeout = timeout
        logger.info(f"Initialized LLM client: {self.base_url}, temperature={temperature}, timeout={timeout}s")
    
    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Generate a completion from the LLM using OpenAI-compatible chat endpoint.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated JSON response as string
            
        Raises:
            RuntimeError: If the LLM request fails
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "cache_prompt": False,
            "response_format": {
                "type": "json_object"
            }
        }
        logger.debug(f"Sending LLM request to {url} with payload: {payload}")
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract content from OpenAI-compatible response format
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                logger.debug(f"LLM response: {content[:200]}...")
                return content
            else:
                raise RuntimeError(f"Unexpected response format: {result}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request failed: {e}")
            raise RuntimeError(f"LLM request failed: {e}")


def create_boundary_prompt(page_i_text: str, page_j_text: str, 
                          page_i_num: int, page_j_num: int) -> str:
    """
    Create a prompt for the LLM to determine if page j starts a new letter.
    
    The prompt is in German (primary language) and asks the LLM to analyze
    whether the second page starts a new letter based on content comparison.
    
    Args:
        page_i_text: Text from page i
        page_j_text: Text from page j (i+1)
        page_i_num: Page number of page i
        page_j_num: Page number of page j
        
    Returns:
        Formatted prompt string
    """
    # Truncate page texts to avoid token limits
    page_i_truncated = page_i_text[:MAX_PAGE_TEXT_LENGTH]
    page_j_truncated = page_j_text[:MAX_PAGE_TEXT_LENGTH]
    
    prompt = f"""Aufgabe: Entscheide, ob Seite {page_j_num} den Beginn eines NEUEN Briefes darstellt oder die Fortsetzung des Briefes von Seite {page_i_num} ist.

SEITE {page_i_num}:
{page_i_truncated}

SEITE {page_j_num}:
{page_j_truncated}

Gib deine Entscheidung im folgenden JSON-Format zurück:
{{
  "boundary": true,
  "confidence": 0.95,
  "reason": "kurze Begründung"
}}"""
    
    return prompt


def parse_llm_response(response: str) -> BoundaryDecision:
    """
    Parse the LLM's JSON response into a BoundaryDecision.
    
    Args:
        response: Raw LLM response text (should be valid JSON)
        
    Returns:
        Parsed BoundaryDecision
        
    Raises:
        ValueError: If response cannot be parsed as valid JSON or is missing required fields
    """
    response = response.strip()
    
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in response: {e}. Response: {response}")
    
    # Validate required fields
    if "boundary" not in data:
        raise ValueError(f"Missing 'boundary' field in response: {data}")
    if "confidence" not in data:
        raise ValueError(f"Missing 'confidence' field in response: {data}")
    if "reason" not in data:
        raise ValueError(f"Missing 'reason' field in response: {data}")
    
    # Validate types and ranges
    if not isinstance(data["boundary"], bool):
        raise ValueError(f"'boundary' must be a boolean, got: {type(data['boundary'])}")
    
    confidence = float(data["confidence"])
    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"'confidence' must be between 0.0 and 1.0, got: {confidence}")
    
    reason = str(data["reason"])
    
    return BoundaryDecision(
        is_boundary=data["boundary"],
        confidence=confidence,
        reason=reason
    )


def detect_boundaries(pages: List[Dict[str, Any]], llm_client: LLMClient) -> List[Tuple[int, int, BoundaryDecision]]:
    """
    Detect letter boundaries in a list of pages using pairwise LLM classification.
    
    Args:
        pages: List of page dictionaries with 'page_number' and 'text' keys
        llm_client: Initialized LLM client
        
    Returns:
        List of tuples (page_i, page_j, decision) for each adjacent pair
    """
    if not pages:
        logger.warning("No pages provided for boundary detection")
        return []
    
    if len(pages) < 2:
        logger.info("Only one page, no boundaries to detect")
        return []
    
    logger.info(f"Starting boundary detection for {len(pages)} pages ({len(pages)-1} pairs)")
    
    decisions = []
    
    for i in range(len(pages) - 1):
        page_i = pages[i]
        page_j = pages[i + 1]
        
        page_i_num = page_i["page_number"]
        page_j_num = page_j["page_number"]
        page_i_text = page_i["text"]
        page_j_text = page_j["text"]
        
        logger.info(f"Analyzing boundary between page {page_i_num} and {page_j_num}")
        
        # Create prompt
        prompt = create_boundary_prompt(page_i_text, page_j_text, page_i_num, page_j_num)
        
        # Query LLM
        try:
            response = llm_client.generate(prompt)
            logger.debug(f"LLM raw response for pages {page_i_num}-{page_j_num}: {response}")
            decision = parse_llm_response(response)
            
            logger.info(f"  Page {page_j_num}: boundary={decision.is_boundary}, "
                       f"confidence={decision.confidence:.2f}, reason='{decision.reason}'")
            
            decisions.append((page_i_num, page_j_num, decision))
            
        except (ValueError, RuntimeError) as e:
            logger.error(f"Failed to get boundary decision for pages {page_i_num}-{page_j_num}: {e}")
            # Re-raise the exception as we have no fallback logic per requirements
            raise
    
    return decisions


def group_pages_into_letters(pages: List[Dict[str, Any]], 
                            decisions: List[Tuple[int, int, BoundaryDecision]]) -> List[List[int]]:
    """
    Group pages into letters based on boundary decisions.
    
    Page 1 is always treated as the start of a letter.
    
    Args:
        pages: List of page dictionaries
        decisions: List of boundary decisions from detect_boundaries()
        
    Returns:
        List of letter groups, where each group is a list of page numbers
    """
    if not pages:
        return []
    
    # Start with page 1 as the first letter
    letters = [[pages[0]["page_number"]]]
    
    # Build a map of page_j -> decision for easy lookup
    decision_map = {page_j: decision for _, page_j, decision in decisions}
    
    # Process remaining pages
    for i in range(1, len(pages)):
        page_num = pages[i]["page_number"]
        decision = decision_map.get(page_num)
        
        if decision and decision.is_boundary:
            # Start a new letter
            letters.append([page_num])
        else:
            # Continue current letter
            letters[-1].append(page_num)
    
    logger.info(f"Grouped {len(pages)} pages into {len(letters)} letters")
    for idx, letter_pages in enumerate(letters, 1):
        logger.info(f"  Letter {idx}: pages {letter_pages}")
    
    return letters

def detect_and_log_boundaries(pages: List[Dict[str, Any]], 
                              llm_host: str = "llm", 
                              llm_port: int = 8080,
                              temperature: float = 0.0) -> None:
    """
    Main entry point: detect boundaries and log results.
    
    This function:
    1. Initializes the LLM client
    2. Detects boundaries using pairwise classification
    3. Groups pages into letters
    4. Logs all results
    
    Args:
        pages: List of page dictionaries from OCR extraction
        llm_host: LLM server hostname
        llm_port: LLM server port
        temperature: LLM sampling temperature (default: 0.0 for fully deterministic)
    """
    logger.info("=" * 80)
    logger.info("LETTER BOUNDARY DETECTION")
    logger.info("=" * 80)
    
    # Initialize LLM client
    llm_client = LLMClient(host=llm_host, port=llm_port, temperature=temperature)

    # Detect boundaries
    decisions = detect_boundaries(pages, llm_client)
    
    logger.info("")
    logger.info("BOUNDARY DETECTION RESULTS:")
    logger.info("-" * 80)
    
    for page_i, page_j, decision in decisions:
        logger.info(f"Pages ({page_i}, {page_j}): boundary={decision.is_boundary}, "
                   f"confidence={decision.confidence:.2f}")
        logger.info(f"  Reason: {decision.reason}")
    
    # Group pages into letters
    logger.info("")
    logger.info("LETTER GROUPINGS:")
    logger.info("-" * 80)
    
    letters = group_pages_into_letters(pages, decisions)
    
    for idx, letter_pages in enumerate(letters, 1):
        logger.info(f"Letter {idx}: {len(letter_pages)} page(s) - {letter_pages}")
    
    logger.info("=" * 80)
