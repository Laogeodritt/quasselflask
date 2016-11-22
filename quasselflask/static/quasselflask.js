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
    $('.animate-start-hidden[data-animate-type="width"]').animate({width:"toggle"}, 0);

    var $watchTarget = $('[data-animate-target]');
    $watchTarget.each(function() {
        $(this).on($(this).data('animate-event'), function() {
            console.log("animating?");
            if($(this).data('animate-once')) $(this).off('input'); // remove this listener after the first time
            $('[data-animate-id="' + $(this).data('animate-target') + '"]').animate(
                    {
                        width: "toggle"
                    },
                    300,
                    'swing',
                    function() {
                        $(this).hide().css('visibility', 'visible');
                        $(this).fadeIn(300);
                    }
            );
        }); // on event
    }); // each
});

/* library */
