"""
Main QuasselFlask package.

Project: QuasselFlask
"""

from flask import Flask, request, g
from flask import render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import or_
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.sql.schema import MetaData
import sqlalchemy.orm.query  # for IDE inspection

from werkzeug.datastructures import MultiDict

from datetime import datetime
import re
import time
import os

from enum import Enum

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


# Bootstrap the application
app = Flask(__name__, instance_path=os.environ.get('QF_CONFIG_PATH', None), instance_relative_config=True)
app.config.from_object(DefaultConfig)
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
    return "[{:%Y-%m-%d %H:%M:%S}] <{}>[{:d}] {}".format(self.time, self.sender.sender, self.type, self.message)
Backlog.__repr__ = __repr_backlog


class BacklogType(Enum):
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
    sql_args = search_parse_args(request.args)

    # If no arguments passed, we can just redirect to the home
    if sql_args is None:
        return redirect(url_for('home'))

    query = db.session.query(Backlog).join(Buffer)  # type: sqlalchemy.orm.query.Query
    results = query.filter(Buffer.buffername == request.args['channel'])[0:2]

    print(results)
    return render_template('search_form.html')
#    return render_template('search_form.html', search_channel='abc', search_usermask='def tyy',
#        search_start='2016-09-15 11:22:33.000', search_end='2016-09-15 12:33:44.000',
#        search_limit=12, search_query='search1 search2', search_query_wildcard=True)


@app.route('/context/<int:post_id>/<int:num_context>')
def context(post_id, num_context):
    pass  # TODO context endpoint


def search_parse_args(args: MultiDict) -> MultiDict:
    """
    Parse args. Return MultiDict containing SQLAlchemy-ready arguments, or None on failure (or if no args).

    :raise ValueError: An argument is invalid. Exception argument is a list of tuples,
            [(arg_key, arg_value, error_text), ...]. Error text may be technical and not suitable for user messages.
    """
    # some helpful constants for the request

    # type of extraction/processing
    unique_args = {'start', 'end', 'limit', 'query_wildcard'}
    flat_args = {'channel', 'usermask'}  # args that are space-separated lists; if an arg is repeated, flatten list
    query_args = {'query'}  # requires query parsing
    search_args = unique_args | flat_args | query_args

    available_args = search_args & set(args.keys())
    parsed_args = MultiDict()

    # if no params set
    if len(available_args) == 0:
        return None

    # Extract and preprocess args for the SQL queries
    # Unique arguments
    if 'start' in available_args:
        try:
            parsed_args.add('start', convert_str_to_datetime(args.get('start')))
        except ValueError:
            pass  # TODO: handle error

    if 'end' in available_args:
        try:
            parsed_args.add('end', convert_str_to_datetime(args.get('end')))
        except ValueError:
            pass  # TODO: handle error

    parsed_args.add('query_wildcard', args.get('query_wildcard', None, int) == 1)

    parsed_args.add('limit', args.get('limit', app.config['MAX_RESULTS_DEFAULT'], int))  # TODO: copy to rendered form

    # Flat-list arguments
    parsed_args.add('channel', _extract_glob_list(args.get('channel')))
    parsed_args.add('usermask', _extract_glob_list(args.get('usermask')))

    # TODO: parse the query

    return parsed_args


def _extract_glob_list(s, sep=' ') -> [str]:
    """
    Extracts an argument of `sep`-separated items, splits it into a list, and converts GLOB-style syntax to SQL LIKE-
    style syntax, ready for use in SQLAlchemy.

    :param s: Argument string to split.
    :param sep: The separator character.
    :return: List of extracted strings. If the `key` is not present in `args`, or its value is empty, returns an
            empty list.
    """
    return [convert_glob_to_like(s)[0] for s in s.split(sep) if s != '' and not s.isspace()]


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


def convert_glob_to_like(s: str) -> (str, bool):
    """
    Converts a glob-style wildcard string to SQL LIKE syntax. Only handles conversion of * and ? to % and _, plus
    escaped characters via '\' (no character classes).
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
        s_parse.append('\\')
    return ''.join(s_parse), has_wildcards


if __name__ == '__main__':
    app.run()
