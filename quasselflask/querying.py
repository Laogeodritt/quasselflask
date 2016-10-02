"""
Functions for querying the database and 'controller' functions for database write operations.

Project: QuasselFlask
"""

import sqlalchemy.orm
from sqlalchemy import desc, and_, or_

from quasselflask import app
from quasselflask.models import Backlog, Buffer, Sender
from quasselflask.parsing.form import convert_str_to_datetime, extract_glob_list, convert_glob_to_like, escape_like
from quasselflask.parsing.query import BooleanQuery


def build_db_query(session, args) -> sqlalchemy.orm.query.Query:
    # prepare SQL query joins
    query = session.query(Backlog).join(Buffer).join(Sender)  # type: sqlalchemy.orm.query.Query

    # Unique arguments
    query_wildcard = args.get('query_wildcard', None, int)  # use later

    limit = args.get('limit', app.config['RESULTS_NUM_DEFAULT'], int)
    if limit > app.config['RESULTS_NUM_MAX']:
        limit = app.config['RESULTS_NUM_MAX']

    start = None
    if args.get('start'):
        try:
            start = convert_str_to_datetime(args.get('start'))
            query = query.filter(Backlog.time >= start)
        except ValueError as e:
            raise ValueError('Invalid start time format: must be in YYYY-MM-DD HH:MM:SS.SSS format.') from e

    end = None
    if args.get('end'):
        try:
            end = convert_str_to_datetime(args.get('end'))
            query = query.filter(Backlog.time <= end)
        except ValueError as e:
            raise ValueError('Invalid end time format: must be in YYYY-MM-DD HH:MM:SS.SSS format.') from e

    # Flat-list arguments
    channels = extract_glob_list(args.get('channel', ''))
    for channel in channels:
        query = query.filter(Buffer.buffername.ilike(channel))

    usermasks = extract_glob_list(args.get('usermask', ''))
    for usermask in usermasks:
        query = query.filter(Sender.sender.ilike(usermask))

    # fulltext string
    query_message_filter, parsed_query = parse_search_query(args.get('query'), query_wildcard)
    if query_message_filter is not None:
        query = query.filter(query_message_filter)

    query = query.order_by(desc(Backlog.time)).limit(limit)

    app.logger.debug("Args|SQL-processed: limit=%i channel%s usermask%s start[%s] end[%s] query%s %s",
                     limit, channels, usermasks, start.isoformat() if start else '', end.isoformat() if end else '',
                     parsed_query, '[wildcard]' if query_wildcard else '[no_wildcard]')\

    return query


def parse_search_query(query_str: str, query_wildcard: bool) -> (sqlalchemy.orm.Query, [str]):
    """
    Parse a query string for a boolean search and return an SQLAlchemy object that can be passed to filter() or
    expression.select().where().

    This is a glue function between the quasselflask.query.BooleanQuery parser and the SQLAlchemy backend.

    :param query_str: Input query string.
    :param query_wildcard: If true, search tokens are considered to allow wildcards and a LIKE search is performed
        instead of a keyword search. (Note that a LIKE search doesn't necessarily break on word boundaries, so
        a search of "back" can match "backed" or "aback", even without wildcards.)
    :return: SQLAlchemy query object for a filter() call
    """

    def wildcard(s: str):
        if isinstance(s, str):
            return Backlog.message.ilike('%' + convert_glob_to_like(s)[0] + '%')
        else:
            return s  # can also be a boolean SQL condition object

    def plain(s: str):
        if isinstance(s, str):
            return Backlog.message.ilike('%' + escape_like(s) + '%')
        else:
            return s  # can also be a boolean SQL condition object

    q = BooleanQuery(query_str, app.logger)
    q.tokenize()
    q.parse()
    if query_wildcard:
        sql_query_filter = q.eval(and_, or_, wildcard)
    else:
        sql_query_filter = q.eval(and_, or_, plain)
    return sql_query_filter, q.get_parsed()
