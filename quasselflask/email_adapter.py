"""
Utilities for email functions. This makes use of Flask-User's email functionality.

Project: Quasselflask
"""

from flask import url_for
from flask_user import emails

from quasselflask import userman
from quasselflask.models.models import QfUser


def send_new_user_set_password_email(user: QfUser):
    """
    Since new users are created by a superuser, they need to set their password on first login.
    This method sends the reset password email, which also doubles as a welcome/registered email.

    This should mark the user as confirmed when the password is reset (see Flask-User v0.6.8 flask_user/views.py:578).

    :param user: QfUser to whom to send via their registered email address
    :return:
    """
    db_adapter = userman.db_adapter
    if userman.enable_email and (userman.send_registered_email or userman.enable_confirm_email):
        # Generate password reset link
        object_id = int(user.get_id())
        token = userman.generate_token(object_id)
        reset_password_link = url_for('user.reset_password', token=token, _external=True)

        # send password reset email (when reset, marks email as confirmed: see flask_user/views.py:578 v0.6.8)
        emails.send_registered_email(user, None, reset_password_link)
        db_adapter.update_object(user, reset_password_token=token)
        db_adapter.commit()


def send_confirm_email_email(user: QfUser):
    """
    Send the user an email asking to confirm their email.

    :param user: QfUser to whom to send via their registered email address
    :return:
    """
    if userman.enable_email and userman.enable_confirm_email:
        # Generate confirm email link
        object_id = int(user.get_id())
        token = userman.generate_token(object_id)
        confirm_email_link = url_for('user.confirm_email', token=token, _external=True)

        emails.send_confirm_email_email(user, None, confirm_email_link)
