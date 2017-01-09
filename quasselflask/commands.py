"""
Terminal commands for quasselflask. Mostly used for non-web maintenance tasks, e.g., creating a database.

Project: Quasselflask
"""

from sys import stderr
from datetime import datetime
import time

import sqlalchemy.orm
from sqlalchemy import func
from quasselflask import app
from flask_script import prompt_bool, prompt_pass
from flask_script.commands import InvalidCommand

from quasselflask import db, cmdman, userman, __version__ as qf_version

_start_time = None


def _timer_start():
    global _start_time
    _start_time = time.time()


def _timer_print():
    print('Completed in {:.3f}s'.format(time.time() - _start_time))


@cmdman.command
def create_superuser(name, email, password=''):
    """
    Creates a new superuser for Quasselflask, so that you can login. Will only work if no superuser currently exists
    (if there is,

    :param name: Username of superuser account to create.
    :param email: Email address of the account to create. This address will be considered automatically confirmed, but
        an email will be sent out confirming registration.
    :param password: Plain-text password of the superuser account to create. It is recommended to log in and change this
        password via the web interface. If not specified, will prompt at the command line.
    """
    from quasselflask.models.models import QfUser as User
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

    _timer_start()

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
    user_fields['themeid'] = app.config.get('QF_DEFAULT_THEME', 0)

    # Add User record using named arguments 'user_fields'
    db_adapter.add_object(User, **user_fields)
    db_adapter.commit()

    print('Created superuser: {} <{}>'.format(user_fields['username'], user_fields['email']))
    print("Email address is assumed confirmed. Make sure it\'s correct. You can change it in the web interface.")
    _timer_print()


@cmdman.command
def create_indices():
    """
    Create all indices used for QuasselFlask searches.
    :return:
    :raise Exception: SQLAlchemy exceptions???
    """
    from quasselflask.models import models
    if prompt_bool(
            'Are you sure? This will build new indices to speed up QuasselFlask searches. DEPENDING ON QUASSEL '
            'BACKLOG SIZE, THIS CAN TAKE SEVERAL MINUTES. If indices were already built, you should run '
            '`drop_indices` first to drop them. (y|n) Default:'):
        print('Creating indices. This may take several minutes. Please wait...')
        _timer_start()
        models.qf_create_indices()
        print('Database indices for QuasselFlask created. (Existing indices have not been changed).')
        _timer_print()
    else:
        print('Cancelled by user. Database has not been modified.')


@cmdman.command
def reset_indices():
    """
    Drop all search indices made specifically for QuasselFlask. This should not affect the database objects for your
    quasselcore installation---but use at your own risk and have backups anyway!
    :return:
    """
    from quasselflask.models import models
    if prompt_bool('Are you sure? This will delete all QuasselFlask-specific search indices and CANNOT BE UNDONE. '
                   'Quassel database will not be deleted. You will need to run the "create_indices" '
                   'command again to create the indices. (y|n) Default:'):
        print('Dropping indices...')
        _timer_start()
        models.qf_drop_indices()
        print('Database indices for QuasselFlask search dropped.')
        _timer_print()
    else:
        print('Cancelled by user. Database has not been modified.')


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
    Have backups!), and does not drop search indices. The connected PostgreSQL user must be owner (or member to the
    owner group) of the table to drop it.
    :return:
    """
    from quasselflask.models import models
    if prompt_bool('Are you sure? This will delete all QuasselFlask users and permissions and CANNOT BE UNDONE. '
                   'Quassel database will not be deleted. You will need to run the "create_superuser" '
                   'command again to set up QuasselFlask tables and superuser. (y|n) Default:'):
        print('Dropping tables...')
        models.qf_drop_tables()
        print('Database tables for Quasselflask dropped.')
    else:
        print('Cancelled by user. Database has not been modified.')
