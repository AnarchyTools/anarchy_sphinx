# Copyright 2016 by Johannes Schriewer
# BSD license, see LICENSE for details

import os

VERSION = (0, 3, 1)

__version__ = ".".join(str(v) for v in VERSION)
__version_full__ = __version__


def get_html_theme_path():
    """Return list of HTML theme paths."""
    cur_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return cur_dir
