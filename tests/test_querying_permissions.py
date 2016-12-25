"""
File description.

Project: Project Name
"""
from unittest import TestCase

import random

from quasselflask.permissions import make_cascaded_permissions, compile_permissions
from quasselflask.models.types import PermissionAccess as Access, PermissionType as Type


class MockPerm:
    _autoinc = 0

    def __init__(self, access: Access, type_: Type, id_: int,
                 parent_userid: int = None, parent_networkid: int = None):
        MockPerm._autoinc += 1
        self.qfpermid = MockPerm._autoinc
        self.access = access
        self.type = type_
        if self.type == Type.user:
            self.userid = id_
            self.user = MockObject(userid=id_)
        elif self.type == Type.network:
            self.networkid = id_
            self.network = MockObject(networkid=id_, userid=parent_userid)
            self.network.user = MockObject(userid=parent_userid)
        elif self.type == Type.buffer:
            self.bufferid = id_
            self.buffer = MockObject(bufferid=id_, networkid=parent_networkid)
            self.buffer.network = MockObject(networkid=parent_networkid, userid=parent_userid)
            self.buffer.network.user = MockObject(userid=parent_userid)
        else:
            raise ValueError("Invalid `type` passed: " + repr(type_))

    def get_target_str(self):
        if self.type == Type.user:
            return 'u{}'.format(self.userid)
        elif self.type == Type.network:
            return 'u{}n{}'.format(self.network.userid, self.networkid)
        elif self.type == Type.buffer:
            return 'u{}n{}b{}'.format(self.buffer.network.userid, self.buffer.networkid, self.bufferid)
        else:
            raise ValueError

    def __str__(self):
        return '{}{}'.format(self.get_target_str(), '+' if self.access is Access.allow else '#')

    def __repr__(self):
        return str(self)

    def get_id(self):
        if self.type == Type.user:
            return self.userid
        elif self.type == Type.network:
            return self.networkid
        elif self.type == Type.buffer:
            return self.bufferid
        else:
            raise ValueError

    def get_match_query(self):
        return self.get_target_str()

    def copy(self):
        if self.type == Type.user:
            id_ = self.userid
            parent_userid = None
            parent_networkid = None
        elif self.type == Type.network:
            id_ = self.networkid
            parent_userid = self.network.userid
            parent_networkid = None
        elif self.type == Type.buffer:
            id_ = self.bufferid
            parent_userid = self.buffer.network.userid
            parent_networkid = self.buffer.networkid
        else:
            raise ValueError
        return MockPerm(self.access, self.type, id_, parent_userid, parent_networkid)

    def __eq__(self, other):
        return isinstance(other, MockPerm) and self.type == other.type and self.userid == other.userid and \
               self.networkid == other.networkid and self.bufferid == other.bufferid and self.access == other.access

    def __lt__(self, other):
        if not isinstance(other, MockPerm):
            raise TypeError("unorderable types: {} < {}".format(type(self), type(other)))
        if self.type != other.type:
            return self.type.value < other.type.value
        else:
            return self.get_id() < other.get_id()

    def __le__(self, other):
        if not isinstance(other, MockPerm):
            raise TypeError("unorderable types: {} <= {}".format(type(self), type(other)))
        if self.type != other.type:
            return self.type.value < other.type.value
        else:
            return self.get_id() <= other.get_id()

    def __gt__(self, other):
        if not isinstance(other, MockPerm):
            raise TypeError("unorderable types: {} > {}".format(type(self), type(other)))
        if self.type != other.type:
            return self.type.value > other.type.value
        else:
            return self.get_id() > other.get_id()

    def __ge__(self, other):
        if not isinstance(other, MockPerm):
            raise TypeError("unorderable types: {} >= {}".format(type(self), type(other)))
        if self.type != other.type:
            return self.type.value > other.type.value
        else:
            return self.get_id() >= other.get_id()


class MockQfUser:
    _autoinc = 0

    def __init__(self, superuser: bool, access: Access, permissions: [MockPerm]):
        MockQfUser._autoinc += 1
        self.qfuserid = MockQfUser._autoinc
        self.access = access
        self.superuser = bool(superuser)
        self.permissions = permissions.copy()


