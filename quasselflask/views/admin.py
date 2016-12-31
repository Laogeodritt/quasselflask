"""
Flask endpoints for admin area.

Project: Quasselflask
"""

import json
import logging
from datetime import datetime

from flask import request, url_for, flash, redirect, render_template
from flask_login import current_user
from flask_user import roles_required
from itsdangerous import BadSignature
from werkzeug.exceptions import BadRequest

from quasselflask import app, userman, db, forms
from quasselflask.email_adapter import send_new_user_set_password_email
from quasselflask.models.query import *
from quasselflask.models.types import *
from quasselflask.parsing.convert_json import convert_permissions_lists, convert_user_permissions
from quasselflask.util import random_string, safe_redirect, get_next_url, repr_user_input, log_access, log_action, \
    log_action_error


@app.before_first_request
def setup_signer():
    forms.make_signer()


logger = app.logger  # type: logging.Logger


def _get_qfuser_log(user):
    return '[QFUSER={user.qfuserid:d} {user.username}]'.format(user=user)


def make_reset_password():
    """
    Make an unusable password (too long) to "disable" an account until password reset
    # (avoid using blank in case 'plaintext' password storage is configured... not that anyone should be!)
    :return: an impossible password
    """
    pass_length = app.config['QF_PASSWORD_MAX'] + 1
    if pass_length <= 0:
        pass_length = 128
    return random_string(pass_length)


@app.route('/admin/create-user', methods=['GET', 'POST'])
@roles_required('superuser')
def admin_create_user():
    """
    Display registration form and create new User.

    Modified from Flask-User 0.6.8 - BSD Licence.
    """

    from quasselflask.forms import CreateUserForm

    logger.info(log_access())

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

        user_fields['password'] = userman.hash_password(make_reset_password())

        # User preference defaults
        user_fields['themeid'] = app.config.get('QF_DEFAULT_THEME', 0)

        # Add User record using named arguments 'user_fields'
        user = db_adapter.add_object(User, **user_fields)
        db_adapter.commit()  # needed to generate ID for email token
        try:
            # email
            send_new_user_set_password_email(user)

            # Prepare one-time system message
            if userman.enable_confirm_email:
                flash('User {user} created. A confirmation/password reset email has been sent to {email}.'
                      .format(user=user.username, email=user.email), 'success')
            else:
                flash('User {user} created.'.format(user=user.username), 'success')

        except Exception as e:
            logger.error(log_action_error('error while creating user', repr(e.args),
                                          ('id', user.qfuserid), ('name', user.username),
                                          ('email', user.email), ('superuser', repr(user.superuser))), exc_info=True)
            db_adapter.delete_object(user)
            db_adapter.commit()
            if app.debug:
                raise  # let us debug this
            else:
                flash('Error occurred while creating user. Please try again later, or contact the server administrator '
                      'with the date/time of this error and your IP address in order to trace error information in the'
                      'logs.', 'error')
                return redirect(url_for('admin_manage_user', userid=user.qfuserid))

        logger.info(log_action('create user', ('id', user.qfuserid), ('name', user.username),
                               ('email', user.email), ('superuser', repr(user.superuser))))
        return redirect(url_for('admin_manage_user', userid=user.qfuserid))

    # Process GET or invalid POST
    return render_template('admin/create_user.html', form=create_form, register_form=create_form)


@app.route('/admin/users', methods=['GET'])
@roles_required('superuser')
def admin_users():
    logger.info(log_access())
    users = query_all_qf_users(db.session)
    return render_template('admin/user_list.html', users=users)


