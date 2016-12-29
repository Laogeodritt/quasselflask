"""
Management of themes on the display.

Project: QuasselFlask
"""


class Theme:
    def __init__(self, id_: int, name: str, file: str=None, root_class: str=None, custom=False):
        self._id = id_
        self._name = name
        self._file = file
        self._clss = root_class
        self._custom = bool(custom)

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def file(self):
        return self._file

    @property
    def root_class(self):
        return self._clss

    @property
    def is_custom(self):
        return self._custom
