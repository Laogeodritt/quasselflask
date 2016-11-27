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

require([
        'dijit/form/FilteringSelect',
        'dojo/store/Memory'
], function(fs, m) {
    FilteringSelect = fs;
    Memory = m;
    preprocessPermissionData();
    bootstrapPermissionSelect();
});


/*
 * Permission Data
 */

/**
 * Find a permission datum by its id.
 * @param key "quasselusers", "networks" or "channels"
 * @param id Numeric ID to search for.
 * @returns {object} Result, or undefined if no results.
 */
function findPermissionById(key, id) {
    return $.grep(PERMISSION_DATA[key], function(o) { return o.id === id; })[0];
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
    PERMISSION_DATA.networks.forEach(function(network) {
        network.label = network.name + '<span class="quasseluser">' +
                        findPermissionById('quasselusers', network.quasseluserid).name + '</span>';
    });
    PERMISSION_DATA.buffers.forEach(function(buffer) {
        buffer.quasseluserid = findPermissionById('networks', buffer.networkid).quasseluserid;
        buffer.label = buffer.name + '<span class="network">' +
                findPermissionById('networks', buffer.networkid).name + '</span><span class="quasseluser">' +
                findPermissionById('quasselusers', buffer.quasseluserid).name + '</span>';
    });
}


/*
 * Permission selector
 */

function bootstrapPermissionSelect() {
    var bufferStore = new Memory({
        identifier: 'id',
        label: 'name',
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
