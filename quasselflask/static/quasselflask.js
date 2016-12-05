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

var ANIMATE_FADE_TIME = 400;
var ANIMATE_SLIDE_TIME = 400;
var ANIMATE_HIGHLIGHT_TIME = 300;

var ANIMATE_OPACITY_VISIBLE = 1;
var ANIMATE_OPACITY_INVISIBLE = 0;

// suggested config values for use by other modules when calling flash methods
var ANIMATE_FLASH_REPEAT = 2;
var ANIMATE_FLASH_DELAY = 300;

/*
 * Bootstrap
 */
$(document).ready(function() {
    /*
     * Generic slide animations
     *
     * HTML attributes:
     *
     * Trigger element (e.g. onclick):
     * data-animate-event = (any valid event name, e.g. 'click')
     * data-animate-target = (corresponds to data-animate-id attribute)
     * data-animate-once (if present, animate only the first time triggered instead of toggle)
     *
     * Animation target:
     *
     * data-animate-type = width|height
     * data-animate-id = (corresponds to data-animate-target of trigger element)
     * data-animate-once (if present, animate only the first time this element is targeted for animation)
     * Class "animate-start-hidden": if present, start hidden; else start visible.
     * data-animate-flash-class = (CSS class to set briefly upon displaying the element)
     */
    var $animateTargets = $('[data-animate-id]');
    initAnimateTarget($animateTargets);

    $('[data-animate-target]').each(function() {
        $(this).on($(this).data('animate-event'), onAnimateEvent);
    }); // each
});

/* library */
/**
 * Initialise one or more animation targets, if properties are already set for this element.
 * @param $targets Jquery object of one or more elements corresponding to animation targets. If non-animation targets
 *      are present (i.e. do not have the 'data-animate-id' property), they will be excluded.
 */
function initAnimateTarget($targets) {
    var $animTargets = $targets.filter('[data-animate-id]');
    $animTargets.filter('.animate-start-hidden[data-animate-type="width"]').animate({width:"toggle"}, 0);
    $animTargets.filter('.animate-start-hidden[data-animate-type="height"]').animate({height:"toggle"}, 0);
}

/**
 * Sets up to animate an element and then initialise it (initAnimateTarget()).
 * @param elem DOM element to animate
 * @param type width|height
 * @param id animation ID (for use with animation trigger elements)
 * @param once {boolean} Whether to animate only once
 * @param startHidden {boolean} Whether to start invisible
 * @param [highlightClass=undefined] {string} If present, enable this class briefly to "flash" or "highlight" an
 *      incoming or outgoing object.
 */
function addAnimation(elem, type, id, once, startHidden, highlightClass) {
    var $elem = $(elem);

    $elem.data('animate-type', type);
    $elem.attr('data-animate-type', type);

    $elem.data('animate-id', id);
    $elem.attr('data-animate-id', id);

    if(typeof highlightClass !== 'undefined' && highlightClass != null) {
        $elem.data('animate-highlight-class', highlightClass);
        $elem.attr('data-animate-highlight-class', highlightClass);
    }

    if(once) {
        $elem.data('animate-once');
        $elem.attr('data-animate-once', 1);
    }
    if(startHidden) $elem.addClass('animate-start-hidden');

    initAnimateTarget($elem);
}


/**
 * Starts an animation from an event trigger. `this` must be set to the event trigger, not the animation target.
 */
function onAnimateEvent() {
    // if this is a one-time-only animation, remove this listener after the first time
    if($(this).data('animate-once') != undefined) $(this).off($(this).data('animate-event'));

    var targetAnimateId = $(this).data('animate-target');
    animateTarget($('[data-animate-id="' + targetAnimateId + '"'));
}

/**
 * Toggles visible/invisible with fade/slide animations. Requires this module's animation attributes to be set.
 * @param $targets JQuery object of one or more targets to animate.
 */
function animateTarget($targets) {
    var $animTargets = $($targets).filter('[data-animate-id]');
    $animTargets.each(function() {
        var $this = $(this);

        // if animate-once, disable further animations
        if($this.data('animate-once') != undefined) {
            $this.data('animate-id', '');
            $this.prop('data-animate-id', '');
        }

        if($this.is(':visible')) {
            animateHideTarget($this);
        }
        else {
            animateShowTarget($this);
        }
    });
}

