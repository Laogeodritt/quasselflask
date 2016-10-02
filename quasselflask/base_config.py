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
