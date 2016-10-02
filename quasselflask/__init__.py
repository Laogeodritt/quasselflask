"""
Main QuasselFlask package.

Project: QuasselFlask
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

__version__ = "0.1"

app = Flask(__name__, instance_path=os.environ.get('QF_CONFIG_PATH', None), instance_relative_config=True)
db = SQLAlchemy(app)

# noinspection PyPep8
from quasselflask.startup import init_app
