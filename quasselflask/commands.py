"""
Terminal commands for quasselflask. Mostly used for non-web maintenance tasks, e.g., creating a database.

Project: Quasselflask
"""

from sys import stderr
from datetime import datetime

import sqlalchemy.orm
from sqlalchemy import func
from flask_script import prompt_bool, prompt_pass
from flask_script.commands import InvalidCommand

from quasselflask import db, cmdman, userman


@cmdman.command
def init_superuser(name, email, password=''):
    """
    Creates a new superuser for Quasselflask, so that you can login. Will only work if no superuser currently exists
    (if there is,

    :param name: Username of superuser account to create.
    :param email: Email address of the account to create. This address will be considered automatically confirmed, but
        an email will be sent out confirming registration.
    :param password: Plain-text password of the superuser account to create. It is recommended to log in and change this
        password via the web interface. If not specified, will prompt at the command line.
    """
    from quasselflask.models import QfUser as User
    db_adapter = userman.db_adapter
    user_class_fields = User.__dict__
    user_fields = {}

    # Check for no superusers yet
    num_superusers = db.session.query(func.count(User.qfuserid)).filter_by(superuser=True).scalar()
    if num_superusers > 0:
        raise InvalidCommand(
            '{:d} superusers already exist. Please login as superuser and use the Web UI to create new superuser.'
            .format(num_superusers))

    # Populate a register_form - to allow easy validation per system settings
    form = userman.register_form(csrf_enabled=False)
    form.username.data = name
    form.email.data = email
    form.password.data = form.retype_password.data = password
    form.validate()

    validation_errors = form.errors
    validation_errors.pop('password', None)
    validation_errors.pop('retype_password', None)
    if validation_errors:
        _print_form_errors(validation_errors)
        raise InvalidCommand()

    # Prompt for password (only show errors after user has entered something)
    first_prompt = True
    while not form.validate():
        if not first_prompt:
            _print_form_errors(form.errors)
        else:
            first_prompt = False

        try:
            form.password.data = prompt_pass("Password", default=None)
            form.retype_password.data = prompt_pass("Retype password", default=None)
        except KeyboardInterrupt:
            raise InvalidCommand("Cancelled by KeyboardInterrupt.")

    # Create and save the user
    # For all form fields
    for field_name, field_value in form.data.items():
        # Hash password field
        if field_name == 'password':
            user_fields['password'] = userman.hash_password(field_value)
        # Store corresponding Form fields into the User object
        else:
            if field_name in user_class_fields:
                user_fields[field_name] = field_value

    # Hardcoded user fields
    user_fields['active'] = True
    user_fields['superuser'] = True
    user_fields['confirmed_at'] = datetime.utcnow()

    # Add User record using named arguments 'user_fields'
    db_adapter.add_object(User, **user_fields)
    db_adapter.commit()

    print('Created superuser: {} <{}>'.format(user_fields['username'], user_fields['email']))
    print("Email address is assumed confirmed. Make sure it\'s correct. You can change it in the web interface.")


def _format_form_errors(errors: {str: [str]}) -> [str]:
    """

    :param errors: Errors structure, directly from a WTForm's form.errors attribute
    :return: A list of string errors
    """
    if not errors:
        return []
    result = []
    for field, errlist in errors.items():
        result.extend(['{}: {}'.format(field, error) for error in errlist])
    return result


def _print_form_errors(errors: {str: [str]}) -> None:
    error_strings = _format_form_errors(errors)
    if not error_strings:
        print("Something went wrong! This isn't supposed to happen! Erm... try something else? ^^;\n",
              file=stderr)
    elif len(error_strings) == 1:
        print("Error: {}\n".format(error_strings[0]), file=stderr)
    else:
        print("Multiple errors occurred:\n    - {}\n".format("\n    - ".join(error_strings)), file=stderr)


@cmdman.command
def reset_db():
    """
    Drops the Quasselflask-specific database tables. Does not drop quassel tables (but use this at your own risk!
    Have backups!). The connected PostgreSQL user must be owner (or member to the owner group) of the table to drop it.
    :return:
    """
    from quasselflask import models
    if prompt_bool('Are you sure? This will delete all QuasselFlask users and permissions and CANNOT BE UNDONE. '
                   'Quassel database will not be deleted. You will need to run the "init_superuser" '
                   'command again to set up QuasselFlask tables and superuser. (y|n) Default: '):
        models.qf_drop_all()
        print('Database tables for Quasselflask dropped.')
    else:
        print('Cancelled by user. Database has not been modified.')
