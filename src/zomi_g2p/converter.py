"""
zomi_g2p.converter
==================

Core Grapheme-to-Phoneme conversion for the Zomi language.

Supports:
- Two output representations: IPA and ASCII.
- Six-tone system (30, 10, 50, 33, 35, 31) appended per syllable.
- Word-level lookup from a packaged lexicon (CSV).
- Polyphone disambiguation via an optional ``sense`` argument.

The converter does not infer tones from spelling. Tones come from the
lexicon, which is the authoritative source.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .exceptions import (
    AmbiguousWordError,
    SyllableToneMismatchError,
    UnknownToneError,
    UnknownWordError,
    InvalidOutputError,
)
from .lexicon import Lexicon, LexiconEntry
# from .rules import RuleEngine

import logging

logger = logging.getLogger("zomi_g2p.converter")

# Tone letters per tone code. Kept here for reference only; the actual
# marks are loaded from data/tones.yaml by Lexicon. This mapping is used
# as a fallback if tones.yaml is missing a code.
_FALLBACK_TONES = {
    "30": {"ipa": "˧", "ascii": "3"},
    "10": {"ipa": "˩ʔ", "ascii": "1q"},
    "50": {"ipa": "˥", "ascii": "5"},
    "33": {"ipa": "˧ː", "ascii": "33"},
    "35": {"ipa": "˧˥", "ascii": "35"},
    "31": {"ipa": "˧˩", "ascii": "31"},
}

_VALID_OUTPUTS = ("ipa", "ascii")

from .utils.provenance import TONES_SOURCE_LEXICON
# from .utils.helpers import _reconcile

@property
def tone_source(self) -> str:
    """The least-trusted source across syllables (pessimistic)."""
    order = {"lexicon": 0, "rule": 1, "model": 2, "unknown": 3}
    return max(self.tone_sources, key=lambda s: order.get(s, 99))

@dataclass(frozen=True)
class ConversionResult:
    """Result of a single word conversion."""

    word: str
    syllables: Sequence[str]
    tones: Sequence[str]
    tone_sources: tuple[str, ...]     # parallel to tones, e.g. ("lexicon", "rule", "neural")
    phonemes: Sequence[str]  # one converted string per syllable
    
    # Output configuration
    output: str = ""
    with_tone: bool = True
    language: str | None = None # "zol" # ISO 639-3 for Zomi
    orthography: str | None = None # "standard" | "dialect:<name>" | None

    def joined(self, sep: str = " ") -> str:
        """Join the per-syllable phoneme strings."""
        return sep.join(self.phonemes)


class ZomiG2P:
    """Grapheme-to-Phoneme converter for Zomi.

    Parameters
    ----------
    lexicon : Lexicon
        Loaded lexicon (word -> entries, syllable -> tone candidates).
    syllable_sep : str, default "-"
        Separator used when joining syllables in output. IPA and ASCII
        outputs typically use a space; this parameter controls the
        ``joined`` convenience method.
    """

    def __init__(self, lexicon: Lexicon, *, language="zol", orthography=None, 
                 syllable_sep: str = " ", rule_engine=None
                #  reconcile: bool = False
                 ) -> None:
        self.lexicon = lexicon
        self.language = language
        self.orthography = orthography
        self.syllable_sep = syllable_sep
        # self.rule_engine = rule_engine or RuleEngine(lexicon.segments)
        # self._reconcile = reconcile

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def convert(
        self,
        word: str,
        output: str = "ipa",
        with_tone: bool = True,
        sense: str | None = None,
    ) -> ConversionResult:
        """Convert a single word to its phoneme representation.

        Parameters
        ----------
        word : str
            The orthographic form to convert. Must exist in the lexicon.
        output : {"ipa", "ascii"}
            Output representation.
        with_tone : bool, default True
            Whether to append the tone mark to each syllable.
        sense : str, optional
            For polyphones, the sense tag used to select the correct
            entry. Required when the word has multiple entries.

        Returns
        -------
        ConversionResult
            Structured result; call ``.joined()`` for a plain string.

        Raises
        ------
        UnknownWordError
            If ``word`` is not in the lexicon.
        AmbiguousWordError
            If the word has multiple entries and ``sense`` is not given
            or does not match any entry.
        UnknownToneError
            If a tone code in the lexicon has no mapping.
        SyllableToneMismatchError
            If the lexicon entry is internally inconsistent.
        ValueError
            If ``output`` is not one of the supported values.
        """
        
        logger.debug("convert word=%r output=%s with_tone=%s sense=%r",
            word, output, with_tone, sense)
        
        self._validate_output(output)
        entry = self._select_entry(word, sense)
        # try:
        #     entry = self._select_entry(word, sense)
        #     # if self._reconcile:
        #     #     entry = self._reconcile(entry)
        # except UnknownWordError:
        #     if not self.rule_engine:
        #         raise
        #     logger.info("word %r not in lexicon; using rule engine", word)
        #     result = self.rule_engine.analyze(word)
        #     entry = result.to_entry(sense=sense)
            
        # if len(entry.syllables) != len(entry.tones):
        #     raise SyllableToneMismatchError(
        #         f"Word '{word}': {len(entry.syllables)} syllables but "
        #         f"{len(entry.tones)} tones."
        #     )

        phonemes: list[str] = []
        for syllable, tone_code in zip(entry.syllables, entry.tones):
            seg = self._convert_segments(syllable, output)
            if with_tone:
                seg += self._tone_mark(tone_code, output)
            phonemes.append(seg)

        result = ConversionResult(
            word=word,
            syllables=tuple(entry.syllables),
            tones=tuple(entry.tones),
            tone_sources=tuple(entry.tone_sources),
            phonemes=tuple(phonemes),
            output=output,
            with_tone=with_tone,
            language=entry.language or self.language,      # see below
            orthography=entry.orthography or self.orthography,
        )
        
        logger.debug("  -> syllables=%s tones=%s phonemes=%s",
                 result.syllables, result.tones, result.phonemes)
        return result

    def convert_text(
        self,
        text: str,
        output: str = "ipa",
        with_tone: bool = True,
        sense: str | None = None,
        unknown: str = "raise",
    ) -> str:
        """Convert a whitespace-separated string of words.

        Parameters
        ----------
        text : str
            Whitespace-separated words.
        output, with_tone, sense
            Forwarded to :meth:`convert`.
        unknown : {"raise", "keep", "skip"}
            Behaviour for unknown words:
            - "raise": raise ``UnknownWordError`` (default).
            - "keep": keep the original token unchanged.
            - "skip": drop the token.
        """
        if unknown not in ("raise", "keep", "skip"):
            raise ValueError(f"unknown must be 'raise', 'keep' or 'skip', got {unknown!r}")

        parts: list[str] = []
        
        tokens = text.split()
        logger.debug("convert_text: %d tokens, unknown=%s", len(tokens), unknown)
        for token in tokens:
            try:
                parts.append(self.convert(token, output=output, with_tone=with_tone, sense=sense).joined(self.syllable_sep))
            except UnknownWordError:
                logger.warning("OOV word %r (policy=%s)", token, unknown)
                if unknown == "raise":
                    raise
                if unknown == "keep":
                    parts.append(token)
                # "skip": do nothing
        return self.syllable_sep.join(parts)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _validate_output(self, output: str) -> None:
        if output not in _VALID_OUTPUTS:
            raise InvalidOutputError(output, valid=_VALID_OUTPUTS)
            # raise InvalidOutputError(
            #     f"output must be one of {_VALID_OUTPUTS}, got {output!r}"
            # )

    # def _select_entry(self, word: str, sense: str | None) -> LexiconEntry:
    #     entries = self.lexicon.entries_for(word)
    #     if not entries:
    #         raise UnknownWordError(word)
    #     if len(entries) == 1:
    #         # Single entry: sense mismatch is a caller error only if a sense
    #         # was given and the entry has a *different* sense.
    #         entry = entries[0]
    #         # if sense is not None and entries[0].sense not in (None, sense):
    #         if sense is not None and entry.sense != sense:
    #             raise AmbiguousWordError(
    #                 f"Word '{word}' has one entry with sense "
    #                 f"{entries[0].sense!r}, not {sense!r}."
    #             )
    #         return entries[0]
    #     # Multiple entries: disambiguate by sense.
    #     if sense is None:
    #         senses = ", ".join(repr(e.sense) for e in entries)
    #         raise AmbiguousWordError(
    #             f"Word '{word}' is a polyphone with senses: {senses}. "
    #             f"Pass sense= to disambiguate."
    #         )
    #     matches = [e for e in entries if e.sense == sense]
    #     if not matches:
    #         senses = ", ".join(repr(e.sense) for e in entries)
    #         raise AmbiguousWordError(
    #             f"Word '{word}' has no entry with sense {sense!r}. "
    #             f"Available senses: {senses}."
    #         )
    #     if len(matches) > 1:
    #         raise AmbiguousWordError(
    #             f"Word '{word}' has multiple entries with sense {sense!r}."
    #         )
    #     return matches[0]
    def _select_entry(self, word: str, sense: str | None) -> LexiconEntry:
        entries = self.lexicon.entries_for(word)
        if not entries:
            raise UnknownWordError(word)
        if len(entries) == 1:
            # Single entry: sense mismatch is a caller error only if a sense
            # was given and the entry has a *different* sense.
            entry = entries[0]
            if sense is not None and entry.sense != sense:
                logger.warning(
                    "word %r has one entry (sense=%r); ignoring requested sense=%r",
                    word, entries[0].sense, sense,
                )
                raise AmbiguousWordError(
                    word=word,
                    senses=(entry.sense,),
                    requested=sense,
                )
            return entry
        # Multiple entries: disambiguate by sense.
        senses = tuple(e.sense for e in entries)
        if sense is None:
            raise AmbiguousWordError(word=word, senses=senses, requested=None)
        matches = [e for e in entries if e.sense == sense]
        if not matches:
            raise AmbiguousWordError(word=word, senses=senses, requested=sense)
        return matches[0]

    def _convert_segments(self, syllable: str, output: str) -> str:
        """Convert one syllable's graphemes to a phoneme string.

        Longest-match-first using the ``segments`` mapping from
        ``segments.yaml``. Characters not present in the mapping are
        passed through unchanged (typically punctuation or apostrophes).
        """
        segments = self.lexicon.segments  # list of (grapheme, ipa, ascii), sorted by len desc
        result: list[str] = []
        i = 0
        while i < len(syllable):
            # for grapheme, ipa, ascii_ in segments:
            #     if syllable.startswith(grapheme, i):
            #         result.append(ipa if output == "ipa" else ascii_)
            #         i += len(grapheme)
            #         break
            for seg in segments:
                if syllable.startswith(seg.grapheme, i):
                    result.append(seg.ipa if output == "ipa" else seg.ascii)
                    i += len(seg.grapheme)
                    break
            else:
                # Unknown grapheme: pass through.
                logger.debug("syllable %r: unknown grapheme %r passed through", syllable, syllable[i])
                result.append(syllable[i])
                i += 1
        return "".join(result)

    def _tone_mark(self, tone_code: str, output: str) -> str:
        """Return the tone mark for a tone code in the given output format."""
        tone = self.lexicon.tones.get(tone_code)
        # if tone is None:
        #     tone = _FALLBACK_TONES.get(tone_code)
        # if tone is None:
        #     raise UnknownToneError(tone_code)
        mark = tone["ipa"] if output == "ipa" else tone["ascii"]
        logger.debug("tone %r -> %r", tone_code, mark)
        return mark