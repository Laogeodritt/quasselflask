"""
App initialization and configuration.

Project: QuasselFlask
"""

from flask_mail import Mail
from flask_user import SQLAlchemyAdapter, UserManager

from quasselflask import app, db
from quasselflask.base_config import DefaultConfig, InternalConfig
from quasselflask.parsing.irclog import DisplayBacklog


def init_app():
    app.config.from_object(DefaultConfig)
    app.config.from_object(InternalConfig)
    app.config.from_pyfile('quasselflask.cfg')

    if not app.config.get('SECRET_KEY', None):
        raise EnvironmentError("QuasselFlask SECRET_KEY parameter not set or empty in configuration")

    DisplayBacklog.set_time_format(app.config['TIME_FORMAT'])

    mail = Mail(app)  # Flask-Mail, for Flask-User

    # User/Login handling
    app.config['USER_APP_NAME'] = app.config['SITE_NAME']  # used by Flask-Usere email templates
    # TODO: make/set anonymous (not-logged-in) class in Flask-User (flask-login specifically) with is_superuser() - "Anonymous users" section https://flask-login.readthedocs.io/en/latest/

    from quasselflask.models import QfUser
    db_adapter = SQLAlchemyAdapter(db, QfUser)
    user_manager = UserManager(db_adapter, app)

    import quasselflask.views

    return app
