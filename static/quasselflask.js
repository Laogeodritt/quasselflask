/******************************************************************************
 * File: quasselflask.js
 * QuasselFlask - Log Search Utility for Quassel Postgresql Database
 * https://github.com/Laogeodritt/quasselflask
 *
 * Dependencies:
 * * jQuery >= 3.0.0
 *
 * Licensed under the GNU Public Licence, version 3
 * <https://www.gnu.org/licenses/gpl-3.0.en.html>
 *****************************************************************************/

/* bootstrap */
$(document).ready(function() {
    updateAddRemoveQueryButtons();
    $(".search-query-wild").each(function() {
        setWildcardQuery(this);
    });
});

/* library */

var _removedQueryRows = [];
const MIN_QUERY_ROWS = 1;
const MAX_QUERY_ROWS = 10;

function updateAddRemoveQueryButtons() {
    var $queryContainers = $('.search-query-container');
    var numRows = $queryContainers.length;
    var isHigh = numRows >= MAX_QUERY_ROWS;
    var isLow = numRows <= MIN_QUERY_ROWS;
    $('#more-queries').prop('disabled', isHigh);
    $('#less-queries').prop('disabled', isLow);
}

function addQueryRow() {
    // prepare
    var $queryContainers = $('.search-query-container');
    var likeCheckboxId = "query-wild-" + $queryContainers.length;
    var $newQuery = null;

    // define the elements - either pick a previously removed one or generate a new one
    if(_removedQueryRows.length == 0) {
        $newQuery = $queryContainers.first().clone();
        $newQuery.find('.search-query').val('');
        var $newQueryCheckbox = $newQuery.find('.search-query-wild');
        $newQueryCheckbox.prop('checked', false).prop('id', likeCheckboxId);
        $newQueryCheckbox.next('label').prop('for', likeCheckboxId);
        setWildcardQuery($newQueryCheckbox);
    }
    else {
        $newQuery = _removedQueryRows.pop();
    }

    // insert at the end (or if none into where it's supposed to go)
    if($queryContainers.length > 0) {
        $queryContainers.last().after($newQuery);
    }
    else {
        $('#moreless-queries').after($newQuery);
    }
}

function removeQueryRow() {
    var $queryContainers = $('.search-query-container');
    if($queryContainers.length > 1) {
        var $removeQuery = $queryContainers.last();
        $removeQuery.detach();
        _removedQueryRows.push($removeQuery);
    }
}

function setWildcardQuery(elCheckbox) {
    var $elCheckbox = $(elCheckbox);
    $elCheckbox.parent().find('.search-query').prop('name', $elCheckbox.prop('checked')?  'wildcardquery' : 'query');
}
