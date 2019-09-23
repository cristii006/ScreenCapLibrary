#  Copyright 2008-2015 Nokia Networks
#  Copyright 2016-     Robot Framework Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import sys
from contextlib import contextmanager


def _norm_path(path):
    if not path:
        return path
    return os.path.normpath(path.replace('/', os.sep))


def _compression_value_conversion(value):
    """
    PNG compression values are within range [0, 9]. This value must
    be mapped to a [0-100] interval.
    """
    try:
        if int(value) < 0 or int(value) > 100:
            raise RuntimeError("Quality argument must be of between 0 and 100.")
        return 0 if int(value) == 100 else int(9 - (int(value) / 11))
    except ValueError:
        raise RuntimeError("Quality argument must be of type integer.")


def _pil_quality_conversion(value):
    """
    The quality in Pillow is between [1, 95] and must be converted to
    a [0-100] interval.
    """
    try:
        if int(value) < 0 or int(value) > 100:
            raise RuntimeError("Quality argument must be of between 0 and 100.")
        if int(value) < 1:
            return 1
        elif int(value) >= 95:
            return 95
        return int(value)
    except ValueError:
        raise RuntimeError("The image quality argument must be of type integer.")


@contextmanager
def suppress_stderr(to=os.devnull):
    fd = sys.__stderr__.fileno()

    def _redirect_stderr(to):
        sys.__stderr__.close()  # + implicit flush()
        os.dup2(to.fileno(), fd)  # fd writes to 'to' file
        sys.__stderr__ = os.fdopen(fd, 'w')  # Python writes to fd

    with os.fdopen(os.dup(fd), 'w') as old_stderr:
        with open(to, 'w') as file:
            _redirect_stderr(to=file)
        try:
            yield  # allow code to be run with the redirected stderr
        finally:
            _redirect_stderr(to=old_stderr)  # restore stderr.
