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
from quasselflask.parsing.form import process_search_params
from quasselflask.parsing.irclog import DisplayBacklog
from quasselflask.querying import build_db_search_query
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

    form_args = request.args
    available_args = search_args & set(form_args.keys())

    # if no arguments passed, we can just redirect to the home
    if not available_args:
        return redirect(url_for('home'))

    # For rendering in templates - will be updated after processing search params (if successful) before render
    render_args = {
        'search_channel': form_args.get('channel'),
        'search_usermask': form_args.get('usermask'),
        'search_start': form_args.get('start'),
        'search_end': form_args.get('end'),
        'search_query': form_args.get('query'),
        'search_query_wildcard': form_args.get('search_query_wildcard', int),
        'search_limit': form_args.get('limit', app.config['RESULTS_NUM_DEFAULT'], int)  # post-processed value
    }

    # Process and parse the args
    try:
        sql_args = process_search_params(form_args)
    except ValueError as e:
        errtext = e.args[0]
        return render_template('search_form.html', error=errtext, **render_args)

    app.logger.debug("Args|SQL-processed: limit=%i channel%s usermask%s start[%s] end[%s] query%s %s",
                     sql_args['limit'], sql_args['channels'], sql_args['usermasks'],
                     sql_args['start'].isoformat() if sql_args['start'] else '',
                     sql_args['end'].isoformat() if sql_args['end'] else '',
                     sql_args['query'].get_parsed(), '[wildcard]' if sql_args['query_wildcard'] else '[no_wildcard]')

    # update after processing params
    render_args['search_query_wildcard'] = sql_args.get('query_wildcard')
    render_args['search_limit'] = sql_args.get('limit')

    # build and execute the query
    results = reversed(build_db_search_query(db.session, sql_args).all())

    if (app.debug or app.testing) and get_debug_queries():
        info = get_debug_queries()[0]
        app.logger.debug("SQL: {}\nParameters: {}\nDuration: {:.3f}s".format(
                info.statement, repr(info.parameters), info.duration))

    return render_template('results.html', records=[DisplayBacklog(result) for result in results], **render_args)


@app.route('/context/<int:post_id>/<int:num_context>')
def context(post_id, num_context):
    pass  # TODO context endpoint


if os.environ.get('QF_ALLOW_TEST_PAGES'):
    @app.route('/test/parse')
    def test_parse():
        pass  # TODO: test_parse endpoint


