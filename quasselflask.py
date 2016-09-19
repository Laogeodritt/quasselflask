from flask import Flask, render_template, request, g
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import or_
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.sql.schema import MetaData
import sqlalchemy.orm.query, sqlalchemy.orm.session  # for IDE inspection

from datetime import datetime
import re
import time
import os

from werkzeug.datastructures import MultiDict

__version__ = "0.1"


class DefaultConfig:
    # SQLALCHEMY_DATABASE_URI
    SITE_NAME = 'SiteName'
    MAX_RESULTS_DEFAULT = 100  # Default maximum results set in the search form
    MAX_RESULTS = 1000  # Maximum number of results per query, regardless of search form settings.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

search_default_args = {
    'limit': 100
}

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


@app.before_request
def globals_init():
    g.start_time = time.time()
    g.get_request_time = lambda: "{:.3f}s".format(time.time() - g.start_time)
    g.display_version = __version__


@app.route('/')
def home():
    return render_template('search_form.html', **search_default_args)
#    return render_template('search_form.html', channel='abc', usermask='def tyy',
#        search_time_start='2016-09-15 11:22:33.000', search_time_end='2016-09-15 12:33:44.000',
#        maxlines=12, queries=[(0, 'blah', False), (1, 'bloop*', True), (2, 'cadenza', False)])


@app.route('/search')
def search():
    # some helpful constants for the request

    # type of extraction/processing
    unique_args = {'start', 'end', 'limit'}
    flat_args = {'channel', 'usermask'}  # args that are space-separated lists; if an arg is repeated, flatten list
    nest_args = {'query', 'wildcardquery'}  # args of space-separated lists; if an arg is repeated, preserve nested list
    query_args = unique_args | flat_args | nest_args

    # types of queries
    plain_args = {'query'}
    glob_args = {'channel', 'usermask', 'wildcardquery'}

    passed_args = query_args & request.args.keys()
    sql_args = MultiDict()

    # if no params set, we can just show the main page
    if len(passed_args) == 0:
        return render_template('search_form.html')

    # TODO Extract and preprocess args for the SQL queries

    query = db.session.query(Backlog).join(Buffer)  # type: sqlalchemy.orm.query.Query
    results = query.filter(Buffer.buffername == request.args['channel'])[0:2]

    print(results)
    return render_template('search_form.html')


@app.route('/context/<int:post_id>/<int:num_context>')
def context(post_id, num_context):
    pass


def _extract_arg_flat_list(args, key, sep=' ') -> [str]:
    """
    Extracts an argument of `sep`-separated items and splits it into a list.

    If more than one argument is present in `args` with the key `key`, then all of them are split on `sep`, and the
    resulting elements are returned in a single list.

    :param args: A MultiDict of arguments, usually `request.args`
    :param key: The key in `args` to extract.
    :param sep: The separator character.
    :return: List of extracted strings. If the `key` is not present in `args`, or its value(s) is(are) empty, returns an
            empty list.
    """
    extracted = []
    for str_list in args.getlist(key):  # type: str
        extracted.extend([s for s in str_list.split(sep) if s != '' and not s.isspace()])
    return extracted


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
    if is_escaped:
        s_parse.append('\\')
    return ''.join(s_parse), has_wildcards


if __name__ == '__main__':
    app.run()
