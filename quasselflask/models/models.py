"""
QuasselFlask models and tools for the Quassel database (read-only). Reflection and automap provides some flexibility
in case of future quassel changes (especially schema changes that don't affect quasselflask's search parameters).

Project: QuasselFlask
"""

from flask_login import AnonymousUserMixin
from flask_user import UserMixin
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Query

from quasselflask import db
from quasselflask.models.types import PermissionAccess, PermissionType
from quasselflask.parsing.irclog import BacklogType

_db_tables = ['backlog', 'sender', 'buffer', 'network', 'quasseluser']
db.metadata.reflect(db.engine, only=_db_tables)
Base = automap_base(metadata=db.metadata)
Base.prepare()

Backlog = Base.classes.backlog
Sender = Base.classes.sender
Buffer = Base.classes.buffer
Network = Base.classes.network
QuasselUser = Base.classes.quasseluser


def __repr_backlog(self):
    try:
        type_str = BacklogType(self.type).name
    except IndexError:
        type_str = 'Unknown'
    return "[{:%Y-%m-%d %H:%M:%S}] [{}]<{}:{}> {}".format(self.time, type_str, self.buffer.buffername,
                                                          self.sender.sender, self.message)

Backlog.__repr__ = __repr_backlog


class QfUser(db.Model, UserMixin):
    """
    Quasselflask-specific user table. This is used to login to Quasselflask and is distinct from a QuasselUser, used to
    log into Quassel and associated to IRC backlogs and connections.
    """
    __tablename__ = "qf_user"
    qfuserid = db.Column(db.Integer, primary_key=True)

    # Authentication
    username = db.Column(db.String(50), nullable=False, index=True, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')
    reset_password_token = db.Column(db.String(100), nullable=False, server_default='')

    # User email information
    email = db.Column(db.String(255), nullable=False, unique=True)
    confirmed_at = db.Column(db.DateTime())

    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='0')
    superuser = db.Column('is_superuser', db.Boolean(), nullable=False, server_default='0')

    # User settings
    themeid = db.Column(db.Integer, nullable=False, server_default='0')

    # default access (allow|deny), when no specific permission is specified
    access = db.Column(db.Enum(PermissionAccess), nullable=False, server_default='deny')

    permissions = db.relationship('QfPermission', back_populates='qfuser', lazy='joined')

    # For Flask-User: see UserMixin
    def get_id(self):
        return self.qfuserid

    def has_role(self, *role_names):
        """
        Checks if the user has any of the role_names. This override does a special check for the 'superuser'
        role, which is stored as a separate bit from Flask_User's ``roles`` attribute.
        :param role_names:
        :return:
        """
        return (self.is_superuser and 'superuser' in role_names) or super(QfUser, self).has_role(*role_names)

    def has_roles(self, *requirements):
        """
        Checks if the user has all the roles in ``requirements``. This override does a special check for the 'superuser'
        role, which is stored as a separate bit from Flask_User's ``roles`` attribute, and passes any other roles
        back to the superclass method.
        :param requirements:
        :return:
        """
        residual_requirements = tuple(req for req in requirements if req != 'superuser')
        return (self.is_superuser or 'superuser' not in requirements) and \
            (not residual_requirements or super(QfUser, self).has_roles(*residual_requirements))

    @property
    def is_superuser(self):  # to match the UserMixin API
        return self.superuser

    def __repr__(self):
        return '<QfUser {}{}{}>'.format(
            self.username,
            '[su]' if self.is_superuser else '', '[disabled]' if not self.active else '')


