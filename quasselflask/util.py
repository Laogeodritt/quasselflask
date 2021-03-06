"""
Miscellaneous utilities.

Project: QuasselFlask
"""

import random
import string
from urllib.parse import urlparse, urljoin

# NOTE: This file is imported very early in the startup process, when some Flask objects (like app) may not have been
# constructed yet. This module should be treated as a "leaf" module that doesn't have dependencies on modules that have
# Flask dependencies, except "import quasselflask" (avoid using "from quasselflask import ...") and totally independent
# modules like quasselflask.base_config. Otherwise, circular dependencies or breaking the startup sequence may result.

from flask import request
from flask_user import current_user
from werkzeug.utils import redirect as unsafe_redirect

import quasselflask
from quasselflask.base_config import DefaultConfig

random.seed()


def repr_user_input(obj):
    """
    Get a representation of an object resulting from user input appropriate for logging. This method limits the length
    of the representation to the MAX_LOG_LENGTH_USER_INPUT config parameter, in order to prevent log growth in the case
    of unexpectedly large user input.

    This method also prepends the original length of the representation.
    :param obj:
    :return:
    """
    s = repr(obj)[0:quasselflask.app.config.get('MAX_LOG_LENGTH_USER_INPUT', DefaultConfig.MAX_LOG_LENGTH_USER_INPUT)]
    return '[' + str(len(s)) + ']' + s


def random_string(length=16, chars=string.printable) -> str:
    """
    Generates a random string. This uses Python's ``random`` module and is not cryptographically strong.
    :param length: Number of characters.
    :param chars: A sequence containing valid characters or substrings. The random string is generated by choosing from
        this sequence.
    :return: Random string.
    """
    return ''.join(random.choice(chars) for _ in range(length))


def safe_redirect(location, *args, **kwargs):
    """
    Safe redirect, built on top of ``werkzeug.util.redirect``. Verifies that the protocol is HTTP or HTTPS and the
    hostname is the same as the Flask request hostname. Must be called in a Flask request context.

    Used for a dirty hack, because Flask-User 0.6.8 doesn't implement secure redirects.

    If you want to redirect to an external domain, use quasselflask.util.unsafe_redirect instead (equivalent to the
    original werkzeug.utils.redirect).

    The method used is described at: http://flask.pocoo.org/snippets/62/

    :raise ValueError: redirect URL is unsafe
    """
    response = unsafe_redirect(location, *args, **kwargs)

    # check either no location set, or is safe:
    if not response.headers.get('Location', None) or is_safe_url(response.headers.get('Location')):
        return response
    else:
        raise ValueError("Unsafe redirect blocked: redirect must be to same hostname.")


def is_safe_url(target):
    """
    Check whether the URL is safe (HTTP or HTTPS protocol, same hostname).

    Source: http://flask.pocoo.org/snippets/62/

    :param target: Target URL string
    :return: True if safe URL, false otherwise.
    """
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def get_next_url(method='GET', default='home'):
    """
    Get the 'next' URL to redirect to after completing an operation. Returns the 'next' parameter, HTTP referer or the
    specified default endpoint, in order of priority.

    :param method: If 'GET', search for the 'next' parameter in query args. If 'POST', search in POST parameters.
    :param default: Name of the default endpoint.
    :return:
    """
    from flask import url_for
    if method == 'GET':
        return request.args.get('next', request.referrer or url_for(default))
    else:
        return request.form.get('next', request.referrer or url_for(default))


def log_access():
    return 'ACCESS [QFUSER={user.qfuserid:d} {user.username}] {endpoint}' \
                .format(user=current_user, endpoint=request.endpoint)


def log_action(action: str, *args: tuple):
    if args:
        str_params = ', '.join(('{}={}'.format(key, value) for key, value in args))
    else:
        str_params = ''
    logmsg = 'ACTION [QFUSER={user.qfuserid:d} {user.username}] {action} {params}'\
        .format(user=current_user, action=action, params=str_params)
    return logmsg


def log_action_error(action: str, msg: str, *args: tuple):
    if args:
        str_params = ', '.join(('{}={}'.format(key, value) for key, value in args))
    else:
        str_params = ''
    logmsg = 'ERROR [QFUSER={user.qfuserid:d} {user.username}] {action} {params}: {errmsg}' \
        .format(user=current_user, action=action, params=str_params, errmsg=msg)
    return logmsg
