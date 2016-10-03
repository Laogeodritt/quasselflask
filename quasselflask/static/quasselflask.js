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
        toggle(event.delegateTarget);
    });
});

/* library */
function toggle(el) {
    var $target = $(el).next();
    $target.toggle()
    // slideUp() and slideDown(), or other anims, not supported on tables. Gah!
}
