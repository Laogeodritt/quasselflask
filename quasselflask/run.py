"""
Starts the WSGI web application. If run directly from the command line, starts a development web server.

Project: QuasselFlask
"""

import quasselflask

quasselflask.init_app()

if __name__ == "__main__":
    quasselflask.cmdman.run()
    # quasselflask.app.run()
