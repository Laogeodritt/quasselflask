"""
Helper functions for database queries.

This module need not be a strong abstraction layer: views or other modules do manipulate declarative model objects
directly along with SQLAlchemy methods (e.g. and_/or_ to generate queries; session commits).

Project: QuasselFlask
"""

import sqlalchemy.orm
from sqlalchemy import desc, asc, and_, or_, func

from quasselflask.models.models import QfPermission
from quasselflask.models.models import QuasselUser, Network, Backlog, Buffer, Sender, QfUser
from quasselflask.models.types import PermissionAccess as Access, PermissionType as Type
from quasselflask.parsing.form import convert_glob_to_like, escape_like
from quasselflask.parsing.irclog import BufferType
from quasselflask.parsing.query import BooleanQuery


def build_query_backlog(session, args, query_options=tuple()) -> sqlalchemy.orm.Query:
    """
    Builds database query (as an SQLAlchemy Query object) for an IRC backlog search, given various search parameters.
    This function does very little checking on the structure of ``args``, as it assumes the args have already been
    processed and validated and reasonable defaults set.

    :param session: Database session (SQLAlchemy)
    :param args: Search parameters as returned by quasselflask.parsing.form.process_search_params(). Refer to that
        function for structure information.
    :param query_options: iterable of options passed to Query.options()
    :return:
    """
    # prepare SQL query joins
    query = session.query(Backlog).join(Buffer).join(Sender)  # type: sqlalchemy.orm.query.Query
    if query_options:
        query = query.options(*query_options)
    query = _apply_backlog_search_filter(query, args)

    if args.get('order') == 'newest':
        query = query.order_by(desc(Backlog.time))
    else:
        query = query.order_by(asc(Backlog.time))

    query = query.limit(args.get('limit'))

    return query


def build_query_usermask(session, args) -> sqlalchemy.orm.Query:
    """
    Builds database query (as an SQLAlchemy Query object) for an IRC usermask search, given various search parameters
    on the user and backlog where the user may have been seen speaking, joining or otherwise active.
    This function does very little checking on the structure of ``args``, as it assumes the args have already been
    processed and validated and reasonable defaults set.

    :param session: Database session (SQLAlchemy)
    :param args: Search parameters as returned by quasselflask.parsing.form.process_search_params(). Refer to that
        function for structure information.
    :return:
    """
    backlog_query = build_query_backlog(session, args).subquery()
    query = session.query(Sender, func.count('*').label('line_count'))\
        .join(backlog_query, Sender.senderid == backlog_query.c.senderid)\
        .group_by(Sender.senderid)\
        .order_by(desc('line_count'))
    return query


def _apply_backlog_search_filter(query: sqlalchemy.orm.Query, args: dict) -> sqlalchemy.orm.Query:
    """
    Applies the filter criteria from ``args`` (Backlog start/end time, Backlog message text search, Buffer name,
    current user Buffer permissions) onto an existing query ``query``.

    See ``build_query_backlog()`` for example usage.

    :param query:
    :param args:
    :return:
    """
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
    query_message_filter = build_filter_backlog_fulltext(args.get('query'), args.get('query_wildcard', None))
    if query_message_filter is not None:
        query = query.filter(query_message_filter)

    query = query.filter(Buffer.bufferid.in_(pbuf.bufferid for pbuf in args['permissions']))

    return query


def build_filter_backlog_fulltext(query: BooleanQuery, query_wildcard: bool) -> (sqlalchemy.orm.Query, [str]):
    """
    Parse a BooleanQuery (parsed boolean search query) and return an SQLAlchemy object that can be passed to filter() or
    expression.select().where().

    This is a glue function between the quasselflask.query.BooleanQuery parser and the SQLAlchemy backend. It is
    primarily an internal method called by ``quasselflask.querying.build_query_backlog``.

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
    :param buffertypes: BufferType (enum value) or list/tuple of BufferType to retrieve (if None, query everything).
    :return:
    """
    query = session.query(Buffer)  # type: sqlalchemy.orm.query.Query
    try:
        query = query.filter(Buffer.buffertype.in_(bt.value for bt in buffertypes))
    except TypeError:
        # maybe it's a single value
        query = query.filter(Buffer.buffertype == buffertypes.value)
    query = query.order_by(asc(Buffer.buffertype), asc(Buffer.buffername))
    return query


def query_qfuser(session: sqlalchemy.orm.Session, qfuserid: int) -> QfUser:
    """
    Find a user.
    :param session: SQLAlchemy session to use
    :param qfuserid: ID to query
    :return: QfUser
    :raise NotFound: User not found.
    """
    from quasselflask import db
    from werkzeug.exceptions import NotFound
    try:
        return db.session.query(QfUser).filter(QfUser.qfuserid == qfuserid).one()
    except sqlalchemy.orm.exc.NoResultFound as e:
        raise NotFound("No such user.") from e


def query_permitted_buffers(session: sqlalchemy.orm.Session, user: QfUser) -> [int]:
    """
    Return a list of buffers that the user is permitted to access.

    :param session: Database session to use
    :param user: User whose permissions to search
    :return: List of Buffer objects
    """
    permissions = {
        'users': tuple(perm for perm in user.permissions if perm.type == Type.user),
        'networks': tuple(perm for perm in user.permissions if perm.type == Type.network),
        'buffers': tuple(perm for perm in user.permissions if perm.type == Type.buffer),
    }
    permitted_buffers = []

    for buffer in query_buffers(session, BufferType.channel_buffer):  # type: Buffer
        # Priority 1: buffer match
        try:
            buffer_perm = next(perm for perm in permissions['buffers'] if perm.bufferid == buffer.bufferid)  \
                # type: QfPermission
            # If allow, add it to the list; if deny, short-circuit current buffer. Then continue to next buffer.
            if buffer_perm.access is Access.allow:
                permitted_buffers.append(buffer)
            continue
        except StopIteration:  # if next() doesn't find a match
            pass

        # Priority 2: network match
        try:
            network_perm = next(perm for perm in permissions['networks'] if perm.networkid == buffer.networkid) \
                # type: QfPermission
            if network_perm.access is Access.allow:
                permitted_buffers.append(buffer)
            continue
        except StopIteration:  # if next() doesn't find a match
            pass

        try:
            user_perm = next(perm for perm in permissions['users'] if perm.userid == buffer.network.userid) \
                # type: QfPermission
            if user_perm.access is Access.allow:
                permitted_buffers.append(buffer)
            continue
        except StopIteration:  # if next() doesn't find a match
            pass

        # default access value
        if user.access is Access.allow or user.is_superuser:
            permitted_buffers.append(buffer)
        continue

    return permitted_buffers
