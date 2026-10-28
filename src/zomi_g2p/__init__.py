"""
zomi_g2p
========

Grapheme-to-Phoneme conversion for the Zomi language.

Public API
----------
- :class:`ZomiG2P` — the converter.
- :func:`load_default_lexicon` — load the bundled lexicon.
- :func:`load_lexicon_from_dir` — load a user-supplied lexicon directory.
- :class:`Lexicon`, :class:`LexiconEntry`, :class:`Segment` — data model.
- Exception hierarchy rooted at :class:`ZomiG2PError`.

Example
-------
>>> from zomi_g2p import ZomiG2P, load_default_lexicon
>>> g2p = ZomiG2P(load_default_lexicon())
>>> g2p.convert("ankham").joined()
"""

from __future__ import annotations

import logging

# from .cli import main as cli_main  # noqa: F401
from .converter import ConversionResult, ZomiG2P
from .exceptions import (
    AmbiguousWordError,
    ConversionError,
    DataValidationError,
    InvalidOutputError,
    LexiconError,
    SyllableToneMismatchError,
    UnknownToneError,
    UnknownWordError,
    ZomiG2PError,
)
from .lexicon import (
    Lexicon,
    LexiconEntry,
    Segment,
    load_default_lexicon,
    load_lexicon_from_dir,
)
from .utils.provenance import (
    TONES_SOURCE_CALLER,
    TONES_SOURCE_LEXICON,
    TONES_SOURCE_MODEL,
    TONES_SOURCE_RULE,
    TONES_SOURCE_UNKNOWN,
)
from .utils.helpers import (
    _reconcile,
    # reconcile
    # _reconcile_tones,
)

# __version__ = "0.1.0"
from .version import __version__

__all__ = [
    # Core API
    "ZomiG2P",
    "ConversionResult",
    # Lexicon loading
    "load_default_lexicon",
    "load_lexicon_from_dir",
    # Data model
    "Lexicon",
    "LexiconEntry",
    "Segment",
    # Exceptions
    "ZomiG2PError",
    "LexiconError",
    "UnknownWordError",
    "AmbiguousWordError",
    "SyllableToneMismatchError",
    "DataValidationError",
    "UnknownToneError",
    "ConversionError",
    "InvalidOutputError",
]

logging.getLogger("zomi_g2p").addHandler(logging.NullHandler())