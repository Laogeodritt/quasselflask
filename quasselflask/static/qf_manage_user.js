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

/***********************
 * BOOTSTRAP
 ***********************/
var FilteringSelect;
var Memory;
var fsBuffer, fsNetwork, fsQuasseluser;
var permissionData, userPermissions;

require([
        'dijit/form/FilteringSelect',
        'dojo/store/Memory'
], function(fs, m) {
    FilteringSelect = fs;
    Memory = m;
    if(typeof QF_MANAGE_USER_PERMISSION_DISABLED === 'undefined' && !QF_MANAGE_USER_PERMISSION_DISABLED)
    {
        permissionData = new PermissionData(PERMISSION_DATA);
        bootstrapPermissionSelect();
        bootstrapPermissionForm();
    }
});


/***********************
 * CLASSES
 ***********************/
/**
 * Preprocessor and interface for permission UI data.
 *
 * The constructor denormalises foreign key references in PERMISSION_DATA, e.g.
 * by including the quasseluserid in the buffers data, because the dijit.form.FilteringSelect
 * widget does not have simple filtering functionality on normalised data.
 *
 * The constructor also generates HTML labels for each item.
 *
 * @param data The data structure as provided by the server. See documentation for views.admin_manage_user on the
 * server side.
 * @constructor
 */
function PermissionData(data) {
    // properties
    this._data = data;
    this._type_subst = {
        'buffer': 'buffers',
        'channel': 'buffers',
        'channels': 'buffers',
        'network': 'networks',
        'user': 'quasselusers',
        'quasseluser': 'quasselusers'
    };

    // methods

    /**
     * Given a type string, return the property supported by this._data.
     * @param type_ An input type string.
     * @returns {string}
     * @private
     */
    this._getCanonicalType = function(type_) {
        return type_ in this._type_subst ? this._type_subst[type_] : type_;
    };

    /**
     *
     * @param type_
     * @returns {{id: number, name: string, label: string, quasseluserid: number, networkid: number}|null}
     */
    this.getType = function(type_) {
        var typeProp = this._getCanonicalType(type_);
        return (typeProp in this._data) ? this._data[typeProp] : null;
    };

    /**
     * Find a permission datum by its id. Returns one result, or null if no results. Result properties 'quasseluserid'
     * and 'networkid' do not exist for quasseluser perm_type; 'networkid' does not exist for network perm_type.
     * @param perm_type "quasselusers", "networks" or "channels"
     * @param id_ Numeric ID to search for.
     * @returns {{id: number, name: string, label: string, quasseluserid: number, networkid: number}|null}
     */
    this.findById = function(perm_type, id_) {
        var typeProp = this._getCanonicalType(perm_type);
        if(typeProp in this._data && typeof id_ !== 'undefined' && id_ !== null) {
            var results = $.grep(this._data[typeProp], function(o, index) { return o.id === id_; });
            return (results.length > 0) ? results[0] : null;
        }
        else {
            console.error('permissionData.findById: invalid arguments: ' + perm_type + ", " + id_);
            return null;
        }
    };

    /**
     * Same as findById, but returns the index of the permission data within its type list.
     * @param perm_type
     * @param id_
     * @returns {number|null}
     */
    this.findIndexById = function(perm_type, id_) {
        var typeProp = this._getCanonicalType(perm_type);
        if(typeProp in this._data && typeof id_ !== 'undefined' && id_ !== null) {
            var results = $.map(this._data[typeProp], function(o, index) { if (o.id === id_) return index; });
            return (results.length > 0) ? results[0] : null;
        }
        else {
            console.error('permissionData.findIndexById: invalid arguments: ' + perm_type + ", " + id_);
            return null;
        }
    };

    // constructor
    if (!('quasselusers' in this._data && 'networks' in this._data && 'buffers' in this._data)) {
        throw new Error('PermissionData(): missing property in data');
    }

    // preprocess - preparation of server-provided data for use here
    this._data.quasselusers.forEach(function(quasseluser) {
        quasseluser.label = quasseluser.name;
    }, this);
    this._data.networks.forEach(function(network) {
        network.label = network.name + '<span class="label-extra quasseluser">' +
                this.findById('quasselusers', network.quasseluserid).name + '</span>';
    }, this);
    this._data.buffers.forEach(function(buffer) {
        buffer.quasseluserid = this.findById('networks', buffer.networkid).quasseluserid;
        buffer.label = buffer.name + '<span class="label-extra network">' +
                this.findById('networks', buffer.networkid).name + '</span><span class="label-extra quasseluser">' +
                this.findById('quasselusers', buffer.quasseluserid).name + '</span>';
    }, this);
}

