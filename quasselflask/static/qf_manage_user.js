/******************************************************************************
 * File: qf_manage_user.js
 * QuasselFlask - Log Search Utility for Quassel Postgresql Database
 * https://github.com/Laogeodritt/quasselflask
 *
 * Dependencies:
 * * jQuery >= 3.0.0
 * * Dojo >= 1.10.4
 *
 * Licensed under the GNU Public Licence, version 3
 * <https://www.gnu.org/licenses/gpl-3.0.en.html>
 *****************************************************************************/

/*
 * Bootstrap
 */
var FilteringSelect;
var Memory;
var fsBuffer, fsNetwork, fsQuasseluser;
var current_permissions = {
    "permissions": [],
    "default": ""
};

require([
        'dijit/form/FilteringSelect',
        'dojo/store/Memory'
], function(fs, m) {
    FilteringSelect = fs;
    Memory = m;
    preprocessPermissionData();
    bootstrapPermissionSelect();
    bootstrapPermissionForm();
});


/*
 * Permission Data
 */

/**
 * Find a permission datum by its id.
 * @param perm_type "quasselusers", "networks" or "channels"
 * @param id Numeric ID to search for.
 * @returns {object} Result, or undefined if no results.
 */
function findPermissionDataById(perm_type, id) {
    return $.grep(PERMISSION_DATA[perm_type], function(o) { return o.id === id; })[0];
}

/**
 * Finds a current user permission datum by its type and ID.
 * @param perm_type "quasselusers", "networks" or "channels"
 * @param id Numeric ID to search for.
 * @returns {int} The index (in current_permissions.permissions) of the found object, or -1 if none found.
 */
function indexOfUserPermissionById(perm_type, id) {
    var indices = $.map(current_permissions.permissions, function(o, index) {
        if (o.type == perm_type && o.id == id) return index;
    });

    if (indices.length > 0) return indices[0];
    else return -1;
}


/**
 * Preprocess permission data.
 *
 * This denormalises foreign key references in PERMISSION_DATA, e.g.
 * by including the quasseluserid in the buffers data, because the dijit.form.FilteringSelect
 * widget does not have simple filtering functionality on normalised data.
 *
 * This function also generates HTML labels for each item.
 */
function preprocessPermissionData() {
    PERMISSION_DATA.quasselusers.forEach(function(quasseluser) {
        quasseluser.label = quasseluser.name;
    });
    PERMISSION_DATA.networks.forEach(function(network) {
        network.label = network.name + '<span class="label-extra quasseluser">' +
                        findPermissionDataById('quasselusers', network.quasseluserid).name + '</span>';
    });
    PERMISSION_DATA.buffers.forEach(function(buffer) {
        buffer.quasseluserid = findPermissionDataById('networks', buffer.networkid).quasseluserid;
        buffer.label = buffer.name + '<span class="label-extra network">' +
                findPermissionDataById('networks', buffer.networkid).name + '</span><span class="label-extra quasseluser">' +
                findPermissionDataById('quasselusers', buffer.quasseluserid).name + '</span>';
    });
}


/*
 * Permission selector
 */

