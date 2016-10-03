"""
QuasselFlask models and tools for the Quassel database (read-only). Reflection and automap provides some flexibility
in case of future quassel changes (especially schema changes that don't affect quasselflask's search parameters).

Project: QuasselFlask
"""

from enum import Enum

from flask_user import UserMixin
from sqlalchemy import MetaData
from sqlalchemy.ext.automap import automap_base

from quasselflask import db
from quasselflask.parsing.irclog import BacklogType


db_metadata = MetaData()
_db_tables = ['backlog', 'sender', 'buffer', 'network', 'quasseluser']
db_metadata.reflect(db.engine, only=_db_tables)
Base = automap_base(metadata=db_metadata)
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


class QfUser(Base, UserMixin):
    """
    Quasselflask-specific user table. This is used to login to Quasselflask and is distinct from a QuasselUser, used to
    log into Quassel and associated to IRC backlogs and connections.
    """
    __tablename__ = "qf_user"
    qfuserid = db.Column(db.Integer, primary_key=True)

    # Authentication
    username = db.Column(db.String(50), nullable=False, index=True, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')  # TODO: empty default? hashing?
    reset_password_token = db.Column(db.String(100), nullable=False, server_default='')

    # User email information
    email = db.Column(db.String(255), nullable=False, unique=True)
    confirmed_at = db.Column(db.DateTime())

    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='0')
    superuser = db.Column('is_superuser', db.Boolean(), nullable=False, server_default='0')

    permissions = db.relationship('QfPermissions', back_populates='qfuser')

    # For Flask-User: see UserMixin
    def get_id(self):
        return self.qfuserid

    def has_role(self, *specified_role_names):
        if 'superuser' in specified_role_names:
            return self.is_superuser
        return super().has_role(*specified_role_names)

    def has_roles(self, *requirements):
        """
        Pre-check the "superuser" role requirement, then pass on any other roles to the
        :param requirements:
        :return:
        """
        if self.is_superuser or 'superuser' not in self.requirements:
            new_reqs = tuple(req for req in requirements if req != 'superuser')
            return super().has_roles(*new_reqs)
        return False

    @property
    def is_superuser(self):  # to match the UserMixin API
        return self.superuser


class PermissionAccess(Enum):
    deny = 0
    allow = 1


class PermissionType(Enum):
    user = 0
    network = 1
    buffer = 2
    all = 15


class QfPermissions(Base):
    __tablename__ = "qf_permissions"
    __table_args__ = (
        db.CheckConstraint("""
        (type = 'all' and userid IS NULL and networkid IS NULL and bufferid IS NULL) OR
        (type = 'user' AND userid IS NOT NULL AND networkid IS NULL AND bufferid IS NULL) OR
        (type = 'network' AND userid IS NULL and networkid IS NOT NULL and bufferid IS NULL) OR
        (type = 'buffer' AND userid IS NULL AND networkid IS NOT NULL and bufferid IS NULL)
        """, name='typeCheck'),
    )
    qfpermid = db.Column(db.Integer, primary_key=True)

    qfuserid = db.Column(db.Integer, db.ForeignKey('qf_user.qfuserid', ondelete='CASCADE'), index=True)
    qfuser = db.relationship('QfUser', back_populates='permissions')

    # Access type: allow or deny?
    access = db.Column(db.Enum(PermissionAccess), nullable=False, server_default='deny')

    # what is being allowed/denied
    type = db.Column(db.Enum(PermissionType), nullable=False, server_default='all')

    userid = db.Column(db.Integer, db.ForeignKey('quasseluser.userid', ondelete='SET NULL'), nullable=True)
    quasseluser = db.relationship("QuasselUser")

    networkid = db.Column(db.Integer, db.ForeignKey('network.networkid', ondelete='SET NULL'), nullable=True)
    network = db.relationship("Network")

    bufferid = db.Column(db.Integer, db.ForeignKey('buffer.bufferid', ondelete='SET NULL'), nullable=True)
    buffer = db.relationship("Buffer")
