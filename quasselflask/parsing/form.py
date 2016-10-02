"""
Form input parameters parsing and conversion tools (for preparing and sanitising for database queries).

Project: QuasselFlask
"""

import re
from datetime import datetime

from quasselflask import app
from quasselflask.parsing.query import BooleanQuery


def process_search_params(in_args) -> dict:
    """
    Process arguments for the /search endpoint.

    Keys returned:

    - query_wildcard: boolean - always set (default false)
    - limit: int - if not set, set to default value in configuration; limited to the max value in configuration
    - start: datetime|None
    - end: datetime|None
    - channels: list (may be empty)
    - usermasks: list (may be empty)
    - query: quasselflask.parsing.query.BooleanQuery

    :param in_args:
    :return:
    """
    out_args = dict()

    # Unique arguments
    out_args['query_wildcard'] = bool(in_args.get('query_wildcard', None, int))

    out_args['limit'] = in_args.get('limit', app.config['RESULTS_NUM_DEFAULT'], int)
    if out_args['limit'] > app.config['RESULTS_NUM_MAX']:
        out_args['limit'] = app.config['RESULTS_NUM_MAX']

    out_args['start'] = None
    if in_args.get('start'):
        try:
            out_args['start'] = convert_str_to_datetime(in_args.get('start'))
        except ValueError as e:
            raise ValueError('Invalid start time format: must be in YYYY-MM-DD HH:MM:SS.SSS format.') from e

    out_args['end'] = None
    if in_args.get('end'):
        try:
            out_args['end'] = convert_str_to_datetime(in_args.get('end'))
        except ValueError as e:
            raise ValueError('Invalid end time format: must be in YYYY-MM-DD HH:MM:SS.SSS format.') from e

    # Flat-list arguments
    out_args['channels'] = extract_glob_list(in_args.get('channel', ''))
    out_args['usermasks'] = extract_glob_list(in_args.get('usermask', ''))

    # fulltext string
    out_args['query'] = BooleanQuery(in_args.get('query', ''), app.logger)
    out_args['query'].tokenize()
    out_args['query'].parse()

    return out_args


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
