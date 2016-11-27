"""
Tools for preparing IRC log results for display.

Project: QuasselFlask
"""
from enum import Enum
from datetime import datetime
from flask import escape, Markup

import crcmod.predefined
import re

calculateNicknameHash = crcmod.predefined.mkPredefinedCrcFun('x-25')


class BacklogType(Enum):
    """
    https://github.com/quassel/quassel/blob/master/src/common/message.h
    That is all.
    """
    privmsg = 0x00001
    notice = 0x00002
    action = 0x00004
    nick = 0x00008
    mode = 0x00010
    join = 0x00020
    part = 0x00040
    quit = 0x00080
    kick = 0x00100
    kill = 0x00200
    server = 0x00400
    info = 0x00800
    error = 0x01000
    daychange = 0x02000
    topic = 0x04000
    netsplit_join = 0x08000
    netsplit_quit = 0x10000
    invite = 0x20000


class BufferType:
    """
    https://github.com/quassel/quassel/blob/master/src/common/bufferinfo.h
    That is all.
    """
    invalid_buffer = 0x00
    status_buffer = 0x01
    channel_buffer = 0x02
    query_buffer = 0x04
    group_buffer = 0x08


class Color(Enum):
    """
    Colours used in the nickname colour field. Names may be used directly in CSS and should coordinate with CSS classes,
    e.g.::

        nick_color = Color.red  # determined by some algorithm
        html += '<span class="nick-' + nick_color.name() + '">User</span>'

    And in CSS::

        .nick-red { color: #ff0000; }

    """
    yellow = 0
    orange = 1
    red = 2
    magenta = 3
    violet = 4
    blue = 5
    cyan = 6
    green = 7


