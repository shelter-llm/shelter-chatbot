#!/usr/bin/env python3
"""
Test script for intelligent location extraction feature.
Tests the regex pattern matching for various query formats.
"""

import re
from typing import Optional


def extract_location_from_query(query: str) -> Optional[str]:
    """
    Extract location names from user queries using pattern matching.
    
    Supports patterns like:
    - "från [location]" (Swedish: "from [location]")
    - "near [location]" (English)
    - "vid [location]" (Swedish: "at [location]")
    - "i [location]" (Swedish: "in [location]")
    - "nära [location]" (Swedish: "near [location]")
    
    Returns the first matched location or None.
    """
    # Pattern to match location references
    # Matches capitalized words, stops at punctuation, spaces followed by lowercase, or conjunctions
    patterns = [
        r"från\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)",
        r"from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"vid\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)",
        r"nära\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)",
        r"near\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"i\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)\??",  # Allow optional ?
        r"in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            location = match.group(1).strip()
            # Stop at conjunctions manually
            for conjunction in [" eller", " or", ","]:
                if conjunction in location:
                    location = location.split(conjunction)[0].strip()
            # Filter out common non-location words
            exclude_words = ["Vilka", "Visa", "Find", "Show", "Which", "What"]
            if location and location not in exclude_words:
                return location
    
    return None


def test_location_extraction():
    """Run test cases for location extraction."""
    
    test_cases = [
        # Swedish patterns
        ("5 skyddsrum från Ångströmlaboratoriet", "Ångströmlaboratoriet"),
        ("Vilka är de närmaste skyddsrummen från Centralstationen?", "Centralstationen"),
        ("Jag är vid Uppsala Slott", "Uppsala Slott"),
        ("Skyddsrum nära Fyrishov", "Fyrishov"),
        ("Finns det skyddsrum i Gottsunda?", "Gottsunda"),
        
        # English patterns
        ("Find 3 shelters from Central Station", "Central Station"),
        ("Shelters near Resecentrum", "Resecentrum"),
        ("I'm at Fyrishov", "Fyrishov"),
        ("Show me shelters in Centrum", "Centrum"),
        
        # Multi-word locations
        ("från Uppsala Slott", "Uppsala Slott"),
        ("near Central Station", "Central Station"),
        ("vid Ångströmlaboratoriet", "Ångströmlaboratoriet"),  # Proper capitalization
        
        # No location (should return None)
        ("Hur många skyddsrum finns det?", None),
        ("What is the largest shelter?", None),
        ("Visa alla skyddsrum", None),
        ("Show me all shelters", None),
        
        # Edge cases
        ("från Centralstationen eller Uppsala Slott", "Centralstationen"),  # Multiple locations, takes first
        ("5 skyddsrum", None),  # No location keyword
    ]
    
    print("=" * 80)
    print("LOCATION EXTRACTION TEST SUITE")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for query, expected in test_cases:
        result = extract_location_from_query(query)
        
        if result == expected:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1
        
        print(f"{status}")
        print(f"  Query:    '{query}'")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        print()
    
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = test_location_extraction()
    exit(0 if success else 1)
