"""
Flask endpoints for admin area.

Project: Quasselflask
"""

from datetime import datetime

from flask import request, url_for, flash, redirect, render_template
from flask.ext.login import current_user
from flask.ext.user import roles_required
from itsdangerous import BadSignature
from werkzeug.exceptions import BadRequest

from quasselflask import app, userman, db
from quasselflask.parsing.data_convert import convert_permissions_lists, convert_user_permissions
from quasselflask.querying import *
from quasselflask.util import random_string, safe_redirect, get_next_url


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

        return redirect(url_for('admin_manage_user', userid=user.qfuserid))

    # Process GET or invalid POST
    return render_template('admin/create_user.html', form=create_form, register_form=create_form)


@app.route('/admin/users', methods=['GET'])
@roles_required('superuser')
def admin_users():
    users = query_all_qf_users(db.session)
    return render_template('admin/user_list.html', users=users)


@app.route('/admin/users/<userid>', methods=['GET', 'POST'])
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
    # get current user to manage
    user = query_qfuser(userid)

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


@app.route('/admin/users/<userid>/update', methods=['POST'])
@roles_required('superuser')
def admin_update_user(userid):
    """
    Update the current user's information. Any fields not included will remain unchanged.

    Some actions return a confirmation page. It is necessary to submit the confirmation form to complete the action.

    If acting on the current user, only the email address may be updated.  This prevents the current user from locking
    themselves out of the application or removing a sole superuser.

    POST command parameter (exactly one required, except email and confirm_email may appear together):

    * `status`: 1 (enabled) or 0 (disabled). Other values treated as 0.
    * `superuser`: 1 (superuser) or 0 (normal user). Other values treated as 0. Returns a confirmation page.
    * `delete`: 1. Returns a confirmation page.
    * `confirm_token`: Confirmation token. Only applies to superuser/delete requests.
    * `email`: new email address. Can only be combined with the `confirm_email` parameter.
    * `confirm_email`: 1 (confirm) or 0 (unconfirm). Force the email confirmation status. Other values are treated as 0.
            Can only be combined with the `email` parameter.

    Other POST parameters, common to all requests:

    * `next`: URL, the URL to return to after the update.

    :param userid: The user ID to modify.
    :return:
    """

    from quasselflask import forms

    commands = frozenset(('status', 'superuser', 'delete', 'email', 'confirm_email', 'confirm_token'))
    request_commands = set(request.form.keys()) & commands

    # validate
    request_valid = len(request_commands) == 1 or \
        (len(request_commands) == 2 and 'email' in request_commands and 'confirm_email' in request_commands)
    user_valid = (userid != current_user.qfuserid or
                  ('email' in request_commands and request.form.get('confirm_email', '0') == '1'))

    if not request_valid:
        raise BadRequest("Multiple commands to user update API endpoint")

    if not user_valid:
        flash("Oops! You can't make changes that would disable yourself.", "error")
        return safe_redirect(get_next_url('POST'))

    # Valid - let's process it
    user = query_qfuser(userid)

    if 'status' in request.form:
        status_arg = request.form.get('status', '0')
        status_val = bool(status_arg == '1')
        user.active = status_val
        db.session.commit()
        flash(('Enabled' if status_val else 'Disabled') + ' user {}'.format(user.username), 'notice')
        return safe_redirect(get_next_url('POST'))

    elif 'superuser' in request.form or 'delete' in request.form:  # non-confirmed
        if 'superuser' in request.form:
            request_property = 'superuser'
            request_value = '1' if request.form.get(request_property, '0') == '1' else '0'
        elif 'delete' in request.form:
            request_property = 'delete'
            if not request.form.get(request_property) == '1':
                raise BadRequest("Delete value must be '1'")
            request_value = '1'
        else:
            raise BadRequest('Well, this is unfortunate. No idea how you got here. Huh. Might want to contact the devs '
                             'about this very... odd... bug. It\'s in the superuser/delete commands handler.')

        confirm_key = forms.get_user_update_confirm_key(userid, request_property, request_value)
        return render_template('admin/update_user_confirm.html',
                               user=user, property=request_property, value=request_value, next_url=get_next_url('POST'),
                               confirm_key=confirm_key)

    elif 'confirm_token' in request.form:  # confirm superuser/delete
        try:
            data = forms.check_user_update_confirm_key(request.form.get('confirm_token'))
        except BadSignature as e:
            raise BadRequest('Invalid confirmation key.')

        request_userid = data['userid']
        request_property = data['update']
        request_value = data['value']
        valid_request = request_userid == userid and \
            ((request_property == 'superuser' and request_value in ['1', '0']) or
             (request_property == 'delete' and request_value == '1'))
        if not valid_request:
            raise BadRequest('Invalid confirmation key.')

        if request_property == 'superuser':
            user.superuser = bool(request_value == '1')
            flash('Set user {} as {}'.format(user.username, 'superuser' if user.superuser else 'normal user'), 'notice')
            db.session.commit()
            return safe_redirect(get_next_url('POST'))
        elif request_property == 'delete':  # request_value should have been validated in valid_request
            db.session.delete(user)
            flash('Deleted user {}'.format(user.username))
            db.session.commit()
            return redirect(url_for('admin_users'))
        db.session.commit()
        return safe_redirect(get_next_url('POST'))

    elif 'email' in request.form or 'confirm_email' in request.form:
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
        return safe_redirect(get_next_url('POST'))

    else:
        return safe_redirect(get_next_url('POST'))


@app.route('/admin/users/<userid>/permissions', methods=['POST'])
@roles_required('superuser')
def admin_permissions(userid):
    """
    On POST request, update a user's permissions. Redirects to the user management page.

    POST parameters:

    * `permissions`: data in the following structure:

        .. code-block:: json
            {
                "permissions": [
                    {
                        "action": "add|remove",
                        "access": "allow|deny",
                        "type": "user|network|buffer",
                        "id": 0,
                        "qfpermid": 0
                    },
                    { ... }
                ],
                "default": "allow|deny"
            }

        ``id`` represents the quasseluser, network or buffer ID. ``qfpermid`` is the ID of an existing record and
        only applies if "action" is "remove" (this is used for efficiency; if the permission ID does not correspond to
        the rest of the information in the object, an error is returned).


    :param userid: The user ID to modify.
    :return:
    """
    return 'update permissions'  # TODO
