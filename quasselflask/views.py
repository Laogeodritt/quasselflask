"""
Flask endpoints for this application.

Project: QuasselFlask
"""

import os
import time

from flask import request, g, render_template, redirect, url_for
from flask_sqlalchemy import get_debug_queries

import quasselflask
from quasselflask import app, db
from quasselflask.parsing.irclog import DisplayBacklog
from quasselflask.querying import build_db_query
from quasselflask.util import repr_user_input


@app.before_request
def globals_init():
    g.start_time = time.time()
    g.get_request_time = lambda: "{:.3f}s".format(time.time() - g.start_time)
    g.display_version = quasselflask.__version__


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
        results = reversed(build_db_query(db.session, request.args).all())
    except ValueError as e:
        errtext = e.args[0]
        return render_template('search_form.html', error=errtext,
            search_channel=args.get('channel'), search_usermask=args.get('usermask'),
            search_start=args.get('start'), search_end=args.get('end'),
            search_query=args.get('query'), search_query_wildcard=args.get('query_wildcard', type=bool),
            search_limit=args.get('limit', app.config['RESULTS_NUM_DEFAULT'], int))

    if get_debug_queries():
        info = get_debug_queries()[0]
        app.logger.debug("SQL: {}\nParameters: {}\nDuration: {:.3f}s".format(
                info.statement, repr(info.parameters), info.duration))

    return render_template('results.html', records=[DisplayBacklog(result) for result in results],
                           search_channel=args.get('channel'), search_usermask=args.get('usermask'),
                           search_start=args.get('start'), search_end=args.get('end'),
                           search_query=args.get('query'), search_query_wildcard=args.get('query_wildcard', type=bool),
                           search_limit=args.get('limit', app.config['RESULTS_NUM_DEFAULT'], int))


@app.route('/context/<int:post_id>/<int:num_context>')
def context(post_id, num_context):
    pass  # TODO context endpoint


if os.environ.get('QF_ALLOW_TEST_PAGES'):
    @app.route('/test/parse')
    def test_parse():
        pass  # TODO: test_parse endpoint