class QfPermission(db.Model):
    """
    Table defining the permissions of a Quasselflask user. Permissions define what a user can search in terms of
    quassel users, networks, and channels. A user's permissions are defined by:

    1. an "allow all" or "deny all" permission (required);
    2. One or more rules allowing specific users, networks or buffers.

    The rules are applied in the following order:

    1. "allow all" or "deny all"
    2. quassel user rules
    3. network rules
    4. buffer rules

    For example, you could have the rules:

    1. deny all
    2. allow quassel user 'user1'
    3. deny buffer '##secret-channel'

    This would give the user access to all of logs of the user 'user1', except ##secret-channel.

    The attribute ``access`` defines whether a rule is allow or deny; ``type`` defines whether it refers to "all",
    "user" (quassel user), "network" or "buffer" (channel) restrictions. For "all" type, the ``userid``,
    ``networkid`` and ``bufferid`` columns must be NULL; for other types, only the column corresponding to the type must
    be non-NULL.

    Note: userid, networkid, bufferid do not have relationships as QfUser/QfPermission need to use Flask-SQLAlchemy
    for Flask-User compatibility, but the reflected Quassel classes are direct SQLAlchemy using a different
    declarative Base. This is an issue to address.
    """
    __tablename__ = "qf_permission"
    __table_args__ = (
        db.CheckConstraint("""
        (type = 'user' AND userid IS NOT NULL AND networkid IS NULL AND bufferid IS NULL) OR
        (type = 'network' AND userid IS NULL and networkid IS NOT NULL and bufferid IS NULL) OR
        (type = 'buffer' AND userid IS NULL AND networkid IS NULL and bufferid IS NOT NULL)
        """, name='typeCheck'),
    )
    qfpermid = db.Column(db.Integer, primary_key=True)

    qfuserid = db.Column(db.Integer, db.ForeignKey('qf_user.qfuserid', ondelete='CASCADE'), index=True)
    qfuser = db.relationship('QfUser', back_populates='permissions')

    # Access type: allow or deny?
    access = db.Column(db.Enum(PermissionAccess), nullable=False, server_default='deny')

    # what is being allowed/denied
    type = db.Column(db.Enum(PermissionType), nullable=False)

    userid = db.Column(db.Integer, db.ForeignKey('quasseluser.userid', ondelete='CASCADE'), nullable=True)
    user = db.relationship(QuasselUser)

    networkid = db.Column(db.Integer, db.ForeignKey('network.networkid', ondelete='CASCADE'), nullable=True)
    network = db.relationship(Network)

    bufferid = db.Column(db.Integer, db.ForeignKey('buffer.bufferid', ondelete='CASCADE'), nullable=True)
    buffer = db.relationship(Buffer)

    def __init__(self, access: PermissionAccess, type_: PermissionType, id_: int):
        """
        Create a new permission. Add this to the ``QfUser.permissions`` list for the user.
        :param access:
        :param type_:
        :param id_:
        """
        self.access = access
        self.type = type_
        if self.type == PermissionType.user:
            self.userid = id_
        elif self.type == PermissionType.network:
            self.networkid = id_
        elif self.type == PermissionType.buffer:
            self.bufferid = id_
        else:
            raise ValueError("Invalid `type` passed: " + repr(type_))

    def get_id(self) -> int:
        """
        Gets the ID corresponding to the permission's `type`.
        :return:
        """
        if self.type == PermissionType.user:
            return self.userid
        elif self.type == PermissionType.network:
            return self.networkid
        elif self.type == PermissionType.buffer:
            return self.bufferid
        else:
            raise ValueError("Invalid `type`: " + repr(self.type))

    def get_tuple(self) -> tuple:
        """
        Return a tuple containing (PermissionType, int id, PermissionAccess, QfPermission).
        Last element is the current object as a back-reference.
        :return:
        """
        return self.type, self.get_id(), self.access, self

    def get_match_query(self) -> Query:
        """
        Return a query that matches this permission's target (user, network or buffer) by column in that object's table
        (User, Network or Buffer classes). The query can be passed to a Query object's filter() method.

        WARNING: IF THIS PERMISSION'S ACCESS IS 'DENY', THIS METHOD STILL RETURNS A QUERY THAT MATCHES THE
        USER/NETWORK/BUFFER. IT DOES NOT EXCLUDE IT.

        :return:
        """
        if self.type == PermissionType.user:
            return QuasselUser.userid == self.userid
        elif self.type == PermissionType.network:
            return Network.networkid == self.networkid
        elif self.type == PermissionType.buffer:
            return Buffer.bufferid == self.bufferid

    def __repr__(self):
        if self.type == PermissionType.user:
            id_ = self.userid
        elif self.type == PermissionType.network:
            id_ = self.networkid
        elif self.type == PermissionType.buffer:
            id_ = self.bufferid
        else:
            id_ = None
        return '<QfPermission:{0:<5s}:{1:<7}:{2:d}>'.format(self.access.name, self.type.name, id_)


class QfAnonymousUserMixin(AnonymousUserMixin):
    @property
    def is_superuser(self):
        return False

    @property
    def themeid(self):
        from quasselflask import app
        return app.config.get('QF_DEFAULT_THEME', 0)


def qf_create_all():
    """
    Create all QuasselFlask-related tables and types.
    :return:
    """
    db.create_all()


def qf_drop_all():
    """
    Drops all QuasselFlask-related tables types. Does not drop Quassel tables.

    The connected PostgreSQL user must be owner (or member to the owner group) of the table to drop it.
    :return:
    """
    db.metadata.drop_all(bind=db.engine, tables=[QfUser.__table__, QfPermission.__table__], checkfirst=True)
    db.Enum(PermissionAccess).drop(db.engine, checkfirst=True)
    db.Enum(PermissionType).drop(db.engine, checkfirst=True)