@app.route('/admin/users/<int:userid>', methods=['GET', 'POST'])
@roles_required('superuser')
def admin_manage_user(userid):
    """
    Returns page to manage a specified user's profile and permissions.

    Includes data on all permissions (quasseluser, network, buffer/channel) that can be set. Structure:

    .. code-block:: json
        {
            "quasselusers": [
                {
                    "id": 0,
                    "name": "user0"
                },
                {
                    "id": 1,
                    "name": "user1"
                }
            ],
            "networks": [
                {
                    "id": 0,
                    "quasseluserid": 0,
                    "name": "Snoonet"
                },
                {
                    "id": 1,
                    "quasseluserid": 1,
                    "name": "Freenode"
                }
            ],
            "channels": [
                {
                    "id": 0,
                    "networkid": 0,
                    "name": "#techsupport"
                },
                {
                    "id": 4,
                    "networkid": 1,
                    "name": "#debian"
                }
            ]
        }

    A Javascript variable USER_PERMISSIONS is included on the returned page, to be processed by Javascript, containing
    the following structure:

    .. code-block:: json
        {
            "permissions": [
                {
                    "qfpermid": 343,
                    "access": "allow|deny",
                    "type": "user|network|buffer",
                    "id": 7,
                },
                { ... }
            ],
            "default": "allow|deny"
        }

    :param userid: User to manage
    :return:
"""

    logger.info(log_access())

    # get current user to manage
    user = query_qfuser(db.session, userid)

    # get all possible permissions - for setting permissions
    db_quasselusers = query_quasselusers(db.session)
    db_networks = query_networks(db.session)
    db_buffers = query_buffers(db.session, [BufferType.channel_buffer, BufferType.query_buffer])
    permission_data = convert_permissions_lists(db_quasselusers, db_networks, db_buffers)
    user_permissions = convert_user_permissions(user)

    return render_template('admin/manage_user.html',
                           user=user,
                           permission_data=permission_data,
                           user_permissions=user_permissions)


@app.route('/admin/users/<int:userid>/update', methods=['POST'])
@roles_required('superuser')
def admin_update_user(userid):
    """
    Update a user's information. Any fields not included will remain unchanged.

    Some actions return a confirmation page. It is necessary to submit the confirmation form to complete the action.

    If acting on the current user, only the email address may be updated.  This prevents the current user from locking
    themselves out of the application or removing a sole superuser.

    POST command parameter (exactly one required, except email and confirm_email may appear together):

    * `status`: 1 (enabled) or 0 (disabled). Other values treated as 0.
    * `superuser`: 1 (superuser) or 0 (normal user). Other values treated as 0. Returns a confirmation page.
    * `confirm_token`: Confirmation token. Only applies to superuser/delete requests.
    * `email`: new email address. Can only be combined with the `confirm_email` parameter.
    * `confirm_email`: 1 (confirm) or 0 (unconfirm). Force the email confirmation status. Other values are treated as 0.
            Can only be combined with the `email` parameter.

    Other POST parameters, common to all requests:

    * `next`: URL, the URL to return to after the update.

    :param userid: The user ID to modify.
    :return:
    """

    logger.info(log_access())

    commands = frozenset(('status', 'superuser', 'email', 'confirm_email', 'confirm_token'))
    request_commands = set(request.form.keys()) & commands

    # validate
    request_valid = len(request_commands) == 1 or \
        (len(request_commands) == 2 and 'email' in request_commands and 'confirm_email' in request_commands)
    user_valid = (userid != current_user.qfuserid or
                  ('email' in request_commands and request.form.get('confirm_email', '0') == '1'))

    if not request_valid:
        raise BadRequest("No command or multiple commands to user update API endpoint")

    if not user_valid:
        flash("Oops! You can't make changes that would disable yourself.", "error")
        return safe_redirect(get_next_url('POST'))

    # Valid - let's process it
    user = query_qfuser(db.session, userid)

    if 'status' in request.form:
        return admin_update_user_status(user)
    elif 'superuser' in request.form:  # non-confirmed
        return admin_update_user_superuser_confirm(user)
    elif 'confirm_token' in request.form:  # confirm superuser/delete
        return admin_update_user_superuser(user)
    elif 'email' in request.form or 'confirm_email' in request.form:
        return admin_update_user_email(user)

    flash("Something happened. You shouldn't have gotten this far.", "error")
    logger.error(log_action_error('update user', 'should have returned earlier in code - bug?',
                                  ('user', _get_qfuser_log(user))))
    logger.debug('request.form=' + repr_user_input(request.form))
    return safe_redirect(get_next_url('POST'))


