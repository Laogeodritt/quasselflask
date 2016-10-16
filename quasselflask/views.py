"""
Flask endpoints for this application.

Project: QuasselFlask
"""

import os
import time

from flask import request, g, render_template, redirect, url_for, flash
from flask_sqlalchemy import get_debug_queries
from flask_user import login_required, roles_required

import quasselflask
from quasselflask import app, db, userman
from quasselflask.parsing.form import process_search_params
from quasselflask.parsing.irclog import DisplayBacklog
from quasselflask.querying import build_db_search_query
from quasselflask.util import random_string


@app.before_request
def globals_init():
    g.start_time = time.time()
    g.get_request_time = lambda: "{:.3f}s".format(time.time() - g.start_time)
    g.display_version = quasselflask.__version__


@app.route('/')
@login_required
def home():
    return render_template('search_form.html')


@app.route('/search')
@login_required
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
        'search_limit': form_args.get('limit', app.config['RESULTS_NUM_DEFAULT'], int),
        'search_order': form_args.get('order')
    }

    # Process and parse the args
    try:
        sql_args = process_search_params(form_args)
    except ValueError as e:
        errtext = e.args[0]
        return render_template('search_form.html', error=errtext, **render_args)

    app.logger.debug("Args|SQL-processed: limit=%i order=%s channel%s usermask%s start[%s] end[%s] query%s %s",
                     sql_args['limit'], sql_args['order'], sql_args['channels'], sql_args['usermasks'],
                     sql_args['start'].isoformat() if sql_args['start'] else '',
                     sql_args['end'].isoformat() if sql_args['end'] else '',
                     sql_args['query'].get_parsed(), '[wildcard]' if sql_args['query_wildcard'] else '[no_wildcard]')

    # update after processing params
    render_args['search_query_wildcard'] = sql_args.get('query_wildcard')
    render_args['search_limit'] = sql_args.get('limit')
    render_args['search_order'] = sql_args.get('order')

    # build and execute the query
    results = build_db_search_query(db.session, sql_args).all()

    if sql_args['order'] == 'newest':
        results = reversed(results)

    if (app.debug or app.testing) and get_debug_queries():
        info = get_debug_queries()[0]
        app.logger.debug("SQL: {}\nParameters: {}\nDuration: {:.3f}s".format(
                info.statement, repr(info.parameters), info.duration))

    return render_template('results.html', records=[DisplayBacklog(result) for result in results], **render_args)

# TODO: look at flask_users/views.py login() endpoint - security issue with 'next' GET parameter?
# TODO: create user permissions page
# TODO: user permissions "copy from" functionality
# TODO: remember me token - don't use user id
# TODO: reset password form
# TODO: forgot password form


@app.route('/context/<int:post_id>/<int:num_context>')
@login_required
def context(post_id, num_context):
    pass  # TODO context endpoint


@app.route('/admin/create-user', methods=['GET', 'POST'])
@roles_required('superuser')
def admin_create_user():
    """
    Display registration form and create new User.

    Modified from Flask-User 0.6.8 - BSD Licence.
    """

    from flask_user import emails
    from quasselflask.forms import CreateUserForm

    db_adapter = userman.db_adapter

    # Initialize form
    create_form = CreateUserForm(request.form)

    # Process valid POST
    if request.method == 'POST' and create_form.validate():
        # Create a User object using Form fields that have a corresponding User field
        User = db_adapter.UserClass
        user_class_fields = User.__dict__
        user_fields = {}

        # Enable user account
        if hasattr(db_adapter.UserClass, 'active'):
            user_fields['active'] = True
        elif hasattr(db_adapter.UserClass, 'is_enabled'):
            user_fields['is_enabled'] = True
        else:
            user_fields['is_active'] = True

        # For all form fields
        for field_name, field_value in create_form.data.items():
            # Store corresponding Form fields into the User object
            if field_name in user_class_fields:
                user_fields[field_name] = field_value

        # set an unusable password (too long) to "disable" the account until password reset
        # (avoid using blank in case 'plaintext' password storage is configured... not that anyone should be!)
        pass_length = app.config['QF_PASSWORD_MAX'] + 1
        if pass_length <= 0:
            pass_length = 128
        user_fields['password'] = userman.hash_password(random_string(pass_length))

        # Add User record using named arguments 'user_fields'
        user = db_adapter.add_object(User, **user_fields)
        db_adapter.commit()  # needed to generate ID for email token
        try:
            # Send 'registered' email and delete new User object if send fails
            if userman.enable_email and (userman.send_registered_email or userman.enable_confirm_email):
                # Generate confirm email link
                object_id = int(user.get_id())
                token = userman.generate_token(object_id)
                # confirm_email_link = url_for('user.confirm_email', token=token, _external=True)
                reset_password_link = url_for('user.reset_password', token=token, _external=True)

                # send password reset email (when reset, marks email as confirmed: see flask_user/views.py:578 v0.6.8)
                # emails.send_registered_email(user, None, confirm_email_link)
                emails.send_forgot_password_email(user, None, reset_password_link)
                db_adapter.update_object(user, reset_password_token=token)
                db_adapter.commit()

            # Prepare one-time system message
            if userman.enable_confirm_email:
                flash('User {user} created. A confirmation/password reset email has been sent to {email}.'
                      .format(user=user.username, email=user.email), 'success')
            else:
                flash('User {user} created.'.format(user=user.username), 'success')

        except Exception:
            db_adapter.delete_object(user)
            db_adapter.commit()
            raise

        return redirect(url_for('admin_manage_user', username=user.username))

    # Process GET or invalid POST
    return render_template('admin/create_user.html', form=create_form, register_form=create_form)


@app.route('/admin/users/<username>', methods=['GET', 'POST'])
@roles_required('superuser')
def admin_manage_user(username):
    return render_template('admin/manage_user.html')  # TODO


@app.route('/admin/users', methods=['GET', 'POST'])
@roles_required('superuser')
def admin_users():
    return render_template('admin/user_list.html')  # TODO


if os.environ.get('QF_ALLOW_TEST_PAGES'):
    @app.route('/test/parse')
    def test_parse():
        pass  # TODO: test_parse endpoint


