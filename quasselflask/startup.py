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
        self._is_init = False
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


# noinspection PyUnresolvedReferences,PyUnresolvedReferences
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
                                   instance_path=os.environ.get('QF_CONFIG_PATH', instance_path),
                                   instance_relative_config=True)
    app.config.from_object(DefaultConfig)
    app.config.from_object(InternalConfig)
    app.config.from_pyfile('quasselflask.cfg')
    app.config.from_envvar('QF_ALLOW_TEST_PAGES', True)

    if not app.config.get('SECRET_KEY', None):
        raise EnvironmentError("QuasselFlask SECRET_KEY parameter not set or empty in configuration")

    app.config['USER_APP_NAME'] = app.config['SITE_NAME']  # used by Flask-User email templates

    init_logging()
    app.logger.info('QuasselFlask {}'.format(quasselflask.__version__))
    app.logger.info('Initialising...')

    # Flask-Script
    cmdman = quasselflask.cmdman = Manager(app)
    cmdman.help_args = ('-?', '--help')

    # Database
    app.logger.info('Configuring database.')
    db = quasselflask.db = SQLAlchemy(app)
    app.logger.info('Connecting to database and analysing quasselcore tables. This may take a while...')
    import quasselflask.models.models
    app.logger.info('Checking QuasselFlask tables and creating if necessary...')
    quasselflask.models.models.qf_create_all()

    # Forms
    CsrfProtect(app)

    # Flask-Mail, for Flask-User
    mail = quasselflask.mail = Mail(app)  # Flask-Mail, for Flask-User

    # Flask-User
    db_adapter = SQLAlchemyAdapter(db, quasselflask.models.models.QfUser)
    loginman = LoginManager()
    loginman.anonymous_user = quasselflask.models.models.QfAnonymousUserMixin
    userman = quasselflask.userman = UserManager(db_adapter, app,
                                                 password_validator=PasswordValidator(
                                                     len_min=app.config['QF_PASSWORD_MIN'],
                                                     len_max=app.config['QF_PASSWORD_MAX'],
                                                     required_regex=app.config['QF_PASSWORD_REGEX'],
                                                     message=app.config['QF_PASSWORD_MSG']),
                                                 login_manager=loginman
                                                 )

    # Configure other internal classes
    DisplayBacklog.set_time_format(app.config['TIME_FORMAT'])

    app.logger.debug('Configuring web endpoints...')
    import quasselflask.views
    app.logger.debug('Configuring command-line commands...')
    import quasselflask.commands

    return app


def init_logging():
    """
    Initialise logging. Does nothing in debug mode (assumption that developer is checking their console or redirecting
    output to file when running in debug mode).
    :return:
    """
    from quasselflask import app
    if app.config.get('QF_LOGGING_ENABLE', False):
        from os import path
        import logging
        from logging.handlers import RotatingFileHandler
        log_filename = app.config.get('QF_LOGGING_FILENAME', 'quasselflask.log')
        log_filepath = path.join(app.instance_path, log_filename)
        max_size = app.config.get('QF_LOGGING_MAX_BYTES', 10*1024*1024)
        max_backups = app.config.get('QF_LOGGING_MAX_BACKUPS', 4)

        file_handler = RotatingFileHandler(log_filepath, maxBytes=max_size, backupCount=max_backups, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        app.logger.addHandler(file_handler)

        # For access logs
        wz_logger = logging.getLogger('werkzeug')
        wz_logger.addHandler(file_handler)