def admin_update_user_status(user: QfUser):
    status_arg = request.form.get('status', '0')
    status_val = bool(status_arg == '1')
    user.active = status_val
    db.session.commit()
    flash(('Enabled' if status_val else 'Disabled') + ' user {}'.format(user.username), 'notice')
    logger.info(log_action('update user', ('user', _get_qfuser_log(user)),
                           ('set', 'status'), ('to', repr(user.active))))
    return safe_redirect(get_next_url('POST'))


def admin_update_user_superuser_confirm(user: QfUser):
    from quasselflask import forms
    update_key = 'superuser'
    update_value = '1' if request.form.get('superuser', '0') == '1' else '0'
    confirm_key = forms.generate_confirm_key(
        {
            'target_user': user.qfuserid,
            'current_user': current_user.qfuserid,
            'update': update_key,
            'value': update_value
        },
        'admin_update_user')
    return render_template('admin/update_user_confirm.html',
                           target=url_for('admin_update_user', userid=user.qfuserid),
                           user=user, action='set superuser' if update_value == '1' else 'set as normal user',
                           next_url=get_next_url('POST'), confirm_key=confirm_key)


def admin_update_user_superuser(user):
    try:
        data = forms.check_confirm_key(request.form.get('confirm_token'), 'admin_update_user')
    except BadSignature:
        logger.error(log_action_error('update user', 'invalid confirmation key', ('user', _get_qfuser_log(user))))
        logger.debug('request.form=' + repr_user_input(request.form))
        raise BadRequest('Invalid confirmation key.')

    valid_request = user.qfuserid == data['target_user'] and \
        current_user.qfuserid == data['current_user'] and \
        'superuser' == data['update']
    if not valid_request:
        logger.error(log_action_error('update user', 'invalid confirmation data', ('user', _get_qfuser_log(user))))
        logger.debug('confirmation data=' + repr_user_input(data))
        logger.debug('request.form=' + repr_user_input(request.form))
        raise BadRequest('Invalid confirmation key.')

    user.superuser = bool(data.get('value', '0') == '1')
    flash('Set user {} as {}'.format(user.username, 'superuser' if user.superuser else 'normal user'), 'notice')
    db.session.commit()
    logger.info(log_action('update user', ('user', _get_qfuser_log(user)),
                           ('set', 'superuser'), ('to', repr(user.superuser))))
    return safe_redirect(get_next_url('POST'))


def admin_update_user_email(user):
    if 'email' in request.form:
        user.email = request.form.get('email')
    if request.form.get('confirm_email', '0') == '1':
        user.confirmed_at = datetime.now()
    else:
        user.confirmed_at = None
    db.session.commit()
    flash('User {user} updated with email {email} ({confirm})'
          .format(user=user.username,
                  email=user.email,
                  confirm='must confirm' if user.confirmed_at is None else 'confirmed'),
          'notice')
    logger.info(log_action('update user', ('user', _get_qfuser_log(user)),
                           ('set', 'email'), ('email', user.email),
                           ('confirmed', 'True' if user.confirmed_at else 'False')))
    return safe_redirect(get_next_url('POST'))


