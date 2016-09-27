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

import crcmod.predefined
calculateNicknameHash = crcmod.predefined.mkPredefinedCrcFun('x-25')

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


# CLASSES

class BacklogType(Enum):
    """
    https://github.com/quassel/quassel/blob/master/src/common/message.h
    That is all.
    """
    privmsg = 0x00001
    notice = 0x00002
    action = 0x00004
    nick = 0x00008
    mode = 0x00010
    join = 0x00020
    part = 0x00040
    quit = 0x00080
    kick = 0x00100
    kill = 0x00200
    server = 0x00400
    info = 0x00800
    error = 0x01000
    daychange = 0x02000
    topic = 0x04000
    netsplit_join = 0x08000
    netsplit_quit = 0x10000
    invite = 0x20000


class Color(Enum):
    """
    Colours used in the nickname colour field. Names may be used directly in CSS and should coordinate with CSS classes,
    e.g.::

        nick_color = Color.red  # determined by some algorithm
        html += '<span class="nick-' + nick_color.name() + '">User</span>'

    And in CSS::

        .nick-red { color: #ff0000; }

    """
    yellow = 0
    orange = 1
    red = 2
    magenta = 3
    violet = 4
    blue = 5
    cyan = 6
    green = 7


class DisplayBacklog:
    _icon_type_map = {
        BacklogType.privmsg: '',
        BacklogType.notice: '',
        BacklogType.action: '-*-',
        BacklogType.nick: '<->',
        BacklogType.mode: '***',
        BacklogType.join: '-->',
        BacklogType.part: '<--',
        BacklogType.quit: '<--',
        BacklogType.kick: '***',
        BacklogType.kill: '***',
        BacklogType.server: '*',
        BacklogType.info: 'i',
        BacklogType.error: '!!!',
        BacklogType.daychange: '*',
        BacklogType.topic: '*',
        BacklogType.netsplit_join: '-->',
        BacklogType.netsplit_quit: '<--',
        BacklogType.invite: '*',
    }

    def __init__(self, backlog: Backlog):
        """
        :param backlog: Backlog string
        """
        self.time = app.config['TIME_FORMAT'].format(backlog.time)  # type: str
        self.channel = backlog.buffer.buffername  # type: str
        self.sender = backlog.sender.sender  # type: str
        self.nickname = self.sender.split('!', 1)[0]  # type: str
        try:
            self.type = BacklogType(backlog.type)
        except IndexError:
            self.type = BacklogType.privmsg
        self.message = backlog.message  # type: str

    def get_icon_text(self):
        return self._icon_type_map.get(self.type, '')

    def get_nick_hash(self):
        """
        Hashes the nick and returns a four-bit value. This method internally uses CRC16 x-25 implementation, which
        corresponds to Quassel's implementation (qChecksum() on Quassel 0.10.0, Qt 4.8.5) according to a quick
        empirical check (6 nicknames).

        See: http://crcmod.sourceforge.net/crcmod.predefined.html
        :return:
        """
        lower_nick = self.nickname.lower().rstrip('_')
        stripped_nick = lower_nick.rstrip('_')
        normalized_nick = stripped_nick if stripped_nick else lower_nick  # in case nickname is all underscores
        return calculateNicknameHash(normalized_nick.encode('latin-1')) & 0xF

    def get_nick_color(self):
        """
        Return the nick's colour based on hash. Corresponds to Quassel's own implementation.

        The colours will correspond in QuasselFlask's default colour scheme and in the Solarized Light/Dark themes for
        Quassel by antoligy <https://github.com/antoligy/SolarizedQuassel>.

        Otherwise, to make this work with other themes, you can customise the Color enum. Usually, Quassel supports 16
        colours. If you want the colours here to correspond to your Quassel colour scheme, specify all 16 colours you
        used in Quassel (or specify 8 colours - corresponds to repeating the list of 8 colours twice in Quassel's nick
        colour settings).

        For Quassel's hash implementation, see:
        https://github.com/quassel/quassel/blob/6509162911c0ceb3658f6a7ece1a1d82c97b577e/src/uisupport/uistyle.cpp#L874
        :return: Color object
        """
        return Color(self.get_nick_hash() % len(Color))


# ENDPOINTS

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

    if get_debug_queries():
        info = get_debug_queries()[0]
        app.logger.debug("SQL: {}\nParameters: {}\nDuration: {:.3f}s".format(
                info.statement, repr(info.parameters), info.duration))

    return render_template('results.html', records=[DisplayBacklog(result) for result in results],
                           search_channel=args.get('channel'), search_usermask=args.get('usermask'),
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
