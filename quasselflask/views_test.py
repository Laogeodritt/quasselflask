"""
Views used for testing or demoing the application.

Project: Quassekflask
"""

from flask import render_template

import quasselflask
from quasselflask import app, db
from quasselflask.parsing.query import BooleanQuery


@app.route('/test/query_parser')
def test_parse_home():
    return test_parse()


@app.route('/test/query_parser/<query_str>')
def test_parse(query_str=None):
    if query_str:
        query = BooleanQuery(query_str, app.logger).tokenize().parse()
        evaluated_query = query.eval(
            lambda a, b: ' ({} AND {}) '.format(b, a),
            lambda a, b: ' ({} OR {}) '.format(b, a),
            lambda s: '"{}"'.format(s)
        )
    else:
        query = BooleanQuery('', app.logger)
        evaluated_query = None

    return render_template('test/query_parse.html',
                           search_query=query_str,
                           evaluated=evaluated_query,
                           postfix=query.get_parsed())
