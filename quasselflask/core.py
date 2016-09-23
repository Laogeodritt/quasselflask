"""
Main QuasselFlask package.

Project: QuasselFlask
"""

import os
import re
import time
from datetime import datetime
from enum import Enum
from typing import Callable

import sqlalchemy.orm
import sqlalchemy.orm.query  # for IDE inspection
from flask import Flask, request, g, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy, get_debug_queries
from sqlalchemy import MetaData, and_, or_, desc
from sqlalchemy.ext.automap import automap_base

from quasselflask.query_parser import extract_glob_list, convert_glob_to_like, escape_like, BooleanQuery

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


class LibraryConfig:
    """
    Configurations for the libraries. Do not change these unless you know what you're doing.
    """
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = bool(os.environ['FLASK_DEBUG'])


# Bootstrap the application
app = Flask(__name__, instance_path=os.environ.get('QF_CONFIG_PATH', None), instance_relative_config=True)
app.config.from_object(DefaultConfig)
app.config.from_object(LibraryConfig)
app.config.from_pyfile('quasselflask.cfg')

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
    return "[{:%Y-%m-%d %H:%M:%S}] [{:d}]<{}:{}> {}".format(self.time, self.type, self.buffer.buffername,
                                                            self.sender.sender, self.message)


Backlog.__repr__ = __repr_backlog


class BacklogType(Enum):
    """
    https://github.com/quassel/quassel/blob/master/src/common/message.h
    That is all.
    """
    Plain = 0x00001
    Notice = 0x00002
    Action = 0x00004
    Nick = 0x00008
    Mode = 0x00010
    Join = 0x00020
    Part = 0x00040
    Quit = 0x00080
    Kick = 0x00100
    Kill = 0x00200
    Server = 0x00400
    Info = 0x00800
    Error = 0x01000
    DayChange = 0x02000
    Topic = 0x04000
    NetsplitJoin = 0x08000
    NetsplitQuit = 0x10000
    Invite = 0x20000


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

    # prepare SQL query joins
    query = db.session.query(Backlog).join(Buffer).join(Sender)  # type: sqlalchemy.orm.query.Query

    # Extract and process args for the SQL queries
    # Unique arguments
    query_wildcard = args.get('query_wildcard', None, int)  # use later

    limit = args.get('limit', app.config['MAX_RESULTS_DEFAULT'], int)

    start = None
    if 'start' in available_args:
        try:
            start = convert_str_to_datetime(args.get('start'))
            query = query.filter(Backlog.time >= start)
        except ValueError:
            pass  # TODO: handle error

    end = None
    if 'end' in available_args:
        try:
            end = convert_str_to_datetime(args.get('end'))
            query = query.filter(Backlog.time <= end)
        except ValueError:
            pass  # TODO: handle error

    # Flat-list arguments
    channels = extract_glob_list(args.get('channel', ''))
    for channel in channels:
        query = query.filter(Buffer.buffername.ilike(channel))  # TODO: ilike efficiency?

    usermasks = extract_glob_list(args.get('usermask', ''))
    for usermask in usermasks:
        query = query.filter(Sender.sender.ilike(usermask))  # TODO: ilike efficiency?

    # fulltext string
    query_message_filter, parsed_query = parse_query(args.get('query'), query_wildcard)
    if query_message_filter is not None:
        query = query.filter(query_message_filter)

    results = reversed(query.order_by(desc(Backlog.time)).limit(limit).all())

    app.logger.debug("Args|SQL-processed: limit=%i channel%s usermask%s start[%s] end[%s] query%s %s",
                     limit, channels, usermasks, start.isoformat() if start else '', end.isoformat() if end else '',
                     parsed_query, '[wildcard]' if query_wildcard else '[no_wildcard]')

    info = get_debug_queries()[0]
    app.logger.debug("SQL: {}\nParameters: {}\nDuration: {:.3f}s".format(
            info.statement, repr(info.parameters), info.duration))
    app.logger.debug("Results:\n" + '\n'.join([repr(result) for result in results]))

    # TODO: display results
    return render_template('search_form.html', search_channel=args.get('channel'), search_usermask=args.get('usermask'),
                           search_start=args.get('start'), search_end=args.get('end'),
                           search_query=args.get('query'), search_query_wildcard=args.get('query_wildcard', type=bool),
                           search_limit=args.get('limit', app.config['MAX_RESULTS_DEFAULT'], int))


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

    def make_query_evaluator(operator: Callable[[str, str], sqlalchemy.orm.Query]):
        def evaluator(a: str, b: str):
            return operator(a, b)
        return evaluator

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


if __name__ == '__main__':
    app.run()