/**
 * Backend representation of user permissions. Does not handle UI functions.
 *
 * @param data The data object provided by the server. Stored by reference, not copied.
 * @constructor
 */
function UserPermissions(data) {
    var this_ = this;
    if (!('default' in data && 'permissions' in data)) {
        throw new Error('UserPermissions: invalid argument object, missing properties');
    }

    // properties
    this._default = data.default;
    this._perms = data.permissions;

    // methods
    /**
     * Default access.
     * @returns {string} 'allow' or 'deny'
     */
    this.getDefault = function() { return this._default; };

    /**
     * Get a permission by index.
     * @param index Index
     * @returns {*}
     */
    this.get = function(index) { return this._perms[index]; };

    Object.defineProperty(this, "length", {
        get: function() { return this_._perms.length; }
    });

    Object.defineProperty(this, "perms", {
        get: function() { return this_._perms; }
    });

    Object.defineProperty(this, "default", {
        get: function() { return this_._default; }
    });

    /**
     * Iterate and call a method on all permission records (except default).
     * This is a wrapper for Javascript's Array.forEach().
     * @param callback Function, same as Array.forEach
     * @param this_reference The `this` keyword will be set to this when calling the callback.
     */
    this.forEach = function(callback, this_reference) { this._perms.forEach(callback, this_reference); };

    /**
     * Finds an active (action property is not "removed") user permission record by type and ID. If multiple are found,
     * a warning is logged and the first result is returned.
     * @param type_ "quasselusers", "networks" or "channels"
     * @param id_ Numeric ID to search for.
     * @returns {number} Index (in current_permissions.permissions) of the found object, or -1 if none found.
     */
    this.find = function(type_, id_) {
        var indices = $.map(this._perms, function(o, index) {
            if (o.type == type_ && o.id == id_ && o.action !== 'remove') return index;
        });
        if(indices.length > 1) console.warn('find(' + type_ + ', ' + id_ + '): multiple results');
        return (indices.length > 0) ? indices[0] : -1;
    };

    /**
     * Finds all current user permission records by type and ID. This includes action:"removed" records.
     * @param type_ "quasselusers", "networks" or "channels"
     * @param id_ Numeric ID to search for.
     * @returns {number[]} List of indices of the found object. Can be empty.
     */
    this.findAll = function(type_, id_) {
        return $.map(this._perms, function(o, index) {
            if (o.type == type_ && o.id == id_) return index;
        });
    };

    /**
     * Convenience method. Toggles the default access value from allow to deny or vice-versa.
     * (If the current value is invalid, sets 'deny').
     */
    this.toggleDefault = function() {
        if(this.getDefault() == 'deny') this.setDefault('allow');
        else this.setDefault('deny');
    };

    this.setDefault = function(access) {
        if(access !== 'allow' && access !== 'deny') {
            throw new Error('Invalid value for "access": ' + access);
        }
        this._default = access;
    };

    this.add = function(addPerm) {
        userPermissions.remove(addPerm.type, addPerm.id);
        this._perms.push(addPerm);
        this._perms.sort(UserPermissions.compare);
    };

    /**
     * Remove permission from the current set
     * @param type_ One of "buffer", "network", or "quasseluser".
     * @param id_ ID of the buffer/network/user.
     */
    this.remove = function(type_, id_) {
        var indices = this.findAll(type_, id_);
        indices.forEach(function(index) {
            if(this._perms[index].action == 'add') {
                this._perms[index] = null; // can't modify in-place, will break found indices
            }
            else {
                this._perms[index].action = 'remove';
            }
        }, this);
        this._removeNullPermissions();
    };

    this._removeNullPermissions = function() {
        var nullIndex = this._perms.indexOf(null);
        while(nullIndex !== -1) {
            this._perms.splice(nullIndex, 1);
            nullIndex = this._perms.indexOf(null);
        }
    };

    // constructor

    this._perms.forEach(function(perm) {
        perm.action = "";
    });
    this._perms.sort(UserPermissions.compare);

}

