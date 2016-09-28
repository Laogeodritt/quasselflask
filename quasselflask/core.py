"""
Main QuasselFlask package.

Project: QuasselFlask
"""

import os
import time

import sqlalchemy.orm
import sqlalchemy.orm.query  # for IDE inspection
from flask import Flask, request, g, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy, get_debug_queries
from sqlalchemy import MetaData, and_, or_, desc
from sqlalchemy.ext.automap import automap_base

from quasselflask.irclog import BacklogType, DisplayBacklog
from quasselflask.query_parser import BooleanQuery
from quasselflask.search_params import convert_str_to_datetime, escape_like, extract_glob_list, convert_glob_to_like


__version__ = "0.1"


class DefaultConfig:
    """
    These configuration variables can be copied into your quasselflask.cfg file and changed.
    Only copy the lines you want to change. You don't need to copy all of them if the defaults are OK.
    """
    # SQLALCHEMY_DATABASE_URI = 'postgresql://sqluser:password@hostname-or-IP-address/databasename'
    SITE_NAME = 'SiteName'
    MAX_RESULTS_DEFAULT = 100  # Default maximum results set in the search form
    MAX_RESULTS = 1000  # Maximum number of results per query, regardless of search form settings.
    TIME_FORMAT = '{:%Y-%m-%d %H:%M:%S}'


class LibraryConfig:
    """
    Configurations for the libraries. Do not change these unless you know what you're doing.
    """
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = bool(os.environ.get('FLASK_DEBUG', 0))


# Bootstrap the application
app = Flask(__name__, instance_path=os.environ.get('QF_CONFIG_PATH', None), instance_relative_config=True)
app.config.from_object(DefaultConfig)
app.config.from_object(LibraryConfig)
app.config.from_pyfile('quasselflask.cfg')

DisplayBacklog.set_time_format(app.config['TIME_FORMAT'])

# Bootstrap the database
# Reflection + automap provides flexibility in case of future quassel changes
# (especially schema changes that don't affect quasselflask's search params!)
db = SQLAlchemy(app)
db_metadata = MetaData()
db_tables = ['backlog', 'sender', 'buffer']  # TODO
db_metadata.reflect(db.engine, only=db_tables)
Base = automap_base(metadata=db_metadata)
Base.prepare()

Backlog = Base.classes.backlog
Sender = Base.classes.sender
Buffer = Base.classes.buffer


def __repr_backlog(self):
    try:
        type_str = BacklogType(self.type).name
    except IndexError:
        type_str = 'Unknown'
    return "[{:%Y-%m-%d %H:%M:%S}] [{}]<{}:{}> {}".format(self.time, type_str, self.buffer.buffername,
                                                          self.sender.sender, self.message)


Backlog.__repr__ = __repr_backlog


@app.before_request
def globals_init():
    g.start_time = time.time()
    g.get_request_time = lambda: "{:.3f}s".format(time.time() - g.start_time)
    g.display_version = __version__


@app.route('/')
def home():
    return render_template('search_form.html')


@app.route('/search')
def search():
    # some helpful constants for the request argument processing
    # type of extraction/processing - this is more documentation as it's not used to process at the moment
    unique_args = {'start', 'end', 'limit', 'query_wildcard'}
    list_wildcard_args = {'channel', 'usermask'}  # space-separated lists; if any arg repeated, list is concatenated
    query_args = {'query'}  # requires query parsing
    search_args = unique_args | list_wildcard_args | query_args

    args = request.args
    available_args = search_args & set(args.keys())

    # if no arguments passed, we can just redirect to the home
    if not available_args:
        return redirect(url_for('home'))

    try:
        results = reversed(_search_build_query().all())
    except ValueError as e:
        return render_template('search_form.html', error=e.args[0],
                               search_channel=args.get('channel'), search_usermask=args.get('usermask'),
                               search_start=args.get('start'), search_end=args.get('end'),
                               search_query=args.get('query'), search_query_wildcard=args.get('query_wildcard', type=bool),
                               search_limit=args.get('limit', app.config['MAX_RESULTS_DEFAULT'], int))

    if get_debug_queries():
        info = get_debug_queries()[0]
        app.logger.debug("SQL: {}\nParameters: {}\nDuration: {:.3f}s".format(
                info.statement, repr(info.parameters), info.duration))

    return render_template('results.html', records=[DisplayBacklog(result) for result in results],
                           search_channel=args.get('channel'), search_usermask=args.get('usermask'),
                           search_start=args.get('start'), search_end=args.get('end'),
                           search_query=args.get('query'), search_query_wildcard=args.get('query_wildcard', type=bool),
                           search_limit=args.get('limit', app.config['MAX_RESULTS_DEFAULT'], int))


def _search_build_query() -> sqlalchemy.orm.query.Query:
    # prepare SQL query joins
    query = db.session.query(Backlog).join(Buffer).join(Sender)  # type: sqlalchemy.orm.query.Query

    # Extract and process args for the SQL queries
    args = request.args

    # Unique arguments
    query_wildcard = args.get('query_wildcard', None, int)  # use later

    limit = args.get('limit', app.config['MAX_RESULTS_DEFAULT'], int)

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
    query_message_filter, parsed_query = parse_query(args.get('query'), query_wildcard)
    if query_message_filter is not None:
        query = query.filter(query_message_filter)

    query = query.order_by(desc(Backlog.time)).limit(limit)

    app.logger.debug("Args|SQL-processed: limit=%i channel%s usermask%s start[%s] end[%s] query%s %s",
                     limit, channels, usermasks, start.isoformat() if start else '', end.isoformat() if end else '',
                     parsed_query, '[wildcard]' if query_wildcard else '[no_wildcard]')\

    return query


@app.route('/context/<int:post_id>/<int:num_context>')
def context(post_id, num_context):
    pass  # TODO context endpoint


if os.environ.get('QF_ALLOW_TEST_PAGES'):
    @app.route('/test/parse')
    def test_parse():
        pass  # TODO: test_parse endpoint


def parse_query(query_str: str, query_wildcard: bool) -> (sqlalchemy.orm.Query, [str]):
    """
    Parse a query string for a boolean search and return an SQLAlchemy object that can be passed to filter() or
    expression.select().where().
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


if __name__ == '__main__':
    app.run()
