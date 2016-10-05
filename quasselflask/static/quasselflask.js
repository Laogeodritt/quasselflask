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
    $('table.irc-log tr.irc-line').click(function(event) {
        toggleIrcLineDetails(event.delegateTarget);
    });

});

/* library */
function toggleIrcLineDetails(el) {
    var $target = $(el).next();
    if($target.hasClass('expanded'))
        $target.addClass('collapsed')
               .removeClass('expanded');
    else
        $target.addClass('expanded')
               .removeClass('collapsed');
    // slideUp() and slideDown(), or other anims, not supported on tables. Gah!
}

function expandAllIrcLineDetails() {
    $('table.irc-log tr.irc-backlog-details.collapsed')
            .addClass('expanded')
            .removeClass('collapsed');
    return false; // when used as a click event on <a>
}

function collapseAllIrcLineDetails() {
    $('table.irc-log tr.irc-backlog-details.expanded')
            .addClass('collapsed')
            .removeClass('expanded');
    return false; // when used as a click event on <a>
}
