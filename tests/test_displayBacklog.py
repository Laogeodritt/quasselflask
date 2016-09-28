"""
DisplayBacklog tests.

Project: QuasselFlask
"""
from unittest import TestCase
from quasselflask.irclog import DisplayBacklog
from datetime import datetime
import re

FORMAT_TAG = '<span class="([^"]+)">'


class TestDisplayBacklog(TestCase):
    def setUp(self):
        class Dummy:
            pass
        dummy = Dummy()
        dummy.time = datetime(1970, 1, 1)
        dummy.buffer = Dummy()
        dummy.buffer.buffername = 'channel'
        dummy.sender = Dummy()
        dummy.sender.sender = 'sender'
        dummy.type = 0
        dummy.message = "message"
        self.dut = DisplayBacklog(dummy)
        self.dummy = dummy

    def test_format_html_message(self):
        # each test case is a tuple:
        # (input_string, results regex string without matching groups, (('bold', 'underline'), ('bold',)) )
        # Last element tuple: outer tuple elements correspond to FORMAT_TAG in result regex; inner tuple elements
        # list all the classes that should be listed in the corresponding FORMAT_TAG (without the irc- prefix)
        test_cases = [
            (  # empty input
                '',
                '',
                ()
            ),
            (  # a space
                ' ',
                ' ',
                ()
            ),
            (  # no formatting
                'Hello mirror so glad to see you my friend',
                'Hello mirror so glad to see you my friend',
                ()
            ),
            (  # Single toggled tag: formats and does not create a <span> when all formatting disabled
                'This is \x02bold text\x02 and normal',
                'This is ' + FORMAT_TAG + 'bold text</span> and normal',
                (('bold',),)
             ),
            (  # Underline, message-initial: formats at the beginning of a message without generating leading </span>
                '\x1fInitially underlined\x1f but not always',
                FORMAT_TAG + 'Initially underlined</span> but not always',
                (('underline',),)
            ),
            (  # Italic, message-final: formats at the end of a message without generating trailing <span...>
                'Ending with \x1ditalic text\x1d',
                'Ending with ' + FORMAT_TAG + 'italic text</span>',
                (('italic',),)
            ),
            (  # Correct handling of multiple nested tags
                'Fun \x02but correct\x1d nesting\x1d of text\x02 here',
                'Fun ' + FORMAT_TAG + 'but correct</span>' + FORMAT_TAG + ' nesting</span>' + FORMAT_TAG +
                ' of text</span> here',
                (('bold',), ('bold', 'italic'), ('bold',))
            ),
            (  # Correct handling of overlapping (but not nested) formatting
                'Fun \x02and incorrect\x1d nesting\x02 of text\x1d here',
                'Fun ' + FORMAT_TAG + 'and incorrect</span>' + FORMAT_TAG + ' nesting</span>' + FORMAT_TAG +
                ' of text</span> here',
                (('bold',), ('bold', 'italic'), ('italic',))
            ),
            (  # Color w/o background
                'Here is \x0301color text',
                'Here is ' + FORMAT_TAG + 'color text</span>',
                (('color01',),)
            ),
            (  # Color reset
                'Here is \x0301color\x03xxa text',
                'Here is ' + FORMAT_TAG + 'color</span>xxa text',
                (('color01',),)
            ),
            (  # Color w/ background
                'Here is \x0301,12color\x03 text',
                'Here is ' + FORMAT_TAG + 'color</span> text',
                (('color01', 'bgcolor12'),)
            ),
            (  # Color single-digit
                'Here is \x0301,5color\x03 text',
                'Here is ' + FORMAT_TAG + 'color</span> text',
                (('color01', 'bgcolor05'),)
            ),
            (  # Invalid colour number w/o background
                'Here is \x0378color text',
                'Here is ' + FORMAT_TAG + '8color text</span>',
                (('color07'),)
            ),
            (  # Invalid colour number in background
                'Here is \x031,78color text',
                'Here is ' + FORMAT_TAG + '8color text</span>',
                (('color01', 'bgcolor07'),)
            ),
            (  # Not a number in expected background position
                'Here is \x031,color text',
                'Here is ' + FORMAT_TAG + ',color text</span>',
                (('color01'),)
            ),
            (  # Reset
                '\x02Let us \x1d test out\x0f reset and also \x034,12color \x02bold\x0f now',
                FORMAT_TAG + 'Let us </span>' + FORMAT_TAG + ' test out</span> reset and also ' +
                FORMAT_TAG + 'color </span>' + FORMAT_TAG + 'bold</span> now',
                (('bold',), ('bold', 'italic'), ('color04', 'bgcolor12'), ('color04', 'bgcolor12', 'bold'))
            ),
            (  # Avoid multiple spans for consecutive format strings
                '\x02\x1d\x0304,12Lots of stuff',
                FORMAT_TAG + 'Lots of stuff</span>',
                (('bold', 'italic', 'color04', 'bgcolor12',),),
            )
        ]

        for irc_input, expected_re, class_list in test_cases:
            dut = self.dut
            dut._message = irc_input
            result = dut.format_html_message()

            # Check if general output is correct (minus HTML tag classes)
            result_match = re.fullmatch(expected_re, result)
            self.assertIsNotNone(result_match, "No regex match for expected result\nInput: " + repr(irc_input) +
                            "\nOutput: " + result +
                            "\nExpected to match: " + expected_re)

            # check HTML tag classes
            for i, (tag_classes, expected_class_list) in enumerate(zip(result_match.groups(), class_list)):
                for expected_class in expected_class_list:
                    self.assertIn(expected_class, tag_classes, "Expected class not found in tag"
                                    "\nFailed on test: " + repr(irc_input) +
                                    "\nOutput: " + result +
                                    "\nTag #{:d} should have class '{}'".format(i+1, expected_class))
