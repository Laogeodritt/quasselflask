"""
Custom forms (various forms also come from Flask-User)

Project: Quasselflask
"""

from flask import current_app
from flask_user.forms import unique_username_validator, unique_email_validator
from flask_wtf import Form
from itsdangerous import URLSafeTimedSerializer
from wtforms import BooleanField, HiddenField, PasswordField, SubmitField, StringField
from wtforms import validators, ValidationError


# for use for signing or creating security keys - not needed for CSRF (handled by WTForms)
signer = URLSafeTimedSerializer(current_app.secret_key, signer_kwargs={'key_derivation': 'hmac'})


def get_user_update_confirm_key(userid, update, value):
    return signer.dumps({'userid': userid, 'update': update, 'value': value}, salt='admin_user_update')


def check_user_update_confirm_key(key: str) -> dict:
    """
    Check the confirmation key. Automatically uses app.config.QF_ADMIN_CONFIRM_TIME.

    An error class is raised if the check fails; errors are the same as `itsdangerous.TimedSerializer.loads`.
    https://pythonhosted.org/itsdangerous/

    :param key: Key to check
    :return: {'userid': userid, 'update': update, 'value': value}
    """
    return signer.loads(key, max_age=current_app.config.get('QF_ADMIN_CONFIRM_TIME'), salt='admin_user_update')


class CreateUserForm(Form):
    """
    Form for creating new users via the admin panel.

    Modified from Flask-User 0.6.8 (RegisterForm) - BSD Licence.
    """
    username = StringField('Username', validators=[
        validators.DataRequired('Username is required'),
        unique_username_validator])
    email = StringField('Email', validators=[
        validators.DataRequired('Email is required'),
        validators.Email('Invalid Email'),
        unique_email_validator])
    superuser = BooleanField('Superuser', description="Is this user a superuser?")
    invite_token = HiddenField('Token')

    submit = SubmitField('Create')

    def validate(self):
        # remove certain form fields depending on user manager config
        user_manager = current_app.user_manager
        if not user_manager.enable_username:
            delattr(self, 'username')
        if not user_manager.enable_email:
            delattr(self, 'email')
        # Add custom username validator if needed
        if user_manager.enable_username:
            has_been_added = False
            for v in self.username.validators:
                if v == user_manager.username_validator:
                    has_been_added = True
            if not has_been_added:
                self.username.validators.append(user_manager.username_validator)
        # Validate field-validators
        return super(CreateUserForm, self).validate()
