"""
Flask endpoints for this application.

Project: QuasselFlask
"""

import quasselflask

import quasselflask.views.core
import quasselflask.views.admin

if quasselflask.app.config.get('QF_ALLOW_TEST_PAGES'):
    import quasselflask.views.test