function bootstrapPermissionSelect() {
    var bufferStore = new Memory({
        identifier: 'id',
        label: 'label',
        data: PERMISSION_DATA.buffers
    });
    fsBuffer = new FilteringSelect({
        id: "combobox-buffer",
        name: "bufferid",
        labelAttr: "label",
        labelType: "html",
        placeholder: "channel",
        store: bufferStore,
        searchAttr: "name",
        required: false,
        query: {networkid: /.*/, quasseluserid: /.*/},
        onChange: function(buffer) {
            console.log("fsBuffer.onChange(" + (this.item? this.item.name : 'undefined') + ")");
            onChangeBuffer(this.item);
        }
    }, "combobox-buffer");

    var networkStore = new Memory({
        identifier: 'id',
        label: 'name',
        data: PERMISSION_DATA.networks
    });
    fsNetwork = new FilteringSelect({
        id: "combobox-network",
        name: "networkid",
        labelAttr: "label",
        labelType: "html",
        placeholder: "network",
        store: networkStore,
        searchAttr: "name",
        required: false,
        query: {quasseluserid: /.*/},
        onChange: function(network) {
            console.log("fsNetwork.onChange(" + (this.item? this.item.name : 'undefined') + ")");
            onChangeNetwork(this.item);
        }
    }, "combobox-network");

    var quasseluserStore = new Memory({
        identifier: 'id',
        label: 'name',
        data: PERMISSION_DATA.quasselusers
    });
    fsQuasseluser = new FilteringSelect({
        id: "combobox-quasseluser",
        name: "userid",
        placeholder: "quassel user",
        store: quasseluserStore,
        searchAttr: "name",
        required: false,
        onChange: function(quasseluser) {
            console.log("fsQuasseluser.onChange(" + (this.item? this.item.name : 'undefined') + ")");
            onChangeQuasselUser(this.item);
        }
    }, "combobox-quasseluser");

    $("#btn-permission-reset").on('clock', function() {
        fsBuffer.query.networkid = fsBuffer.query.quasseluserid = /.*/;
        fsNetwork.query.quasseluserid = /.*/;
    });

    fsBuffer.startup();
    fsNetwork.startup();
    fsQuasseluser.startup();

    $('[widgetid="combobox-quasseluser"] .dijitValidationIcon').on('click', function() {
        fsQuasseluser.set("value", null);
    });
    $('[widgetid="combobox-network"] .dijitValidationIcon').on('click', function() {
        fsNetwork.set("value", null);
    });
    $('[widgetid="combobox-buffer"] .dijitValidationIcon').on('click', function() {
        fsBuffer.set("value", null);
    });
}


/**
 * When the buffer selection changes in the permission select:
 *
 * * Set the corresponding quasseluser and network.
 * * Filter the buffer list according to the set network.
 *
 * @param buffer
 */
function onChangeBuffer(buffer) {
    var quasseluserbox = dijit.byId("combobox-quasseluser");
    var networkbox = dijit.byId("combobox-network");
    var bufferbox = dijit.byId("combobox-buffer");

    bufferbox.query.networkid = buffer ? buffer.id : /.*/;
    bufferbox.query.quasseluserid = /.*/;

    if(buffer) networkbox.set("value", buffer.networkid);

    if(buffer) quasseluserbox.set("value", buffer.quasseluserid);
}


/**
 * When the network selection changes in the permission select:
 *
 * * Set the corresponding quasseluser.
 * * Filter the network list according to the set quasseluser.
 * * Filter the buffer according to the set network.
 * * If the currently-set buffer doesn't correspond to the set network, unset the buffer.
 *
 * @param network
 */
function onChangeNetwork(network) {
    var quasseluserbox = dijit.byId("combobox-quasseluser");
    var networkbox = dijit.byId("combobox-network");
    var bufferbox = dijit.byId("combobox-buffer");

    if(network) quasseluserbox.set("value", network.quasseluserid);

    networkbox.query.quasseluserid = network ? network.quasseluserid : /.*/;

    bufferbox.query.networkid = network ? network.id : /.*/;
    bufferbox.query.quasseluserid = /.*/;
    if(bufferbox.item && network && bufferbox.item.networkid !== network.id) {
        bufferbox.set("value", null);
    }
}


/**
 * When the quasseluser selection changes in the permission select:
 *
 * * Filter the network list according to the set quasseluser.
 * * If the currently set network doesn't correspond to the set quasseluser, unset the network.
 * * Filter the buffer according to the set network. (But not if a network is still set - that is the more restrictive
 *   filter condition).
 * * If the buffer doesn't correspond to the set quasseluser, unset the buffer.
 *
 * @param quasseluser
 */
function onChangeQuasselUser(quasseluser) {
    var quasseluserbox = dijit.byId("combobox-quasseluser");
    var networkbox = dijit.byId("combobox-network");
    var bufferbox = dijit.byId("combobox-buffer");

    networkbox.query.quasseluserid = quasseluser ? quasseluser.id : /.*/;
    if(networkbox.item && quasseluser && networkbox.item.quasseluserid !== quasseluser.id) {
        networkbox.set("value", null);
    }

    if(!networkbox.item) { // only set filter if not already set from a valid `network` selection
        bufferbox.query.networkid = /.*/;
        bufferbox.query.quasseluserid = quasseluser ? quasseluser.id : /.*/;
    }
    if(bufferbox.item && quasseluser && bufferbox.item.quasseluserid !== quasseluser.id) {
        bufferbox.set("value", null);
    }
}

