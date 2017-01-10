"""
Main flask endpoints for this application.

Project: QuasselFlask
"""

import time
from sqlalchemy.orm import joinedload

from flask import flash
from flask import request, g, render_template, url_for, redirect
from flask_sqlalchemy import get_debug_queries
from flask_user import login_required, current_user
from werkzeug.exceptions import BadRequest

import quasselflask
from quasselflask import app, db, userman
from quasselflask.email_adapter import send_confirm_email_email
from quasselflask.models.query import *
from quasselflask.parsing.form import process_search_params, SearchType
from quasselflask.parsing.irclog import DisplayBacklog, DisplayUserSummary
from quasselflask.util import safe_redirect, get_next_url, log_access, log_action, log_action_error, repr_user_input

logger = app.logger  # type: logging.Logger


@app.context_processor
def inject_themes():
    themeid = current_user.themeid
    default_themeid = app.config.get('QF_DEFAULT_THEME', 0)
    themes_dict = app.config.get('QF_THEMES', {})
    theme = themes_dict.get(themeid, default_themeid)
    return dict(user_theme=theme, themes=themes_dict)


@app.context_processor
def inject_search():
    """
    Inject search variables/constants universal to search form-based templates.
    :return:
    """
    return dict(SearchType=SearchType)


@app.before_first_request
def flask_user_redirect_patch():
    """
    HACK: Replace werkzeug redirect() with a safe version globally at runtime

    This is a workaround for Flask-User <0.6.8, which upon login, logout, etc. will redirect according to the 'next'
    GET parameter without validating it and thus presents an open redirect security risk. As a solution, we will
    globally replace the redirect() function in werkzeug with a safety-checked one.

    The original method is available as werkzeug.util.unsafe_redirect.
    """
    import flask_user.views
    flask_user.views.unsafe_redirect = flask_user.views.redirect
    flask_user.views.redirect = flask_user.views.safe_redirect = safe_redirect


@app.before_first_request
def qf_setup_themes():
    """ Reads the theme config (default and custom) and generates the structures used by the template. """
    from quasselflask.views.themes import Theme

    themes_dict = {}
    for id_, name, file, cls in app.config.get('QF_DEFAULT_THEMES', []):
        theme = Theme(id_, name, file=file, root_class=cls)
        themes_dict[theme.id] = theme
    for id_, name, file, cls in app.config.get('QF_CUSTOM_THEMES', []):
        theme = Theme(id_, name, file=file, root_class=cls, custom=True)
        themes_dict[theme.id] = theme
    app.config['QF_THEMES'] = themes_dict


@app.before_request
def globals_init():
    g.start_time = time.time()
    g.get_request_time = lambda: "{:.3f}s".format(time.time() - g.start_time)
    g.display_version = quasselflask.__version__


@app.route('/')
@login_required
def home():
    return render_template('search_form.html')


@app.route('/search/logs')
@login_required
def search():
    # process the args passed in from the query string in the request
    # this also documents the POST form parameters - check this method's source along with the readme
    try:
        sql_args, render_args = _process_search_form_params()
        sql_args['limit'] += 1  # so we know if there are more results
    except BadRequest:
        return redirect(url_for('home'))

    # build and execute the query
    results_cursor = build_query_backlog(db.session, sql_args,
                                         query_options=(joinedload(Backlog.sender),
                                                        joinedload(Backlog.buffer).joinedload(Buffer.network))).all()

    # reversed() if we're doing newest-first because we still want chronological order
    if sql_args['order'] == 'newest':
        results_raw = list(reversed(results_cursor))
    else:
        results_raw = list(results_cursor)

    # check if we have more results available than the passed limit (note that we queried for limit+1 results)
    render_args['more_results'] = False
    if len(results_raw) == sql_args['limit']:  # this limit was already incremented
        results_raw = results_raw[0:-1]  # only show up to the user-entered limit
        render_args['more_results'] = True  # for template

    # set up display
    results_display = [DisplayBacklog(result) for result in results_raw]
    render_args['search_results_total'] = len(results_display)

    if (app.debug or app.testing) and get_debug_queries():
        for info in get_debug_queries():
            app.logger.debug("SQL: {}\nParameters: {}\nDuration: {:.3f}s\n\n".format(
                info.statement, repr(info.parameters), info.duration))

    # get unique channels and users by ID
    # efficiency note for big result sets: set() type uses hashing for fast "x in s" operations, and
    # set.add() won't add redundant entries - so this yields sets of unique channels/users.
    result_users = set()
    result_channels = set()
    for result in results_raw:
        result_users.add(result.senderid)
        result_channels.add(result.bufferid)

    # determine some display settings based on the type of query made
    has_single_channel = (len(result_channels) == 1)
    is_user_search = bool(sql_args.get('usermasks'))
    is_keyword_search = bool(sql_args.get('query'))
    render_args['expand_line_details'] = not has_single_channel or is_user_search or is_keyword_search

    return render_template('results.html', records=results_display, **render_args)


@app.route('/search/users')
@login_required
def search_users():
    # process the args passed in from the query string in the request
    # this also documents the POST form parameters - check this method's source along with the readme
    try:
        sql_args, render_args = _process_search_form_params()
        # not doing the +1 trick to check if more results, because of the grouping+summing that happens here
    except BadRequest:
        return redirect(url_for('home'))

    # build and execute the query
    results_cursor = build_query_usermask(db.session, sql_args).all()

    if (app.debug or app.testing) and get_debug_queries():
        info = get_debug_queries()[0]
        app.logger.debug("SQL: {}\nParameters: {}\nDuration: {:.3f}s".format(
            info.statement, repr(info.parameters), info.duration))

    results_raw = list(results_cursor)
    results_display = [DisplayUserSummary(sender, count) for sender, count in results_raw]
    render_args['search_results_total'] = sum(record.count for record in results_display)

    return render_template('results_users.html', records=results_display, **render_args)


