"""
Search input parameters parsing and conversion tools (for preparing and sanitising for database queries).

Project: QuasselFlask
"""
import re
from datetime import datetime


def convert_str_to_datetime(s: str) -> datetime:
    """
    Convert a string of format "YYYY-MM-DD HH:MM:SS" (24-hour) into a datetime object with no timezone. This method
    can accept '-', '/', ':', ' ' or '.' for the date and time separators in any combination, allowing flexibility for
    user inputs.
    :param s: Input datetime string.
    :return: Datetime object corresponding to the string.
    :raises ValueError: String format is invalid.
    """
    dt_format_arr = ['%Y', '%m', '%d', '%H', '%M', '%S']
    norm_s = s.replace('/', '-').replace(':', '-').replace('.', '-').replace(' ', '-').strip('-')
    norm_s = re.sub('-+', '-', norm_s)
    segments_count = norm_s.count('-') + 1
    return datetime.strptime(norm_s, '-'.join(dt_format_arr[0:segments_count]))


def escape_like(s: str) -> str:
    """
    Escape special characters _ and % for LIKE queries, as well as the escape character '\'.
    :param s:
    :return:
    """
    if s is None:
        return None
    return s.replace('\\', '\\\\').replace('_', '\\_').replace('%', '\\%')


def extract_glob_list(s: str, sep=' ') -> [str]:
    """
    Extracts an argument of `sep`-separated items, splits it into a list, and converts GLOB-style syntax to SQL LIKE-
    style syntax, ready for use in SQLAlchemy.

    :param s: Argument string to split.
    :param sep: The separator character.
    :return: List of extracted strings. If the `key` is not present in `args`, or its value is empty, returns an
            empty list.
    """
    return [convert_glob_to_like(s)[0] for s in s.split(sep) if s and not s.isspace()]


def convert_glob_to_like(s: str) -> (str, bool):
    """
    Converts a glob-style wildcard string to SQL LIKE syntax. Only handles conversion of * and ? to % and _, plus
    escaped characters via '\' (no character classes). NOTE: Does not place % around the expression.
    :param s: Glob string to convert.
    :return: (like_str, hasWildcards) - hasWildcards is True if a non-escaped wildcard was found.
    """
    if s is None:
        return None

    s_parse = []
    is_escaped = False
    has_wildcards = False
    for c in s:
        if is_escaped:
            if c == '\\':
                s_parse.append('\\\\')
            elif c == '*' or c == '?':
                s_parse.append(c)
            elif c == '_' or c == '%':
                s_parse.append('\\' + c)
            else:
                s_parse.append(c)
            is_escaped = False
        else:
            if c == '\\':
                is_escaped = True
            elif c == '*':
                s_parse.append('%')
                has_wildcards = True
            elif c == '?':
                s_parse.append('_')
                has_wildcards = True
            elif c == '_' or c == '%':
                s_parse.append('\\' + c)
            else:
                s_parse.append(c)
    if is_escaped:  # in case there's a hanging backslash
        s_parse.append('\\\\')
    return ''.join(s_parse), has_wildcards
