"""
Functions for querying the database and 'controller' functions for database write operations.

Project: QuasselFlask
"""

import sqlalchemy.orm
from sqlalchemy import desc, asc, and_, or_

from quasselflask import app
from quasselflask.models import QuasselUser, Network, Backlog, Buffer, Sender, QfUser
from quasselflask.parsing.form import convert_glob_to_like, escape_like
from quasselflask.parsing.irclog import BufferType
from quasselflask.parsing.query import BooleanQuery


def build_db_search_query(session, args) -> sqlalchemy.orm.query.Query:
    """
    Builds database query (as an SQLAlchemy Query object) for an IRC backlog search. This function does very little
    checking on ``args``, as it assumes the args have already been processed and validated and reasonable defaults set.

    :param session: Database session (SQLAlchemy)
    :param args: Search parameters as returned by quasselflask.parsing.form.process_search_params()
    :return:
    """
    # prepare SQL query joins
    query = session.query(Backlog).join(Buffer).join(Sender)  # type: sqlalchemy.orm.query.Query

    if args.get('start'):
        query = query.filter(Backlog.time >= args.get('start'))

    if args.get('end'):
        query = query.filter(Backlog.time <= args.get('end'))

    # Flat-list arguments
    for channel in args.get('channels'):
        query = query.filter(Buffer.buffername.ilike(channel))
    for usermask in args.get('usermasks'):
        query = query.filter(Sender.sender.ilike(usermask))

    # fulltext string
    query_message_filter = build_sql_search_terms(args.get('query'), args.get('query_wildcard', None))
    if query_message_filter is not None:
        query = query.filter(query_message_filter)

    if args.get('order') == 'newest':
        query = query.order_by(desc(Backlog.time))
    else:
        query = query.order_by(asc(Backlog.time))

    query = query.limit(args.get('limit'))

    return query


def build_sql_search_terms(query: BooleanQuery, query_wildcard: bool) -> (sqlalchemy.orm.Query, [str]):
    """
    Parse a query string for a boolean search and return an SQLAlchemy object that can be passed to filter() or
    expression.select().where().

    This is a glue function between the quasselflask.query.BooleanQuery parser and the SQLAlchemy backend.

    :param query: Input query. If this object has not been tokenized or parsed yet, this will be executed first.
    :param query_wildcard: If true, search tokens are considered to allow wildcards and a LIKE search is performed
        instead of a keyword search. (Note that a LIKE search doesn't necessarily break on word boundaries, so
        a search of "back" can match "backed" or "aback", even without wildcards.)
    :return: SQLAlchemy query object that can be used as the argument to a filter() call
    """

    # Callback functions for query.eval
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

    if query is None:
        return None

    # If needed, parse the query first
    if not query.is_tokenized:
        query.tokenize()
    if not query.is_parsed:
        query.parse()

    # Build the search query
    if query_wildcard:
        sql_query_filter = query.eval(and_, or_, wildcard)
    else:
        sql_query_filter = query.eval(and_, or_, plain)
    return sql_query_filter


def query_all_qf_users(session) -> sqlalchemy.orm.query.Query:
    """
    Query the database for all QuasselFlask users.
    :param session: Database session (SQLAlchemy)
    :return: SQLAlchemy results
    """
    query = session.query(QfUser).order_by(asc(QfUser.qfuserid))  # type: sqlalchemy.orm.query.Query
    return query


def query_quasselusers(session) -> sqlalchemy.orm.query.Query:
    """
    Query the database for all Quassel users.
    :param session: Database session (SQLAlchemy)
    :return:
    """
    query = session.query(QuasselUser).order_by(asc(QuasselUser.username))  # type: sqlalchemy.orm.query.Query
    return query


def query_networks(session) -> sqlalchemy.orm.query.Query:
    """
    Query the database for all Quassel networks.
    :param session: Database session (SQLAlchemy)
    :return:
    """
    query = session.query(Network).order_by(asc(Network.networkname))  # type: sqlalchemy.orm.query.Query
    return query


def query_buffers(session, buffertypes=None) -> sqlalchemy.orm.query.Query:
    """
    Query the database for all Quassel buffers of the specified type.
    :param session: Database session (SQLAlchemy)
    :param buffertypes: Buffer type or list of buffer types to retrieve (if None, query everything)
    :return:
    """
    query = session.query(Buffer)  # type: sqlalchemy.orm.query.Query
    if isinstance(buffertypes, BufferType):
        query = query.filter(Buffer.bufferType == buffertypes)
    elif buffertypes:
        query = query.filter(Buffer.buffertype.in_(buffertypes))
    query = query.order_by(asc(Buffer.buffertype), asc(Buffer.buffername))
    return query


def query_qfuser(qfuserid) -> QfUser:
    """
    Find a user.
    :param qfuserid:
    :return: QfUser
    :raise NotFound: User not found.
    """
    from quasselflask import db
    from werkzeug.exceptions import NotFound
    try:
        return db.session.query(QfUser).filter(QfUser.qfuserid == qfuserid).one()
    except sqlalchemy.orm.exc.NoResultFound as e:
        raise NotFound("No such user.")