def _process_search_form_params() -> (dict, dict):
    """
    Process the params in request.args. This method is a wrapper method that a) outputs useful debugging messages; and
    b) returns both the processed SQL parameters, and the sanitized "display" parameters that can be passed to the
    template to prepopulate the form.
    :return: Two dicts: first is sql args, second is render (template) args after sanitisation. See ``search()`` for
        example usage of this function.
    :raise BadRequest: set of search parameters is invalid
    """
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
        raise BadRequest("Invalid search: no search parameters")

    # For rendering in templates - will be updated after processing search params (if successful) before render
    render_args = {
        'search_channel': form_args.get('channel'),
        'search_usermask': form_args.get('usermask'),
        'search_start': form_args.get('start'),
        'search_end': form_args.get('end'),
        'search_query': form_args.get('query'),
        'search_query_wildcard': form_args.get('search_query_wildcard', int),
        'search_limit': form_args.get('limit', app.config['RESULTS_NUM_DEFAULT'], int),
        'search_order': form_args.get('order'),
        'search_type': form_args.get('type'),
        'expand_line_details': False,
    }

    # Process and parse the args
    try:
        sql_args = process_search_params(form_args)
        sql_args['permissions'] = query_permitted_buffers(db.session, current_user)
    except ValueError as e:
        errtext = e.args[0]
        return render_template('search_form.html', error=errtext, **render_args)

    app.logger.debug("Args|SQL: limit=%i order=%s channel%s usermask%s start[%s] end[%s] query%s %s",
                     sql_args['limit'], sql_args['order'], sql_args['channels'], sql_args['usermasks'],
                     sql_args['start'].isoformat() if sql_args['start'] else '',
                     sql_args['end'].isoformat() if sql_args['end'] else '',
                     sql_args['query'].get_parsed(), '[wildcard]' if sql_args['query_wildcard'] else '[no_wildcard]')

    app.logger.debug("Permissions: {}".format(', '.join(str(pbuf.bufferid) for pbuf in sql_args['permissions'])))

    # update after processing params
    render_args['search_query_wildcard'] = sql_args.get('query_wildcard')
    render_args['search_limit'] = sql_args.get('limit')
    render_args['search_order'] = sql_args.get('order')
    render_args['search_type'] = sql_args.get('type')
    return sql_args, render_args


@app.route('/user/permissions', methods=['GET'])
@login_required
def check_permissions():
    """
    Shows a list of permitted buffers.
    :return:
    """
    permitted_buffers = query_permitted_buffers(db.session, current_user)
    return render_template("check_permissions.html", user=current_user, buffers=permitted_buffers)

# TODO: 'next' parameter hack - add version check on Flask-User version


@app.route('/user/update', methods=['POST'])
@login_required
def user_update():
    """
    Update current user's information. Any fields not included will remain unchanged.

    Some actions return a confirmation page. It is necessary to submit the confirmation form to complete the action.

    If acting on the current user, only the email address may be updated.  This prevents the current user from locking
    themselves out of the application or removing a sole superuser.

    POST command parameter (exactly one required):

    * `email`: new email address. This will require the user to reconfirm their email address before their account is
        re-enabled.
    * `themeid`: new theme ID (int).

    Other POST parameters, common to all requests:

    * `next`: URL, the URL to return to after the update.

    :return:
    """

    logger.info(log_access())

    commands = frozenset(('email', 'themeid'))
    request_commands = set(request.form.keys()) & commands

    # validate
    request_valid = len(request_commands) == 1

    if not request_valid:
        raise BadRequest("No command or multiple commands to user update API endpoint")

    # Valid - let's process it
    user = current_user  # laziness and because this mirrors the admin_update_user endpoint

    if 'email' in request_commands:
        try:
            user.email = request.form.get('email')
            if userman.enable_confirm_email:
                user.confirmed_at = None

            # confirmation email
            send_confirm_email_email(user)

            db.session.commit()
            flash('Updated email to {email} (must re-confirm to reactivate account)'.format(email=user.email), 'notice')
            logger.info(log_action('update user', ('set', 'email'), ('email', user.email)))
            return safe_redirect(get_next_url('POST'))
        except Exception as e:
            logger.error(log_action_error('error while updating user profile', repr(e.args),
                                          ('id', user.qfuserid), ('name', user.username),
                                          ('email', user.email), ('superuser', repr(user.superuser))), exc_info=True)
            db.session.rollback()
            if app.debug:
                raise  # let us debug this
            else:
                flash('Error occurred while updating user. Please try again later, or contact the server administrator '
                      'with the date/time of this error and your IP address in order to trace error information in the'
                      'logs.')
                return safe_redirect(get_next_url('POST'))

    elif 'themeid' in request_commands:
        try:
            newid = int(request.form.get('themeid'))
        except ValueError:
            newid = None

        logger.debug(repr(app.config['QF_THEMES']))
        logger.debug(repr(newid))
        if newid in app.config['QF_THEMES']:
            user.themeid = newid
            db.session.commit()
            return safe_redirect(get_next_url('POST'))
        else:
            raise BadRequest("Invalid theme ID.")

    flash("Something happened. You shouldn't have gotten this far.", "error")
    logger.error(log_action_error('user update', 'should have returned earlier in code - bug?'))
    logger.debug('request.form=' + repr_user_input(request.form))
    return safe_redirect(get_next_url('POST'))


@app.route('/context/<int:post_id>/<int:num_context>')
def context(post_id, num_context):
    pass  # TODO context endpoint
