"""
Converter methods for database model classes into other formats.

Project: QuasselFlask
"""

import sqlalchemy.orm

from quasselflask.models.models import QfUser, QfPermission


def convert_permissions_lists(db_quasselusers: sqlalchemy.orm.query.Query,
                              db_networks: sqlalchemy.orm.query.Query,
                              db_buffers: sqlalchemy.orm.query.Query):
    return {
        'quasselusers': convert_quasselusers(db_quasselusers),
        'networks': convert_networks(db_networks),
        'buffers': convert_buffers(db_buffers)
    }


def convert_user_permissions(user: QfUser):
    return {
        "default": user.access.name,
        "permissions": [{
            "qfpermid": perm.qfpermid,
            "access": perm.access.name,
            "type": perm.type.name if (perm.type.name != 'user') else 'quasseluser',
            "id": perm.get_id()
        } for perm in user.permissions]
    }


def convert_quasselusers(db_quasselusers: sqlalchemy.orm.query.Query):
    """
    Convert Quasseluser database records into a list of dicts:

    .. code-block:: python
        {
          "id": 0,
          "name": "user0"
        }

    :param db_quasselusers: SQL query for QuasselUser objects. This method will iterate over this object (consumes
        sqlalchemy cursors).
    :return:
    """
    list_quasselusers = []
    for quasseluser in db_quasselusers:
        list_quasselusers.append({'id': quasseluser.userid, 'name': quasseluser.username})
    return list_quasselusers


def convert_networks(db_networks: sqlalchemy.orm.query.Query):
    """
    Convert network database records into a list of dicts:

    .. code-block:: python
        {
            "id": 0,
            "quasseluserid": 0,
            "name": "Snoonet"
        }

    :param db_networks: SQL query for Network objects. This method will iterate over this object (consumes
        sqlalchemy cursors).
    :return:
    """
    list_networks = []
    for network in db_networks:
        list_networks.append({
            'id': network.networkid,
            'name': network.networkname,
            'quasseluserid': network.userid
        })
    return list_networks


def convert_buffers(db_buffers: sqlalchemy.orm.query.Query):
    """
    Convert buffer database records into a list of dicts:

    .. code-block:: python
        {
          "id": 0,
          "networkid": 0,
          "name": "#techsupport"
        },

    :param db_buffers: SQL query of Buffer objects. This method will iterate over this object (consumes
        sqlalchemy cursors).
    :return:
    """
    list_buffers = []
    for buffer in db_buffers:
        list_buffers.append({
            'id': buffer.bufferid,
            'networkid': buffer.networkid,
            'name': buffer.buffername
        })
    return list_buffers