class DisplayBacklog:
    _icon_type_map = {
        BacklogType.privmsg: '',
        BacklogType.notice: '',
        BacklogType.action: '-*-',
        BacklogType.nick: '<->',
        BacklogType.mode: '***',
        BacklogType.join: '-->',
        BacklogType.part: '<--',
        BacklogType.quit: '<--',
        BacklogType.kick: '***',
        BacklogType.kill: '***',
        BacklogType.server: '*',
        BacklogType.info: 'i',
        BacklogType.error: '!!!',
        BacklogType.daychange: '*',
        BacklogType.topic: '*',
        BacklogType.netsplit_join: '-->',
        BacklogType.netsplit_quit: '<--',
        BacklogType.invite: '*',
    }
    _time_format = '{:%Y-%m-%d %H:%M:%S}'
    _format_chars = ['\x02', '\x1D', '\x1F', '\x03', '\x16', '\x0f']
    _color_number = '1[0-5]|0?[1-9]'  # between 01 and 15 inclusive
    # capture groups always (formatting_match, num1, num2)
    # num1 and num2 are colour ids (or None) for \x03, None for other formatting
    _format_re = re.compile('(\x02|'  # b
                            '\x1D|'  # i
                            '\x1F|'  # u
                            # colours, capture groups: full spec, color1|None, color2|None
                            '\x03' r'(?:(' + _color_number + ')(?:,(' + _color_number + '))?)?|'
                            '\x16|'  # swap
                            '\x0f)'  # reset
                            )

    @classmethod
    def set_time_format(cls, s: str):
        """
        :param s: format() specifier containing one variable for a datetime argument. This method does not check whether
            the time format specifies a valid datetime format, only that it executes format() without raising an
            exception (the returned string might not actually format a datetime).
        :return: None
        :raise IndexError: too many arguments in format specifier
        :raise KeyError: invalid key specified in format specifier
        """
        _ = s.format(datetime.now())  # test if valid - may throw IndexError or KeyError on invalid specification
        cls._time_format = s

    def __init__(self, backlog):
        """
        :param backlog: Backlog string
        """
        self.time = DisplayBacklog._time_format.format(backlog.time)  # type: str
        self.channel = backlog.buffer.buffername  # type: str
        self.sender = backlog.sender.sender  # type: str
        self.nickname = self.sender.split('!', 1)[0]  # type: str
        try:
            self.type = BacklogType(backlog.type)
        except ValueError:
            self.type = BacklogType.privmsg
        self._message = backlog.message  # type: str

    def get_icon_text(self):
        return self._icon_type_map.get(self.type, '')

    def get_nick_hash(self):
        """
        Hashes the nick and returns a four-bit value. This method internally uses CRC16 x-25 implementation, which
        corresponds to Quassel's implementation (qChecksum() on Quassel 0.10.0, Qt 4.8.5) according to a quick
        empirical check (6 nicknames).

        See: http://crcmod.sourceforge.net/crcmod.predefined.html
        :return:
        """
        lower_nick = self.nickname.lower().rstrip('_')
        stripped_nick = lower_nick.rstrip('_')
        normalized_nick = stripped_nick if stripped_nick else lower_nick  # in case nickname is all underscores
        return calculateNicknameHash(normalized_nick.encode('latin-1')) & 0xF

    def get_nick_color(self):
        """
        Return the nick's colour based on hash. Corresponds to Quassel's own implementation.

        The colours will correspond in QuasselFlask's default colour scheme and in the Solarized Light/Dark themes for
        Quassel by antoligy <https://github.com/antoligy/SolarizedQuassel>.

        Otherwise, to make this work with other themes, you can customise the Color enum. Usually, Quassel supports 16
        colours. If you want the colours here to correspond to your Quassel colour scheme, specify all 16 colours you
        used in Quassel (or specify 8 colours - corresponds to repeating the list of 8 colours twice in Quassel's nick
        colour settings).

        For Quassel's hash implementation, see:
        https://github.com/quassel/quassel/blob/6509162911c0ceb3658f6a7ece1a1d82c97b577e/src/uisupport/uistyle.cpp#L874
        :return: Color object
        """
        return Color(self.get_nick_hash() % len(Color))

    def format_html_message(self):
        """
        Convert IRC formatting into HTML.
        :return: HTML string
        """
        irc_chars = DisplayBacklog._format_chars

        safe_msg = escape(self._message)
        in_msg_tokens = DisplayBacklog._format_re.split(safe_msg)  # simple tokenize!
        out_msg_tokens = []

        nesting = 0
        state = {
            'bold': False,
            'italic': False,
            'underline': False,
            'color': False
        }
        color_processing = False
        color_processing_arg = 0
        color_args = [None, None]

        for token in in_msg_tokens:
            if color_processing:
                try:
                    color_args[color_processing_arg] = int(token)
                except (ValueError, TypeError):
                    color_args[color_processing_arg] = None
                color_processing_arg += 1

                # end condition
                if color_processing_arg >= 2:
                    self._add_html_close_tag(out_msg_tokens, state)
                    state['color'] = True if any(color_args) else False
                    color_processing = False
                    color_processing_arg = 0
                    self._add_html_open_tag(out_msg_tokens, state, color_args)

            elif token and (token[0] in irc_chars):
                c = token[0]
                if c == '\x02':
                    self._add_html_close_tag(out_msg_tokens, state)
                    state['bold'] = not state['bold']
                    self._add_html_open_tag(out_msg_tokens, state, color_args)
                elif c == '\x1d':
                    self._add_html_close_tag(out_msg_tokens, state)
                    state['italic'] = not state['italic']
                    self._add_html_open_tag(out_msg_tokens, state, color_args)
                elif c == '\x1f':
                    self._add_html_close_tag(out_msg_tokens, state)
                    state['underline'] = not state['underline']
                    self._add_html_open_tag(out_msg_tokens, state, color_args)
                elif c == '\x03':
                    color_processing = True
                    color_processing_arg = 0
                elif c == '\x16':
                    if state['color']:  # only if colour is applied right now
                        self._add_html_close_tag(out_msg_tokens, state)
                        color_args[0], color_args[1] = color_args[1], color_args[0]
                        self._add_html_open_tag(out_msg_tokens, state, color_args)
                elif c == '\x0f':
                    self._add_html_close_tag(out_msg_tokens, state)
                    state = {k: False for k in state}
                else:
                    raise ValueError('Bad formatting character - '
                                     'did you change _format_chars and forget to update format_html_message()?')
            else:  # not a special character
                if token:  # we only filter None/empty string here because None is valuable for colour processing
                    out_msg_tokens.append(token)

        # if any formatting still applied at the end, close the last tag
        self._add_html_close_tag(out_msg_tokens, state)
        return Markup(''.join(out_msg_tokens))

    @staticmethod
    def _add_html_open_tag(output: list, state: {str: bool}, color_args=(None, None)):
        """
        Add HTML opening tag for the currently enabled formatting options (in ``state`` plus ``color_args``) to
        ``output``. Used by format_html_message(). If no formatting options enabled, does nothing.
        :param output: the current list of output tokens so far
        :param state: The formatting flags to be applied.
        :param color_args: Color arguments, a 2-element addressable collection (e.g. tuple or list).
        :return: True if an open tag was added, False otherwise (because no formatting enabled)
        """
        classes = []

        for name, enabled in state.items():
            if enabled and name != 'color':
                classes.append('irc-{}'.format(name))
            elif enabled and name == 'color' and any(color_args):
                try:
                    classes.append('irc-color{:02d}'.format(color_args[0]))
                    classes.append('irc-bgcolor{:02d}'.format(color_args[1]))
                except (ValueError, TypeError):
                    # no colour, I guess! None (no arg) and invalid strings
                    # foreground colour may be set at this point even if background colour is None/invalid
                    # that behaviour is intended: no need for cleanup here
                    pass

        if classes:
            output.append('<span class="{}">'.format(' '.join(classes)))
            return True
        return False

    @staticmethod
    def _add_html_close_tag(output: list, pre_state: {str: bool}):
        """
        Add an HTML closing tag if any formatting options are enabled now in ``pre-state``, which represents the
        formatting state before the closing tag is added. This state is not modified - it is the responsibility of the
        caller to update the state after the formatting is closed.

        In the case that ``output`` contains an opening tag as its last element, and thus adding this close tag would
        create a redundant/empty element, this redundant element is removed instead.
        :param output: the current list of output tokens so far
        :param pre_state: the formatting options state (enabled/disabled) before the close tag is added
        :return: True if anything was added or redundant tags removed, False if not (because nothing applied)
        """
        if any(pre_state.values()):  # close tag only if formatting had previously been applied
            if output and output[-1].startswith('<span'):  # redundant element
                output.pop()
            else:
                output.append('</span>')
            return True
        return False
