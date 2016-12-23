"""
Types used in database models or in Python glue logic.

This module should remain independent of SQLAlchemy. Bindings to SQLAlchemy should be made in files where models are
defined.

Project: Quasselflask
"""
from enum import Enum


class PermissionAccess(Enum):
    """
    Represents the access (allow or deny) of a permission row.

    This type implements __bool__ (True if allow, False if deny).

    This type implements the ~ (invert/bitwise not) operator; in this case, it inverts the permission value
    (allow↔deny).
    """
    deny = 0
    allow = 1

    @classmethod
    def from_name(cls, name: str):
        """ Get the PermissionAccess object corresponding to the name. Raises KeyError on failure."""
        return cls.__members__[name]

    def __bool__(self):
        return self is PermissionAccess.allow

    def __invert__(self):
        return PermissionAccess.deny if bool(self) else PermissionAccess.allow


class PermissionType(Enum):
    user = 0
    network = 1
    buffer = 2

    @classmethod
    def from_name(cls, name: str):
        """ Get the PermissionType object corresponding to the name. Raises KeyError on failure."""
        return cls.__members__[name]