function bootstrapPermissionForm() {
    $("#user-permissions-submit").on("click", submitPermissions);
    $("#btn-default-allow").on("click", setAllowDefault);
    $("#btn-default-deny").on("click", setDenyDefault);
    current_permissions = USER_PERMISSIONS;
    current_permissions.permissions.forEach(function(perm) {
        perm.action = "";
    });
    showPermissions();
}

/**
 * In-place permission sort. Sorts by type ("channel", "network", "quasseluser"), then
 * by ID.
 *
 * @param perms Permissions object with property 'permissions', containing a list of permissions
 * objects.
 */
function sortPermissions(perms) {
    var typeSort = ['buffer', 'network', 'quasseluser'];
    perms.permissions.sort(function(a, b) {
        if (a.type == b.type) {
            return a.id - b.id;
        }
        else {
            var aTypeSort = typeSort.indexOf(a.type);
            var bTypeSort = typeSort.indexOf(b.type);
            if (aTypeSort == -1) {
                console.log("Invalid type " + a.type + " for qfpermid " + a.qfpermid);
                return +1;
            }
            else if (bTypeSort == -1) {
                console.log("Invalid type " + b.type + " for qfpermid " + b.qfpermid);
                return -1;
            }
            else return aTypeSort - bTypeSort;
        }
    });
}

function showPermissions() {
    var $target = $("#user-permission-display");
    $target.empty();
    sortPermissions(current_permissions);
    current_permissions.permissions.forEach(function(perm) {
        if(perm.action == 'remove') return; // do nothing
        console.log("showPermissions: " + perm.access + " " + perm.type + " " + perm.id);
        var $permButton = createPermissionButton(perm.qfpermid, perm.type, perm.id, perm.access);
        $target.append($permButton);
    });

    var $defaultButton = createPermissionButton(null, 'default', null, current_permissions.default);
    $target.append($defaultButton);
}

/**
 * @param qfpermid Permission record ID. If not specified, -1.
 * @param type "quasseluser", "network", "buffer" or "default"
 * @param id ID of the object to which the permission applies. This ID is for the specified `type`.
 * @param access "allow" or "deny".
 */
function createPermissionButton(qfpermid, type, id, access) {
    if (qfpermid === 'undefined' || qfpermid === null) {
        qfpermid = -1;
    }
    if(id === 'undefined' || id === null) {
        id = -1;
    }
    var $button = $('<button>');
    $button.attr('type', 'button');
    $button.addClass('btn-perm');
    $button.data('permission-access', access);
    $button.addClass('permission-access-' + access);

    if(type !== 'default') {
        var permData = findPermissionDataById(type + 's', id);
        $button.html(permData.label);
    }
    else {
        $button.html('(Default)');
    }
    $button.data('permission-qfpermid', qfpermid);
    $button.addClass('permission-qfpermid-' + qfpermid);
    $button.data('permission-type', type);
    $button.addClass('permission-type-' + type);
    $button.data('permission-id', id);
    $button.addClass('permission-id-' + id);
    if(type != 'default') $button.on('click', removePermissionFromButton);
    else                  $button.on('click', toggleDefault);
    return $button;
}

function setAllowDefault() {
    setDefault('allow');
}

function setDenyDefault() {
    setDefault('deny');
}

function toggleDefault() {
    var access;
    if(current_permissions.default == 'deny') current_permissions.default = 'allow';
    else current_permissions.default = 'deny';
    setDefault(current_permissions.default);
}

function setDefault(access) {
    if (access !== 'allow' && access !== 'deny' && access != null && access !== 'undefined') {
        console.error('Invalid value for "access": ' + access);
        return;
    }

    current_permissions.default = access;

    var $target = $('#user-permission-display');
    $target.find('.permission-type-default')
            .removeClass('permission-access-allow permission-access-deny')
            .addClass('permission-access-' + access)
            .data('permission-access', access);
}

function removePermissionFromButton() {
    var $this = $(this);
    var index = indexOfUserPermissionById($this.data('permission-type'), $this.data('permission-id'));
    if (index >= 0) {
        current_permissions.permissions[index].action = 'remove';
    }
    $this.fadeOut(function() {
        $this.remove();
    });
    // TODO: load into the permission selector
}

function submitPermissions() {
    console.log("submitPermissions");
}
