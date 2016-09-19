"""
Parser for binary search queries (Google-like). Supports:

* AND and OR operators (equal-precedence, left-associative)
* Implicit AND of multiple space-separated words
* Parenthesis grouping
* String literals using double-quotes (can be used to match parentheses and the words AND/OR too)
* Escaped double-quote literal '\"'

Project: QuasselFlask
"""
