"""
App initialization and configuration.

Project: QuasselFlask
"""

import os
from flask import Flask
from flask_mail import Mail
from flask_user import SQLAlchemyAdapter, UserManager, LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_wtf.csrf import CsrfProtect


class DummyObject:
    """
    Dummy object that provides a helpful error message on attempting to access or call attributes/methods.
    """
    error_format = 'Cannot access {}.{}: quasselflask.init_app() has not been called.'

    def __init__(self, name='component'):
        self.name = name

    def __getattr__(self, item):
        error_msg = self.error_format.format(self.name, item)
        raise RuntimeError(error_msg)

    def __setattr__(self, key, value):
        if key == 'name':
            super().__setattr__(key, value)
        else:
            self.__getattr__(key)


def init_app(instance_path=None):
    """
    Initializes Flask configurations, SQLAlchemy, Quasselflask-specific setup, Flask extension setup/glue.
    Imports SQLAlchemy models (will create DB connections immediately due to the need to reflect Quassel).

    Does not create Quasselflask-specific tables - need to call ``init_db()``.
    :return:
    """
    import quasselflask
    from quasselflask.base_config import DefaultConfig, InternalConfig
    from quasselflask.parsing.irclog import DisplayBacklog
    from quasselflask.parsing.form import PasswordValidator

    # Flask
    app = quasselflask.app = Flask(__name__,
                                   instance_path=os.environ.get('QF_CONFIG_PATH', None),
                                   instance_relative_config=True)
    app.config.from_object(DefaultConfig)
    app.config.from_object(InternalConfig)
    app.config.from_pyfile('quasselflask.cfg')

    if not app.config.get('SECRET_KEY', None):
        raise EnvironmentError("QuasselFlask SECRET_KEY parameter not set or empty in configuration")

    app.config['USER_APP_NAME'] = app.config['SITE_NAME']  # used by Flask-User email templates

    # Flask-Script
    cmdman = quasselflask.cmdman = Manager(app)
    cmdman.help_args = ('-?', '--help')

    # Database
    db = quasselflask.db = SQLAlchemy(app)
    import quasselflask.models
    quasselflask.models.qf_create_all()

    # Forms
    CsrfProtect(app)

    # Flask-Mail, for Flask-User
    mail = quasselflask.mail = Mail(app)  # Flask-Mail, for Flask-User

    # Flask-User
    db_adapter = SQLAlchemyAdapter(db, quasselflask.models.QfUser)
    loginman = LoginManager()
    loginman.anonymous_user = quasselflask.models.QfAnonymousUserMixin
    userman = quasselflask.userman = UserManager(db_adapter, app,
                                                 password_validator=PasswordValidator(
                                                     min=app.config['QF_PASSWORD_MIN'],
                                                     max=app.config['QF_PASSWORD_MAX'],
                                                     required_regex=app.config['QF_PASSWORD_REGEX'],
                                                     message=app.config['QF_PASSWORD_MSG']),
                                                 login_manager=loginman
                                                 )

    # Configure other internal classes
    DisplayBacklog.set_time_format(app.config['TIME_FORMAT'])

    import quasselflask.views
    import quasselflask.commands

    return app
