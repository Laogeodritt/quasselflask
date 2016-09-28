"""
Tools for preparing IRC log results for display.

Project: QuasselFlask
"""
from enum import Enum
from datetime import datetime

import crcmod.predefined

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

    @staticmethod
    def set_time_format(s: str):
        """
        :param s: format() specifier containing one variable for a datetime argument. This method does not check whether
            the time format specifies a valid datetime format, only that it executes format() without raising an
            exception (the returned string might not actually format a datetime).
        :return: None
        :raise IndexError: too many arguments in format specifier
        :raise KeyError: invalid key specified in format specifier
        """
        _ = s.format(datetime.now())  # test if valid - may throw IndexError or KeyError on invalid specifications
        DisplayBacklog._time_format = s

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
        except IndexError:
            self.type = BacklogType.privmsg
        self.message = backlog.message  # type: str

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


