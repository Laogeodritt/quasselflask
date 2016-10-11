"""
Starts the WSGI web application. If run directly from the command line, starts a development web server.

Project: QuasselFlask
"""

import sys
from flask_script.commands import InvalidCommand
import quasselflask

quasselflask.init_app()

if __name__ == "__main__":
    try:
        quasselflask.cmdman.run()
    except InvalidCommand as e:
        print(e, file=sys.stderr)
        sys.exit(1)
