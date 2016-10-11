"""
File description.

Project: Project Name
"""
from unittest import TestCase
from wtforms import ValidationError
from quasselflask.parsing.form import PasswordValidator


class TestPasswordValidator(TestCase):
    def _validate(self, str):
        class Dummy:
            data = str
            description = 'Test Field'
        self.validator(None, Dummy())

    def test_no_requirements(self):
        validate1 = PasswordValidator(min=-1, max=-1, required_regex=tuple(), message=None)
        validate2 = PasswordValidator(min=0, max=-1, required_regex=tuple(), message=None)

        # should all pass: no ValidationError exceptions
        for validate in (validate1, validate2):
            self.validator = validate
            self._validate('a')
            self._validate('Z')
            self._validate('4')
            self._validate('*')
            self._validate('abc123')
            self._validate('aBc123')
            self._validate(' ')
            self._validate('')
            self._validate('@%$*')
            self._validate('ja4yJAPIO#$N#HA)RNak34nyA4ha4hai;34ya)EHA34nalbgh$LJIkba:O@#${_)P#$UYi5464i57hya4UIABNe')

    def test_min_length(self):
        self.validator = PasswordValidator(min=6, max=-1, required_regex=tuple(), message=None)

        # should all pass: no ValidationError exceptions
        self._validate('aBc123')
        self._validate('@%$*$*^')
        self._validate('Password123')
        self._validate('ja4yJAPIO#$N#HA)RNak34nyA4ha4hai;34ya)EHA34nalbgh$LJIkba:O@#${_)P#$UYi5464i57hya4UIABNe')

        # should fail
        self.assertRaises(ValidationError, self._validate, 'a')
        self.assertRaises(ValidationError, self._validate, ' ')
        self.assertRaises(ValidationError, self._validate, '')

    def test_max_length(self):
        self.validator = PasswordValidator(min=-1, max=8, required_regex=tuple(), message=None)

        # should all pass: no ValidationError exceptions
        self._validate('Z')
        self._validate(' ')
        self._validate('')
        self._validate('aBc123')
        self._validate('@%$*v$*^')

        # should fail
        self.assertRaises(ValidationError, self._validate, 'Password123')
        self.assertRaises(ValidationError, self._validate,
                          'ja4yJAPIO#$N#HA)RNak34nyA4ha4hai;34ya)EHA34nalbgh$LJIkba:O@#${_)P#$UYi5464i57hya4UIABNe')

    def test_window_length(self):
        self.validator = PasswordValidator(min=6, max=8, required_regex=tuple(), message=None)

        # should all pass: no ValidationError exceptions
        self._validate('abc123')
        self._validate('aBc123!')
        self._validate('@%$*v$*^')

        # should fail
        self.assertRaises(ValidationError, self._validate, 'a')
        self.assertRaises(ValidationError, self._validate, ' ')
        self.assertRaises(ValidationError, self._validate, '')
        self.assertRaises(ValidationError, self._validate, 'Password123')
        self.assertRaises(ValidationError, self._validate,
                          'ja4yJAPIO#$N#HA)RNak34nyA4ha4hai;34ya)EHA34nalbgh$LJIkba:O@#${_)P#$UYi5464i57hya4UIABNe')

    def test_regexes(self):
        self.validator = PasswordValidator(min=6, max=8,
                                     required_regex=('[A-Z]', '[a-xy]', '[0-9]'), message=None)

        # should all pass: no ValidationError exceptions
        self._validate('Abc123')
        self._validate('aBC123!')
        self._validate('XAYbc314')

        # should fail
        self.assertRaises(ValidationError, self._validate, 'Abc12')
        self.assertRaises(ValidationError, self._validate, 'Abc123$%^')
        self.assertRaises(ValidationError, self._validate, 'abc123')
        self.assertRaises(ValidationError, self._validate, 'AbCdEf')
        self.assertRaises(ValidationError, self._validate, 'ABC123')
        self.assertRaises(ValidationError, self._validate, 'Password123')