@app.route('/admin/users/<int:userid>/permissions', methods=['POST'])
@roles_required('superuser')
def admin_permissions(userid):
    """
    On POST request, update a user's permissions. Redirects to the user management page.

    POST parameters:

    * `permissions`: new permissions to set. Data in the following structure:

        .. code-block:: json
            {
                "permissions": [
                    {
                        "access": "allow|deny",
                        "type": "user|network|buffer",
                        "id": 0
                    },
                    { ... }
                ],
                "default": "allow|deny"
            }

        ``id`` represents the quasseluser, network or buffer ID, depending on the set `type` value.


    :param userid: The user ID to modify.
    :return:
    """

    logger.info(log_access())
    user = query_qfuser(db.session, userid)
    try:
        perm_data = json.loads(request.form.get('permissions'))
    except json.JSONDecodeError:
        logger.error(log_action_error('update permissions', 'invalid JSON', ('user', _get_qfuser_log(user))))
        logger.debug('request.form=' + repr_user_input(request.form))
        raise BadRequest('Invalid permissions data.')

    try:
        logger.debug(log_action('old permissions', ('user', _get_qfuser_log(user)),
                                ('default', user.access), ('permissions', user.permissions)))
        user.access = PermissionAccess.from_name(perm_data['default'])

        # If any permissions for this user, delete them first
        if user.permissions:
            del user.permissions[:]

        # Add the new permissions. Validations:
        # access, type: from_name validates against enum python-side; db columns are enums
        # ID: foreign key constraint, database will complain if non-existent for the given type
        # All: If not present in in_perm (malformed permission object), KeyError raised
        # TODO: figure out what kind of SQLAlchemy exceptions can be thrown here to throw in with Invalid permissions
        for in_perm in perm_data['permissions']:
            user.permissions.append(QfPermission(
                PermissionAccess.from_name(in_perm['access']),
                PermissionType.from_name(in_perm['type']),
                in_perm['id']
            ))

        db.session.commit()

        logger.info(log_action('update permissions', ('user', _get_qfuser_log(user)),
                               ('default', user.access), ('permissions', user.permissions)))

    except (KeyError, TypeError, ValueError, sqlalchemy.exc.NoReferencedColumnError):
        logger.error(log_action_error('update permissions', 'invalid perm data', ('user', _get_qfuser_log(user))))
        logger.debug('perm_data=' + repr_user_input(perm_data), exc_info=True, stack_info=True)
        db.session.rollback()
        raise BadRequest('Invalid permissions data.')
    # other SQLAlchemy errors are not caught: legitimate server error (HTTP 500), let Flask handle it

    return safe_redirect(get_next_url('POST'))


@app.route('/admin/users/<int:userid>/check_permissions', methods=['GET'])
@roles_required('superuser')
def admin_check_permissions(userid):
    """
    Shows a list of permitted buffers.
    :param userid: User ID to check.
    :return:
    """
    user = query_qfuser(db.session, userid)
    permitted_buffers = query_permitted_buffers(db.session, user)
    return render_template("check_permissions.html", user=user, buffers=permitted_buffers)


@app.route('/admin/users/<int:userid>/delete', methods=['GET', 'POST'])
@roles_required('superuser')
def admin_delete_user(userid):
    """
    Delete a user. The current user cannot be deleted.

    This action return a confirmation page. It is necessary to submit the confirmation form to complete the action.

    POST command parameters:

    * `confirm_token`: Confirmation token. Only applies to superuser/delete requests. Optional (returns the confirmation
        page if not present).
    * `next`: URL, the URL to return to after the update.

    :param userid: The user ID to modify.
    :return:
    """

    from quasselflask import forms

    logger.info(log_access())

    # validate
    if userid == current_user.qfuserid:
        flash("Oops! You can't delete yourself.", "error")
        return safe_redirect(get_next_url('POST'))

    # Valid - let's process it
    user = query_qfuser(db.session, userid)

    # check if confirmed
    is_confirmed = False
    data = {}
    if 'confirm_token' in request.form:
        try:
            data = forms.check_confirm_key(request.form.get('confirm_token'), 'admin_user_delete')
            is_confirmed = True
        except BadSignature:
            logger.error(log_action_error('update user', 'invalid confirmation key', ('user', _get_qfuser_log(user))))
            logger.debug('request.form=' + repr_user_input(request.form))
            is_confirmed = False

    if not is_confirmed:
        confirm_key = forms.generate_confirm_key({'current_user': current_user.qfuserid, 'target_user': user.qfuserid},
                                                 'admin_user_delete')
        return render_template('admin/update_user_confirm.html',
                               target=url_for('admin_delete_user', userid=userid),
                               user=user, action='delete', next_url=get_next_url('POST'),
                               confirm_key=confirm_key)
    else:
        valid_request = data.get('target_user', -1) == user.qfuserid and \
                        data.get('current_user', -1) == current_user.qfuserid
        if not valid_request:
            logger.error(log_action_error('delete user', 'invalid confirmation key', ('user', _get_qfuser_log(user))))
            logger.debug('confirmation data=' + repr_user_input(data))
            logger.debug('request.form=' + repr_user_input(request.form))
            raise BadRequest('Invalid confirmation key.')

        db.session.delete(user)
        flash('Deleted user {}'.format(user.username))
        db.session.commit()
        logger.info(log_action('delete user', ('user', _get_qfuser_log(user))))
        return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:userid>/reset-password', methods=['GET', 'POST'])
