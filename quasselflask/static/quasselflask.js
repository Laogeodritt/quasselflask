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
    $('.animate-start-hidden[data-animate-type="height"]').animate({height:"toggle"}, 0);

    $('[data-animate-target]').each(function() {
        $(this).on($(this).data('animate-event'), onAnimateEvent);
    }); // each
});

/* library */

/**
 * Starts an animation. `this` must be set to the event trigger, not the animation target.
 */
function onAnimateEvent() {
    // remove this listener after the first time
    if($(this).data('animate-once') != undefined) $(this).off($(this).data('animate-event'));

    var targetAnimateId = $(this).data('animate-target')
    $('[data-animate-id="' + targetAnimateId + '"]').each(function() {
        var animateProp;
        switch($(this).data('animate-type')) {
        case "width":
            animateProp = { width: "toggle" };
            break;
        case "height":
            animateProp = { height: "toggle" };
            break;
        }
        $(this).animate(
                animateProp,
                400,
                'swing',
                function() {
                    $(this).hide().css('visibility', 'visible');
                    $(this).fadeIn(300);
                }
        );
    }); // each target
}
