#!/usr/bin/env python3
"""
Document splitter module for grouping PageAnalysis objects into logical Letters.

This module implements heuristic-based document splitting using weighted scoring
to determine where one letter ends and another begins in a concatenated PDF.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from page_analysis_data import PageAnalysis

# Configure module logger
logger = logging.getLogger(__name__)

# Scoring threshold for splitting
SPLIT_THRESHOLD = 500

# Position thresholds for page layout analysis
TOP_THIRD_THRESHOLD = 0.33  # Top third of the page (0.0 to 0.33)
TOP_HALF_THRESHOLD = 0.5     # Top half of the page (0.0 to 0.5)
MIDDLE_PAGE_THRESHOLD = 0.3  # Below this is considered "middle" for page indices


@dataclass
class Letter:
    """
    Represents a logical letter consisting of one or more pages.
    
    Attributes:
        pages: List of PageAnalysis objects that make up this letter
    """
    pages: list[PageAnalysis]
    
    @property
    def master_date(self) -> Optional[str]:
        """
        Extract the date from the first page of the letter.
        
        Returns:
            Date string if found on first page, None otherwise
        """
        if not self.pages:
            return None
        first_page = self.pages[0]
        if first_page.date.found and first_page.date.date_value:
            return first_page.date.date_value.strftime('%Y-%m-%d')
        return None
    
    @property
    def master_subject(self) -> Optional[str]:
        """
        Extract the subject from the first page of the letter.
        
        Returns:
            Subject string if found on first page, None otherwise
        """
        if not self.pages:
            return None
        first_page = self.pages[0]
        if first_page.subject.found and first_page.subject.raw:
            return first_page.subject.raw
        return None


class TransitionScorer:
    """
    Scores the transition between consecutive pages to determine if a split should occur.
    
    Uses weighted heuristics based on page markers, layout patterns, and logical sequences.
    """
    
    def score_transition(self, prev_page: PageAnalysis, curr_page: PageAnalysis) -> tuple[int, list[str]]:
        """
        Calculate the split score between two consecutive pages.
        
        Args:
            prev_page: The previous page analysis
            curr_page: The current page analysis
        
        Returns:
            Tuple of (total_score, contributing_factors_list)
        """
        score = 0
        factors = []
        
        # 1. Definitive Markers (The "Anchor" Rules)
        
        # +1000: Current page LetterPageIndex.current == 1
        if curr_page.letter_page_index.found and curr_page.letter_page_index.current == 1:
            # Check if it's in the middle of the page (y_rel > MIDDLE_PAGE_THRESHOLD)
            if curr_page.letter_page_index.y_rel and curr_page.letter_page_index.y_rel > MIDDLE_PAGE_THRESHOLD and curr_page.letter_page_index.y_rel < 1 - MIDDLE_PAGE_THRESHOLD:
                score += 200
                factors.append("New Index in middle (+200)")
            else:
                score += 1000
                factors.append("New Index (+1000)")
        
        # +1000: Previous page LetterPageIndex.current == total
        if (prev_page.letter_page_index.found and 
            prev_page.letter_page_index.current is not None and 
            prev_page.letter_page_index.total is not None and
            prev_page.letter_page_index.current == prev_page.letter_page_index.total):
            score += 1000
            factors.append("Last Index of Previous (+1000)")
        
        # 2. Start-of-Letter Heuristics (Cumulative)
        
        # Address Block scoring
        if curr_page.address_block.found:
            if curr_page.address_block.y_rel is not None:
                if curr_page.address_block.y_rel <= TOP_THIRD_THRESHOLD:  # Top third
                    score += 450
                    factors.append("Address Block at top (+450)")
                else:
                    score += 75
                    factors.append("Address Block lower (+75)")
        
        # Subject Line scoring
        if curr_page.subject.found:
            if curr_page.subject.y_rel is not None:
                if curr_page.subject.y_rel <= TOP_HALF_THRESHOLD:  # Top half
                    score += 300
                    factors.append("Subject at top (+300)")
                else:
                    score += 50
                    factors.append("Subject lower (+50)")
        
        # Greeting scoring
        if curr_page.greeting.found:
            if curr_page.greeting.y_rel is not None:
                if curr_page.greeting.y_rel <= TOP_HALF_THRESHOLD:  # Top half
                    score += 250
                    factors.append("Greeting at top (+250)")
                else:
                    score += 50
                    factors.append("Greeting lower (+50)")
        
        # Date Marker scoring
        if curr_page.date.found:
            if curr_page.date.y_rel is not None:
                if curr_page.date.y_rel <= TOP_THIRD_THRESHOLD:  # Top third
                    score += 50
                    factors.append("Date at top (+50)")
        
        # 3. Logical Sequence Penalties (Negative Weights)
        
        # -150: Address Block is found below the Subject or Greeting
        if (curr_page.address_block.found and curr_page.address_block.y_rel is not None):
            # Check if address is below subject
            if (curr_page.subject.found and curr_page.subject.y_rel is not None and
                curr_page.address_block.y_rel > curr_page.subject.y_rel):
                score -= 150
                factors.append("Address below Subject (-150)")
            # Check if address is below greeting
            elif (curr_page.greeting.found and curr_page.greeting.y_rel is not None and
                  curr_page.address_block.y_rel > curr_page.greeting.y_rel):
                score -= 150
                factors.append("Address below Greeting (-150)")
        
        # -200: Subject is found below the Greeting
        if (curr_page.subject.found and curr_page.subject.y_rel is not None and
            curr_page.greeting.found and curr_page.greeting.y_rel is not None and
            curr_page.subject.y_rel > curr_page.greeting.y_rel):
            score -= 200
            factors.append("Subject below Greeting (-200)")
        
        # -100: Current page starts with a goodbye at the top third
        if (curr_page.goodbye.found and curr_page.goodbye.y_rel is not None and
            curr_page.goodbye.y_rel <= TOP_THIRD_THRESHOLD):
            score -= 100
            factors.append("Goodbye at top (-100)")
        
        # 4. The "Single Page" Bonus
        # +200: Previous page contains both Greeting and Goodbye, and goodbye.y_rel > greeting.y_rel
        if (prev_page.greeting.found and prev_page.goodbye.found and
            prev_page.greeting.y_rel is not None and prev_page.goodbye.y_rel is not None and
            prev_page.goodbye.y_rel > prev_page.greeting.y_rel):
            score += 200
            factors.append("Previous page complete letter (+200)")
        
        return score, factors


def group_pages_into_letters(pages: list[PageAnalysis]) -> list[Letter]:
    """
    Group a sequence of PageAnalysis objects into logical Letter objects.
    
    This is the main entry point for document splitting. It iterates through
    pages and uses the TransitionScorer to determine where to split.
    
    Args:
        pages: List of PageAnalysis objects to group
    
    Returns:
        List of Letter objects, each containing related pages
    """
    if not pages:
        logger.debug("No pages to group")
        return []
    
    scorer = TransitionScorer()
    letters = []
    current_letter_pages = [pages[0]]
    
    logger.debug(f"Starting grouping with {len(pages)} pages")
    
    # Iterate through consecutive page pairs
    for i in range(1, len(pages)):
        prev_page = pages[i - 1]
        curr_page = pages[i]
        
        # Score the transition
        score, factors = scorer.score_transition(prev_page, curr_page)
        
        # Log the decision
        if score > SPLIT_THRESHOLD:
            logger.debug(f"Split at Page {curr_page.scan_page_num} (Score: {score}). Factors: {', '.join(factors)}")
            # Create a new letter with accumulated pages
            letters.append(Letter(pages=current_letter_pages))
            current_letter_pages = [curr_page]
        else:
            logger.debug(f"Continue at Page {curr_page.scan_page_num} (Score: {score}). Factors: {', '.join(factors) if factors else 'None'}")
            current_letter_pages.append(curr_page)
    
    # Don't forget the last letter
    if current_letter_pages:
        letters.append(Letter(pages=current_letter_pages))
    
    logger.info(f"Grouped {len(pages)} pages into {len(letters)} letters")
    
    # Post-process validation
    _validate_letters(letters)
    
    return letters


def _validate_letters(letters: list[Letter]) -> None:
    """
    Validate letter groups for consistency and log warnings for issues.
    
    Checks for gaps in LetterPageIndex sequences within each letter.
    
    Args:
        letters: List of Letter objects to validate
    """
    for letter_idx, letter in enumerate(letters, start=1):
        # Check for gaps in page indices
        page_indices = []
        for page in letter.pages:
            if page.letter_page_index.found and page.letter_page_index.current is not None:
                page_indices.append(page.letter_page_index.current)
        
        if page_indices:
            # Check for gaps in the sequence
            expected_indices = list(range(min(page_indices), max(page_indices) + 1))
            if page_indices != expected_indices:
                logger.warning(
                    f"Letter {letter_idx} has gaps in page indices. "
                    f"Found: {page_indices}, Expected: {expected_indices}. "
                    f"Scan pages: {[p.scan_page_num for p in letter.pages]}"
                )
