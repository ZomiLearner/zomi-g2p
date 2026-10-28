"""
zomi_g2p.exceptions
===================

Exception hierarchy for zomi-g2p.

All exceptions raised by the package inherit from :class:`ZomiG2PError`.
This lets callers write::

    from zomi_g2p import ZomiG2PError

    try:
        g2p.convert(word)
    except ZomiG2PError:
        ...

while still allowing specific handling::

    from zomi_g2p import UnknownWordError, AmbiguousWordError

    try:
        g2p.convert(word)
    except AmbiguousWordError as exc:
        # polyphone needs a sense tag
        ...
    except UnknownWordError:
        # OOV: fall back to character input
        ...

Hierarchy
---------
ZomiG2PError
├── LexiconError
│   ├── UnknownWordError
│   ├── AmbiguousWordError
│   ├── SyllableToneMismatchError
│   └── DataValidationError
├── UnknownToneError
└── ConversionError
    └── InvalidOutputError
"""

from __future__ import annotations


class ZomiG2PError(Exception):
    """Base class for all zomi-g2p errors."""


# ---------------------------------------------------------------------------
# Lexicon / data errors
# ---------------------------------------------------------------------------
class LexiconError(ZomiG2PError):
    """Base class for errors related to lexicon data."""


class UnknownWordError(LexiconError):
    """Raised when a word is not present in the lexicon.

    Attributes
    ----------
    word : str
        The word that was looked up.
    """

    def __init__(self, word: str) -> None:
        self.word = word
        super().__init__(f"Word not found in lexicon: {word!r}")


class AmbiguousWordError(LexiconError):
    """Raised when a polyphone cannot be disambiguated.

    This happens when a word has multiple lexicon entries and either no
    ``sense`` was supplied or the supplied ``sense`` does not match any
    entry.

    Attributes
    ----------
    word : str
        The ambiguous word.
    senses : tuple[str | None, ...]
        The senses available for this word.
    requested : str | None
        The sense that was requested, if any.
    """

    def __init__(
        self,
        word: str,
        senses: tuple[str | None, ...] = (),
        requested: str | None = None,
    ) -> None:
        self.word = word
        self.senses = senses
        self.requested = requested
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        available = ", ".join(repr(s) for s in self.senses) or "(none)"
        if self.requested is None:
            return (
                f"Word {self.word!r} is a polyphone with senses: {available}. "
                f"Pass sense= to disambiguate."
            )
        return (
            f"Word {self.word!r} has no entry with sense {self.requested!r}. "
            f"Available senses: {available}."
        )


class SyllableToneMismatchError(LexiconError):
    """Raised when a lexicon row has a different number of syllables and tones.

    Attributes
    ----------
    word : str | None
        The offending word, if known.
    n_syllables : int | None
        Number of syllables parsed.
    n_tones : int | None
        Number of tones parsed.
    """

    def __init__(
        self,
        message: str | None = None,
        *,
        word: str | None = None,
        n_syllables: int | None = None,
        n_tones: int | None = None,
    ) -> None:
        self.word = word
        self.n_syllables = n_syllables
        self.n_tones = n_tones
        if message is None:
            message = (
                f"Word {word!r}: {n_syllables} syllables but {n_tones} tones."
            )
        super().__init__(message)


class DataValidationError(LexiconError):
    """Raised when packaged data files are internally inconsistent.

    Examples: duplicate graphemes in ``segments.yaml``, missing required
    columns in ``lexicon.csv``, duplicate ``(word, sense)`` rows, or
    characters in syllables that no segment covers.
    """


# ---------------------------------------------------------------------------
# Tone errors
# ---------------------------------------------------------------------------
class UnknownToneError(ZomiG2PError):
    """Raised when a tone code has no mapping in ``tones.yaml``.

    Attributes
    ----------
    code : str | None
        The unknown tone code, if a single code was responsible.
    """

    def __init__(self, code: str | None = None, message: str | None = None) -> None:
        self.code = code
        if message is None:
            message = f"Unknown tone code: {code!r}"
        super().__init__(message)


# ---------------------------------------------------------------------------
# Conversion errors
# ---------------------------------------------------------------------------
class ConversionError(ZomiG2PError):
    """Base class for errors raised during conversion."""


class InvalidOutputError(ConversionError):
    """Raised when an unsupported ``output`` value is requested.

    Attributes
    ----------
    output : str
        The invalid output value.
    valid : tuple[str, ...]
        The supported output values.
    """

    def __init__(self, output: str, valid: tuple[str, ...] = ("ipa", "ascii")) -> None:
        self.output = output
        self.valid = valid
        super().__init__(
            f"output must be one of {valid}, got {output!r}"
        )