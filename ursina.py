import os as _os

# Brython requests "ursina.py" before "ursina/__init__.py"; expose a package path
# to avoid a 404 and keep submodule imports working.
__path__ = [_os.path.join(_os.path.dirname(__file__), "ursina")]

from ursina.sequence import Sequence, Func, Wait  # noqa: F401
from ursina.entity import Entity  # noqa: F401
from ursina.main import window  # noqa: F401
from ursina.main import scene  # noqa: F401
from ursina import color  # noqa: F401
from ursina.input_handler import held_keys  # noqa: F401
from ursina.main import mouse  # noqa: F401
from ursina.main import invoke, destroy  # noqa: F401
from ursina.main import Ursina  # noqa: F401
from ursina.main import camera  # noqa: F401

from ursina.text import Text  # noqa: F401
from ursina.text import Tooltip  # noqa: F401
from ursina.button import Button  # noqa: F401

from ursina.main import Entity as Panel  # noqa: F401

from ursina.main import Empty  # noqa: F401
from ursina.main import Empty as Quad  # noqa: F401
from ursina.main import Empty as Circle  # noqa: F401
