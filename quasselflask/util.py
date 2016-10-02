"""
Miscellaneous utilities.

Project: QuasselFlask
"""

from quasselflask import app
from quasselflask.base_config import DefaultConfig


def repr_user_input(obj):
    """
    Get a representation of an object resulting from user input appropriate for logging. This method limits the length
    of the representation to the MAX_LOG_LENGTH_USER_INPUT config parameter, in order to prevent log growth in the case
    of unexpectedly large user input.

    This method also prepends the original length of the representation.
    :param obj:
    :return:
    """
    s = repr(obj)[0:app.config.get('MAX_LOG_LENGTH_USER_INPUT', DefaultConfig.MAX_LOG_LENGTH_USER_INPUT)]
    return '[' + str(len(s)) + ']' + s