/**
 * Compare two permission objects. Sorting is by type  ("buffer", "network", "quasseluser"), then by name (case-
 * insensitive, excludes special characters e.g. #).
 *
 * Note that this method may involve a lookup of permission data to obtain the names of each argument.
 *
 * @param a
 * @param b
 * @returns {number} -1 if a comes before b; +1 if a comes after b; 0 if equal sort.
 */
UserPermissions.compare = function(a, b) {
    var typeSort = ['buffer', 'network', 'quasseluser'];
    if (a.type == b.type) {
        var aData = permissionData.findById(a.type, a.id);
        var bData = permissionData.findById(b.type, b.id);

        var cmpNameA = aData.name.replace(/\W/g, '').toUpperCase();
        var cmpNameB = bData.name.replace(/\W/g, '').toUpperCase();
        return (cmpNameA < cmpNameB) ? -1 : +1;
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
};

/*
 * Permission selector
 */

/**
 * Bootstrap the permission selector.
 */
function bootstrapPermissionSelect() {
    var bufferStore = new Memory({
        identifier: 'id',
        label: 'label',
        data: permissionData.getType('buffers')
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
        data: permissionData.getType('networks')
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
        data: permissionData.getType('quasselusers')
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

/**
 * Get a permission object from the selector. Note that 'access' will be returned blank.
 * @returns {{action: string, access: string, type: (string|string|string), id: *, qfpermid: number}|null}
 */
function getSelectorPermission() {
    var type, id;

    // find the selector current value
    if(fsBuffer.isValid() && fsBuffer.value !== "") {
        type = 'buffer';
        id = fsBuffer.value;
    }
    else if(fsNetwork.isValid() && fsNetwork.value !== "") {
        type = 'network';
        id = fsNetwork.value;
    }
    else if(fsQuasseluser.isValid() && fsQuasseluser.value !== "") {
        type = 'quasseluser';
        id = fsQuasseluser.value;
    }
    else {
        console.warn("getSelectorPermission: no selection");
        return null;
    }

    // Build the object to add
    return {
        'action': 'add',
        'access': '',
        'type': type,
        'id': id,
        'qfpermid': -1
    };
}

function clearPermissionSelector() {
    fsQuasseluser.set("value", null);
    fsNetwork.set("value", null);
    fsBuffer.set("value", null);
}

/***********************
 * User Permissions form
 ***********************/

/**
 * Bootstrap the main user permissions controls.
 */
function bootstrapPermissionForm() {
    $("#user-permissions-submit").on("click", submitPermissions);
    $("#btn-permission-allow").on("click", addAllowPermissionFromSelector);
    $("#btn-permission-deny").on("click", addDenyPermissionFromSelector);
    userPermissions = new UserPermissions(USER_PERMISSIONS);
    setupPermissionButtons();
}

function submitPermissions() {
    console.log("submitPermissions"); // TODO: submitPermissions
}


/**
 * Create the permission buttons and display them on the page.
 */
function setupPermissionButtons() {
    var $target = $("#user-permission-display");
    $target.empty();
    userPermissions.forEach(function(perm) {
        if(perm.action == 'remove') return; // do nothing
        console.log("setupPermissionButtons: " + perm.access + " " + perm.type + " " + perm.id);
        var $permButton = createPermissionButton(perm.qfpermid, perm.type, perm.id, perm.access);
        $target.append($permButton);
    });

    var $defaultButton = createPermissionButton(null, 'default', null, userPermissions.default);
    $target.append($defaultButton);
}

/**
 * @param qfpermid Permission record ID. If not specified, -1.
 * @param type "quasseluser", "network", "buffer" or "default"
 * @param id ID of the object to which the permission applies. This ID is for the specified `type`.
 * @param access "allow" or "deny".
 */
function createPermissionButton(qfpermid, type, id, access) {
    if (typeof qfpermid === 'undefined' || qfpermid === null) {
        qfpermid = -1;
    }
    if(typeof id === 'undefined' || id === null) {
        id = -1;
    }
    var $button = $('<button>');
    $button.attr('type', 'button');
    $button.addClass('btn-perm');
    $button.data('permission-access', access);
    $button.addClass('permission-access-' + access);

    if(type !== 'default') {
        var permData = permissionData.findById(type, id);
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
    if(type != 'default') $button.on('click', onButtonClickRemovePermission);
    else                  $button.on('click', onDefaultButtonClick);
    return $button;
}

/**
 * Called when the 'default' permission button is clicked. Toggles the default access and updates the UI button.
 */
function onDefaultButtonClick() {
    userPermissions.toggleDefault();
    updateDefaultButton();
}

function updateDefaultButton() {
    var $target = $('#user-permission-display');
    var access = userPermissions.getDefault();
    $target.find('.permission-type-default')
            .removeClass('permission-access-allow permission-access-deny')
            .addClass('permission-access-' + access)
            .data('permission-access', access);
}

function addAllowPermissionFromSelector() {
    var addPerm = getSelectorPermission();
    if(addPerm === null) return;
    addPerm.access = 'allow';
    addPermission(addPerm);
}

function addDenyPermissionFromSelector() {
    var addPerm = getSelectorPermission();
    if(addPerm === null) return;
    addPerm.access = 'deny';
    addPermission(addPerm);
}

function addPermission(addPerm) {
    userPermissions.add(addPerm);
    addPermissionToButtons(addPerm);
    clearPermissionSelector();
}

function addPermissionToButtons(addPerm) {
    // add the button to the UI
    var $target = $('#user-permission-display');

    // first possibility: button for this perm exists, want to trigger a colour transition if changing ID
    var $existingButton = $target.find('.permission-type-' + addPerm.type + '.permission-id-' + addPerm.id);
    if($existingButton.length > 0) {
        var newClass = 'permission-access-' + addPerm.access;
        if($existingButton.hasClass(newClass))
        {
            flashClass($existingButton, 'state-flashing-on', ANIMATE_FLASH_REPEAT, ANIMATE_FLASH_DELAY);
        }
        else
        {
            $existingButton.removeClass('permission-access-allow permission-access-deny')
                    .addClass('permission-access-' + addPerm.access)
                    .data('permission-access', addPerm.access);
        }
    }
    // second possibility: button doesn't exist for this permission
    else {
        // find where the new button goes
        var $allButtons = $target.children();
        var btnAddIndex = $allButtons.length;
        $allButtons.each(function(index, button) {
            var $button = $(button);
            var buttonPerm = {
                'type': $button.data('permission-type'),
                'id': $button.data('permission-id'),
                'access': $button.data('permission-access'),
                'qfpermid': $button.data('permission-qfpermid')
            };

            if(UserPermissions.compare(addPerm, buttonPerm) < 0) {
                btnAddIndex = index;
                return false;
            }
        });

        // prepare to insert and animate the new button in
        var $button = createPermissionButton(addPerm.qfpermid, addPerm.type, addPerm.id, addPerm.access);

        if($allButtons.length > btnAddIndex) {
            $allButtons.eq(btnAddIndex).before($button);
            addAnimation($button, 'width', 'perm-btn-' + addPerm.type + '-' + addPerm.id, true, true, 'state-flashing-on');
            animateTarget($button);
        }
        else {
            console.error("Cannot insert button at index " + btnAddIndex + ": only " + $allButtons.length + " buttons");
        }
    }
}

function onButtonClickRemovePermission() {
    var $this = $(this);
    var type_ = $this.data('permission-type');
    var id_ = $this.data('permission-id');

    userPermissions.remove(type_, id_);
    removePermissionButton(type_, id_);

    var perm = permissionData.findById(type_, id_);

    if(perm !== null)
    {
        fsBuffer.set("value", null);
        fsNetwork.set("value", null);
        fsQuasseluser.set("value", null);

        var targetSelector;
        if(type_ == 'buffer') targetSelector = fsBuffer;
        else if(type_ == 'network') targetSelector = fsNetwork;
        else if(type_ == 'quasseluser') targetSelector = fsQuasseluser;
        else throw new Error('Invalid type value: ' + type_);

        targetSelector.set("value", perm.id);
    }
    else
    {
        console.warn("onButtonClickRemovePermission: cannot find permission data to load into selector");
    }
}

function removePermissionButton(type, id) {
    var $target = $('#user-permission-display').find('.permission-type-' + type + '.permission-id-' + id);
    addAnimation($target, 'width', 'perm-btn-' + type + '-' + id, true, false);
    animateHideTarget($target, function() { $(this).remove(); });
}
