"""
Permissions model.

Project: Quasselflask
"""

from quasselflask.models.types import PermissionType


def compile_permissions(user):
    """
    Build the permissions structure.

    This structure represents the full permissions as a cascade, where the highest priority is at the end of the list.
    This is a reduction of a full tree with root note default, followed by user, network, and channel nodes at each
    subsequent level of depth (if each one is specified for each branch of the tree, e.g. default->network->channel
    is a possible branch if the quassel user is not explicitly specified as a permission.

    The below structure only represents the different tree depths, rather than the full tree.

    The first element is the default value for the user as a bare PermissionType object.
    The next elements are lists of QfPermission objects in increasing order of priority.

    Basic criteria for the sorting of permissions into this cascade:

    1. Permissions have a natural hierarchy of default_access -> user -> network -> buffer (channel).
    2. The top level (level 0) is always the default access for the current user.
    3. All elements of each level must alternate access value. For example, if default=deny, then all first-level
       elements must be 'allow'. This is because a first-level 'deny' element would already be applied by the default
       permission and is therefore redundant.
    4. Each permission should be placed in the first level in which none of its ancestors (in terms of hierarchy)
       is present (if it meets #3). This rule enables rule #3 to be defined per-level: for example, if default=deny,
       and network id=10 is allow and its user (id=3) is not specified, then network id=10 is inserted into the first
       level. However, if network id=10 is deny and user id=3 is allow, then the user is level 1 and the network is
       level 2: this way, the network and user cascade (network id=10 denied, but any other network from user id=3
       allowed).

    :param user: QfUser whose permissions to compile.
    :type user: quasselflask.models.models.QfUser
    :return: tuple whose elements correspond to each level described above (0: PermissionAccess, 1-3: [QfPermission])
    """
    users = tuple(perm for perm in user.permissions if perm.type == PermissionType.user)
    networks = tuple(perm for perm in user.permissions if perm.type == PermissionType.network)
    buffers = tuple(perm for perm in user.permissions if perm.type == PermissionType.buffer)

    perm_cascade = (user.access,  # level 0: default value
                    [],  # level 1: ~default permission
                    [],  # level 2: same as default permission
                    [],  # level 3: ~default permission
                    )
    perm_cascade_access = [user.access, ~user.access, user.access, ~user.access]

    for perm in users + networks + buffers:
        if perm.type is PermissionType.user:
            parent_userid = None
            parent_networkid = None
        elif perm.type is PermissionType.network:
            parent_userid = perm.network.userid
            parent_networkid = None
        elif perm.type is PermissionType.buffer:
            parent_userid = perm.buffer.network.userid
            parent_networkid = perm.buffer.network.networkid
        else:
            raise ValueError("Invalid argument 'type' attribute value")

        # check all levels against rule 3 and 4 - insert at the first level that satisfies those rules
        for level in range(1, 4):
            # check if types higher in hierarchy are present in this level
            parent_user_present = parent_userid is not None and \
                parent_userid in [p.get_id() for p in perm_cascade[level] if p.type is PermissionType.user]
            parent_network_present = parent_networkid is not None and \
                parent_networkid in [p.get_id() for p in perm_cascade[level] if p.type is PermissionType.network]

            if not parent_user_present and not parent_network_present:  # Rule 4
                if perm_cascade_access[level] == perm.access:  # Rule 3 - if not, discard
                    perm_cascade[level].append(perm)
                break
        else:  # didn't find a place to append it. Weird.
            raise ValueError("Specified permission can't be inserted "
                             "(??? Should not be possible! Permissions model changed?)")

    return perm_cascade