class MockObject(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def and_(a, b):
    return "{} {} *".format(a, b)


def or_(a, b):
    return "{} {} +".format(a, b)


def not_(a):
    return "{} ¬".format(a)


class TestQueryingPermissions(TestCase):
    # FIXME: this test is unfortunately implementation-dependent:
    # - Boolean expressions aren't evaluated
    # - TRUE/FALSE aren't short-circuited
    # - AND and OR are commutative and De Morgan's theorem means there isn't a unique representation (canonical sum-of-
    #   products boolean expression could solve this)
    #
    # That seems too complex for a test. I feel like this entire solution, and its test, are too complex. =P
    #

    @staticmethod
    def make_permissions_filter_string(user):
        """ Returns reverse polish notation. """
        cascaded = make_cascaded_permissions(user)

        # Sort to ensure result order is consistent for a given permission set
        for level in (1, 2, 3):
            cascaded[level].sort()
        return compile_permissions(cascaded, and_, or_, not_, 'TRUE', 'FALSE')

    def setUp(self):
        # allow-all user
        self.allow_user = MockQfUser(False, Access.allow, [])

        # deny-all user
        self.deny_user = MockQfUser(False, Access.deny, [])

        # whitelist-based (default = deny)
        self.white_perms = []
        self.white_perms.append(MockPerm(Access.allow, Type.user, 1))

        self.white_perms.append(MockPerm(Access.deny, Type.network, 1, parent_userid=1))
        self.white_perms.append(MockPerm(Access.allow, Type.buffer, 1, parent_networkid=1, parent_userid=1))
        self.white_perms.append(MockPerm(Access.allow, Type.buffer, 2, parent_networkid=1, parent_userid=1))

        # This network is redundant (allow with parent user allow) and shouldn't appear in the final output
        self.white_perms.append(MockPerm(Access.allow, Type.network, 10, parent_userid=1))

        # userid=3 is absent here and network=2 is allow so it's not redundant
        self.white_perms.append(MockPerm(Access.allow, Type.network, 2, parent_userid=3))
        self.white_perms.append(MockPerm(Access.deny, Type.buffer, 7, parent_networkid=2, parent_userid=3))
        self.white_perms.append(MockPerm(Access.deny, Type.buffer, 8, parent_networkid=2, parent_userid=3))

        self.white_perms.append(MockPerm(Access.allow, Type.user, 2))

        self.white_perms.append(MockPerm(Access.deny, Type.network, 3, parent_userid=2))
        self.white_perms.append(MockPerm(Access.allow, Type.buffer, 3, parent_networkid=3, parent_userid=2))
        self.white_perms.append(MockPerm(Access.allow, Type.buffer, 4, parent_networkid=3, parent_userid=2))
        # This buffer is redundant (deny with parent network deny) and shouldn't appear in the final output
        self.white_perms.append(MockPerm(Access.deny, Type.buffer, 10, parent_networkid=3, parent_userid=2))

        self.white_perms.append(MockPerm(Access.deny, Type.network, 4, parent_userid=2))
        self.white_perms.append(MockPerm(Access.allow, Type.buffer, 5, parent_networkid=4, parent_userid=2))
        self.white_perms.append(MockPerm(Access.allow, Type.buffer, 6, parent_networkid=4, parent_userid=2))

        # only the channel is present in the hierarchy, and allowed; no network and user
        self.white_perms.append(MockPerm(Access.allow, Type.buffer, 9, parent_networkid=5, parent_userid=4))

        # This user is redundant (deny on a default of deny) and shouldn't appear in the final output
        self.white_perms.append(MockPerm(Access.deny, Type.user, 10))
        random.shuffle(self.white_perms)

        self.white_user = MockQfUser(False, Access.deny, self.white_perms)
        self.white_expect = (Access.deny,
                             {'u1+', 'u2+', 'u3n2+', 'u4n5b9+'},
                             {'u1n1#', 'u2n3#', 'u2n4#', 'u3n2b7#', 'u3n2b8#'},
                             {'u1n1b1+', 'u1n1b2+', 'u2n3b3+', 'u2n3b4+', 'u2n4b5+', 'u2n4b6+'}
                             )

        # blacklist-based (default = allow)
        self.black_perms = [perm.copy() for perm in self.white_perms]
        for perm in self.black_perms:
            perm.access = ~perm.access  # black_perms is an exact inversion of white_perms

        self.black_user = MockQfUser(False, Access.allow, self.black_perms)
        self.black_expect = (Access.allow,
                             {'u1#', 'u2#', 'u3n2#', 'u4n5b9#'},
                             {'u1n1+', 'u2n3+', 'u2n4+', 'u3n2b7+', 'u3n2b8+'},
                             {'u1n1b1#', 'u1n1b2#', 'u2n3b3#', 'u2n3b4#', 'u2n4b5#', 'u2n4b6#'}
                             )

    def test_sorted_permissions_white(self):
        cascaded = make_cascaded_permissions(self.white_user)
        expected = self.white_expect
        self.assertIs(cascaded[0], expected[0], 'level 0 access mismatch')
        for level in range(1, 3+1):
            compiled_set = set(repr(perm) for perm in cascaded[level])
            expected_set = expected[level]
            self.assertEqual(expected_set, compiled_set, 'level {} mismatch'.format(level))

    def test_sorted_permissions_black(self):
        cascaded = make_cascaded_permissions(self.black_user)
        expected = self.black_expect
        self.assertIs(cascaded[0], expected[0], 'level 0 access mismatch')
        for level in range(1, 3+1):
            compiled_set = set(repr(perm) for perm in cascaded[level])
            expected_set = expected[level]
            self.assertEqual(expected_set, compiled_set, 'level {} mismatch'.format(level))

    def test_filter_allow_all(self):
        expected = 'TRUE'
        result = self.make_permissions_filter_string(self.allow_user)
        self.assertEqual(expected, result, 'mismatch boolean strings')

    def test_filter_deny_all(self):
        expected = 'FALSE'
        result = self.make_permissions_filter_string(self.deny_user)
        self.assertEqual(expected, result, 'mismatch boolean strings')

    def test_filter_white_user(self):
        expected = 'FALSE u1 u2 + u3n2 + u4n5b9 + + u1n1 u2n3 + u2n4 + u3n2b7 + u3n2b8 + ¬ * ' \
                   'u1n1b1 u1n1b2 + u2n3b3 + u2n3b4 + u2n4b5 + u2n4b6 + +'
        result = self.make_permissions_filter_string(self.white_user)
        print(result)
        self.assertEqual(expected, result, 'mismatch boolean strings')

    def test_filter_black_user(self):
        expected = 'TRUE u1 u2 + u3n2 + u4n5b9 + ¬ * u1n1 u2n3 + u2n4 + u3n2b7 + u3n2b8 + + ' \
                   'u1n1b1 u1n1b2 + u2n3b3 + u2n3b4 + u2n4b5 + u2n4b6 + ¬ *'
        result = self.make_permissions_filter_string(self.black_user)
        print(result)
        self.assertEqual(expected, result, 'mismatch boolean strings')
