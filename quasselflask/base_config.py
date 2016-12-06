"""
QuasselFlask base and internal configuration.

Project: QuasselFlask
"""

import os


class DefaultConfig:
    """
    These configuration variables can be copied into your quasselflask.cfg file and changed.
    Only copy the lines you want to change. You don't need to copy all of them if the defaults are OK.

    Commented lines must be set in your quasselflask.cfg file.
    """

    # SQLALCHEMY_DATABASE_URI = 'postgresql://sqluser:password@hostname-or-IP-address/databasename'  # SQL config
    SITE_NAME = 'SiteName'
    RESULTS_NUM_DEFAULT = 100  # Default number of results per query set in the search form
    RESULTS_NUM_MAX = 1000  # Maximum number of results per query
    TIME_FORMAT = '{:%Y-%m-%d %H:%M:%S}'  # Time format to show in IRC lots, should be Python .format() compatible
    SECRET_KEY = ''  # IMPORTANT: Set this for security! See documentation

    QF_PASSWORD_MIN = 12  # Minimum password length for Quasselflask users
    QF_PASSWORD_MAX = 128  # Maximum password length for Quasselflask users (generally shouldn't set this low)
    QF_PASSWORD_REGEX = (r'[A-Z]', r'[a-z]', r'[0-9]')  # tuple of regexes that must all match a valid password
    QF_PASSWORD_MSG = 'must be at least 12 characters long, and contain at least one uppercase letter, '\
                      'one lowercase letter and one digit.'

    QF_ADMIN_CONFIRM_TIME = 600  # seconds - max time for admin user to respond to a confirm dialog for some actions

    USER_PASSWORD_HASH = 'sha512_crypt'
    USER_CONFIRM_EMAIL_EXPIRATION = 3*24*3600  # seconds
    USER_RESET_PASSWORD_EXPIRATION = 24*3600  # seconds

    # MAIL_USERNAME = 'email@example.com'  # SMTP username (for user account-related emails)
    # MAIL_PASSWORD = 'password'  # SMTP password (for user account-related emails)
    # MAIL_DEFAULT_SENDER = '"Sender" <noreply@example.com>'  # 'From' address (for user account-related emails)
    # MAIL_SERVER = 'smtp.gmail.com'  # SMTP server (for user account-related emails)
    # MAIL_PORT = 465  # SMTP server's port (for user account-related emails)
    # MAIL_USE_SSL = True  # SMTP server: whether to connect with SSL (for user account-related emails)
    # MAIL_USE_TLS = False  # SMTP server: whether to connect with TLS (for user account-related emails)

    MAX_LOG_LENGTH_USER_INPUT = 1024  # For logs involving user input, max log length (avoids large logs on large input)


class InternalConfig:
    """
    Internal configuration of Flask and its extensions or other libraries. Generally don't change these unless you're
    very sure of what you're doing.
    """

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = bool(os.environ.get('FLASK_DEBUG', 0))
    CSRF_ENABLED = True

    USER_ENABLE_CHANGE_PASSWORD = True
    USER_ENABLE_CHANGE_USERNAME = False
    USER_ENABLE_CONFIRM_EMAIL = True
    USER_ENABLE_FORGOT_PASSWORD = True
    USER_ENABLE_LOGIN_WITHOUT_CONFIRM = False
    USER_ENABLE_EMAIL = True
    USER_ENABLE_MULTIPLE_EMAILS = False
    USER_ENABLE_REGISTRATION = False
    USER_ENABLE_RETYPE_PASSWORD = True
    USER_ENABLE_USERNAME = True

    USER_AUTO_LOGIN_AFTER_CONFIRM = False
    USER_INVITE_EXPIRATION = 7*24*3600  # seconds
    USER_SEND_PASSWORD_CHANGED_EMAIL = True
    USER_SEND_REGISTERED_EMAIL = True
    USER_SHOW_USERNAME_EMAIL_DOES_NOT_EXIST = False

    USER_LOGIN_URL = '/user/login'
    USER_LOGOUT_URL = '/user/logout'
