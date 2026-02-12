#!/usr/bin/env python3
"""Monkey patch josepy to add ComparableX509 for acme compatibility."""
import josepy

# Add ComparableX509 as an alias for ComparableKey to fix acme compatibility
josepy.ComparableX509 = josepy.ComparableKey