@roles_required('superuser')
def admin_user_reset_password(userid):
    """
    Reset the user's password and send them an email inviting them to change their password.

    This action return a confirmation page. It is necessary to submit the confirmation form to complete the action.

    POST command parameters:

    * `confirm_token`: Confirmation token. Optional (returns the confirmation page if not present).
    * `next`: URL, the URL to return to after the update.

    :param userid: The user ID to modify.
    :return:
    """

    from quasselflask import forms

    logger.info(log_access())

    if userid == current_user.get_id():
        flash("Can't force reset your own password: go change it from the user profile like a normal person, "
              "you dummy!", 'error')
        return safe_redirect(get_next_url('POST'))

    user = query_qfuser(db.session, userid)

    # check if confirmed
    is_confirmed = False
    data = {}
    if 'confirm_token' in request.form:
        try:
            data = forms.check_confirm_key(request.form.get('confirm_token'), 'admin_user_reset_password')
            is_confirmed = True
        except BadSignature:
            logger.error(log_action_error('update user', 'invalid confirmation key', ('user', _get_qfuser_log(user))))
            logger.debug('request.form=' + repr_user_input(request.form))
            is_confirmed = False

    if not is_confirmed:
        confirm_key = forms.generate_confirm_key({'current_user': current_user.qfuserid, 'target_user': user.qfuserid},
                                                 'admin_user_reset_password')
        return render_template('admin/update_user_confirm.html',
                               target=url_for('admin_user_reset_password', userid=userid),
                               user=user, action='reset password', next_url=get_next_url('POST'),
                               confirm_key=confirm_key)
    else:
        valid_request = data.get('target_user', -1) == user.qfuserid and \
                        data.get('current_user', -1) == current_user.qfuserid
        if not valid_request:
            logger.error(log_action_error('reset user password', 'invalid confirmation key',
                                          ('user', _get_qfuser_log(user))))
            logger.debug('confirmation data=' + repr_user_input(data))
            logger.debug('request.form=' + repr_user_input(request.form))
            raise BadRequest('Invalid confirmation key.')

        try:
            user.password = userman.hash_password(make_reset_password())
            send_new_user_set_password_email(user)
            db.session.commit()
            flash('User {user} login disabled; this user cannot login until they reset their password. A password '
                  'reset email has been sent to {email}.'
                  .format(user=user.username, email=user.email), 'success')
        except Exception as e:
            logger.error(log_action_error('error while creating user', repr(e.args),
                                          ('id', user.qfuserid), ('name', user.username),
                                          ('email', user.email), ('superuser', repr(user.superuser))), exc_info=True)
            db.session.rollback()
            if app.debug:
                raise  # let us debug this
            else:
                flash('Error occurred resetting password. Please try again later, or contact the server administrator '
                      'with the date/time of this error and your IP address in order to trace error information in the'
                      'logs.', 'error')
                return redirect(url_for('admin_manage_user', userid=user.qfuserid))

        logger.info(log_action('reset user password', ('user', _get_qfuser_log(user))))
        return safe_redirect(get_next_url('POST'))
