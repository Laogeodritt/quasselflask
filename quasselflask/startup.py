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
    post_init_error_format = 'Cannot access {}.{}: the calling module is imported during init_app and appears to ' \
                             'have been misconfigured. Modules imported during init_app must be careful to ' \
                             '`import quasselflask` and not `from quasselflask import app` (for the variables ' \
                             'available directly at the module level; sub-modules are OK), and must not assign ' \
                             '`quasselflask.app` and similar to other variables at the module level, to avoid ' \
                             'getting this dummy object before init_app has run.'

    _dummies = []

    @classmethod
    def set_all_init(cls):
        for dummy in cls._dummies:
            dummy.set_init()

    def __init__(self, name='component'):
        self.name = name
        DummyObject._dummies.append(self)

    def __getattr__(self, item):
        if not self._is_init:
            error_msg = self.error_format.format(self.name, item)
        else:
            error_msg = self.post_init_error_format.format(self.name, item)
        raise RuntimeError(error_msg)

    def __setattr__(self, key, value):
        if key == 'name' or key == '_is_init':
            super().__setattr__(key, value)
        else:
            self.__getattr__(key)

    def set_init(self):
        self._is_init = True


def init_app(instance_path=None):
    """
    Initializes Flask configurations, SQLAlchemy, Quasselflask-specific setup, Flask extension setup/glue.
    Imports SQLAlchemy models (will create DB connections immediately due to the need to reflect Quassel).

    Does not create Quasselflask-specific tables - need to call ``init_db()``.
    :return:
    """

    # flag the dummy as during/after init_app call - just to be nice to devs who misconfigure sensitive modules!
    # Need to do this before the import calls to allow them to be flagged if issues exist at the module level
    DummyObject.set_all_init()

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
