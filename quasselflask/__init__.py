"""
Main QuasselFlask package.

Project: QuasselFlask
"""

import flask
import flask_mail
import flask_script
import flask_sqlalchemy
import flask_user

import quasselflask.startup
from quasselflask.startup import init_app

__version_info__ = ('0', '6', '0')
__version__ = '.'.join(__version_info__)
__author__ = 'Marc-Alexandre Chan <laogeodritt@arenthil.net>'
__maintainer__ = 'Marc-Alexandre Chan <laogeodritt@arenthil.net>'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (c) 2016 Marc-Alexandre Chan and contributors'

# These will be populated by init_app()
app = quasselflask.startup.DummyObject('app')  # type: flask.Flask
db = quasselflask.startup.DummyObject('db')  # type: flask_sqlalchemy.SQLAlchemy
userman = quasselflask.startup.DummyObject('userman')  # type: flask_user.UserManager
cmdman = quasselflask.startup.DummyObject('cmdman')  # type: flask_script.Manager
mail = quasselflask.startup.DummyObject('mail')  # type: flask_mail.Mail
