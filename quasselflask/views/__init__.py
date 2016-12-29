"""
Flask endpoints for this application.

Project: QuasselFlask
"""

import quasselflask

import quasselflask.views.core
import quasselflask.views.admin

# TODO: refactor when merging with main branch
# if os.environ.get('QF_ALLOW_TEST_PAGES'):
#     import quasselflask.views.test