/**
 * Toggles visible with slide/fade animation. Requires this module's animation attributes to be set.
 * @param $targets JQuery object of one or more targets to animate.
 * @param [callback=undefined] {function} Callback. `this` in the callback is set to the target.
 */
function animateShowTarget($targets, callback) {
    if(typeof callback === 'undefined' || callback === null) callback = function() {};
    function _fadeIn() {
        var complete;
        if(typeof $(this).data('animate-highlight-class') !== 'undefined')
            complete = _highlight;
        else
            complete = callback;

        $(this).css('visibility', 'visible')
                .css('opacity', '0')
                .fadeTo(ANIMATE_FADE_TIME, ANIMATE_OPACITY_VISIBLE, complete);
    }

    function _highlight() {
        flashClass($(this), $(this).data('animate-highlight-class'), 1, ANIMATE_HIGHLIGHT_TIME, callback);
    }

    var $animTargets = $($targets).filter('[data-animate-id]');
    $animTargets.each(function() {
        var $this = $(this);
        $this.css('visibility', 'hidden');
        $this.animate(getAnimateProp($this), ANIMATE_SLIDE_TIME, 'swing', _fadeIn);
    }); // each target
}

/**
 * Toggles invisible with fade/slide animation. Requires this module's animation attributes to be set.
 * @param $targets JQuery object of one or more targets to animate.
 * @param [callback=undefined] {function} Callback. `this` in the callback is set to the target.
 */
function animateHideTarget($targets, callback) {
    if(typeof callback === 'undefined' || callback === null) callback = function() {};
    function _highlight() {
        flashClass($(this), $(this).data('animate-highlight-class'), 1, ANIMATE_HIGHLIGHT_TIME, _fadeOut);
    }
    function _fadeOut() {
        $(this).css('opacity', 1).fadeTo(ANIMATE_FADE_TIME, ANIMATE_OPACITY_INVISIBLE, _slideOut)
    }

    function _slideOut() {
        $(this).css('visibility', 'hidden').animate(getAnimateProp($(this)), ANIMATE_SLIDE_TIME, 'swing', callback);
    }

    var $animTargets = $($targets).filter('[data-animate-id]');
    $animTargets.each(function() {
        if(typeof $(this).data('animate-highlight-class') !== 'undefined')
            _highlight.call(this);
        else
            _fadeOut.call(this);
    })
}

/**
 * Flash a target by applying a CSS class on and off. This method does not handle the transition animations or actual
 * styles, which can be configured in CSS3 if desired (transition attribute).
 *
 * @param $targets {object} jQuery object of one or more elements to flash.
 * @param flashClass {string} CSS class to flash on/off.
 * @param repetition {number} How many times to flash them. Must be at least 1.
 * @param delay {number} Milliseconds between on and off, i.e., half-period.
 * @param [callback=undefined] {function} Callback at the end of the flashing. `this` is set to $targets.
 */
function flashClass($targets, flashClass, repetition, delay, callback) {
    if(typeof callback === 'undefined') callback = function() {};
    var curReps = 0;

    function _flashFirst() {
        $targets.addClass(flashClass);
        setTimeout(_flashSecond, delay);
    }

    function _flashSecond() {
        $targets.removeClass(flashClass);
        curReps += 1;
        if(curReps < repetition) setTimeout(_flashFirst, delay);
        else if(typeof callback === 'function') callback.call($targets);
    }

    _flashFirst();
}

/**
 * Get the animateProp object for JQuery animate() method for the slide part of animations.
 * @param $target JQuery object of ONE target to animate. If multiple, returns the animateProp of the first result.
 */
function getAnimateProp($target) {
    var animateProp;
    switch($target.data('animate-type')) {
    case 'width':
        animateProp = { width: "toggle" };
        break;
    case "height":
    default:
        animateProp = { height: "toggle" };
        break;
    }
    return animateProp;
}
