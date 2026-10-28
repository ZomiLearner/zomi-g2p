"""
zomi_g2p.rules
==============

Rule-based syllabification and tone assignment for Zomi.

Two roles:

1. **Fallback** — when a word is not in the lexicon, `syllabify()` and
   `predict_tones()` produce a best-effort pronunciation using
   phonological rules only.
2. **Data generation** — `generate_entry()` produces a `LexiconEntry`
   from a bare word, suitable for seeding a lexicon or training a
   neural G2P model.

The rules here are intentionally simple and transparent. They are not
a substitute for a curated lexicon; they are a starting point that can
be refined as linguistic knowledge grows.

Syllabification rules (v0.1)
----------------------------
Zomi syllables follow a (C)V(V)(C) shape. The algorithm:
1. Locate vowel graphemes using `segments.yaml`.
2. Each vowel (or vowel cluster) forms the nucleus of one syllable.
3. Assign consonants to syllables: onset goes with the following
   vowel; coda goes with the preceding vowel, following the maximal
   onset principle subject to Zomi phonotactics.
4. A final consonant that cannot be a valid coda joins the previous
   syllable's onset if possible; otherwise it forms its own syllable.

Tone rules (v0.1)
-----------------
- Single-vowel syllable → tone 30 (mid-short)
- Syllable with a long vowel (aa, ee, ii, oo, uu) or diphthong → tone 33 (mid-long)
- Final syllable with a glottal stop grapheme (') → tone 10 (low-short)
- These are placeholders; replace with real phonological rules as
  they are validated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from .lexicon import (
    LexiconEntry,
    Segment,
)
from .utils.provenance import (
    TONES_SOURCE_LEXICON,
    TONES_SOURCE_RULE,
)

logger = logging.getLogger("zomi_g2p.rules")


# Vowel graphemes: derived from segments.yaml at call time so the rule
# engine and the lexicon always agree on what counts as a vowel.
_LONG_VOWELS = frozenset({"aa", "ee", "ii", "oo", "uu"})
_DIPHTHONGS = frozenset({
    "ia", "iu", "ua", "ui", "ei", "eu", "ou", "oi", "ai", "au",
})


@dataclass(frozen=True)
class RuleResult:
    """Output of the rule engine for a single word."""

    word: str
    syllables: tuple[str, ...]
    tones: tuple[str, ...]
    tone_sources: tuple[str, ...]

    def to_entry(self, sense: str | None = None) -> LexiconEntry:
        """Convert to a LexiconEntry for use with the converter or lexicon."""
        return LexiconEntry(
            word=self.word,
            syllables=self.syllables,
            tones=self.tones,
            tone_sources=self.tone_sources,
            sense=sense,
        )


class RuleEngine:
    """Rule-based syllabification and tone assignment.

    Parameters
    ----------
    segments : Sequence[Segment]
        The segment inventory from ``segments.yaml``. Used to identify
        which graphemes are vowels and which are consonants.
    """

    def __init__(self, segments: Sequence[Segment]) -> None:
        self.segments = tuple(
            sorted(segments, key=lambda s: (-len(s.grapheme), s.grapheme))
        )
        # Graphemes that are vowels (their IPA contains a vowel symbol,
        # or they match the known vowel sets).
        self.vowel_graphemes = frozenset(
            s.grapheme for s in self.segments
            if self._is_vowel_grapheme(s.grapheme)
        )
        logger.debug(
            "RuleEngine initialized: %d vowels, %d segments",
            len(self.vowel_graphemes), len(self.segments),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze(self, word: str) -> RuleResult:
        """Syllabify and assign tones to a word using rules only."""
        syllables = self.syllabify(word)
        tones, sources = self.predict_tones(syllables)
        return RuleResult(
            word=word,
            syllables=tuple(syllables),
            tones=tuple(tones),
            tone_sources=tuple(sources),
        )

    def syllabify(self, word: str) -> list[str]:
        """Split a word into syllables using phonological rules.

        Returns a list of syllable strings. For an empty word, returns
        an empty list. For a word with no vowels, returns the whole word
        as a single syllable (best effort).
        """
        if not word:
            return []

        # 1. Identify vowel positions (longest-match).
        tokens = self._tokenize(word)
        vowel_indices = [
            i for i, (g, _) in enumerate(tokens) if g in self.vowel_graphemes
        ]

        if not vowel_indices:
            return [word]

        # 2. Each vowel is a nucleus. Distribute consonants.
        boundaries = self._syllable_boundaries(tokens, vowel_indices)
        return self._split_at(tokens, boundaries)

    def predict_tones(
        self, syllables: Sequence[str]
    ) -> tuple[list[str], list[str]]:
        """Assign a default tone to each syllable.

        Returns (tones, sources) where sources are all ``TONES_SOURCE_RULE``.
        """
        tones = []
        for syl in syllables:
            tones.append(self._default_tone(syl))
        sources = [TONES_SOURCE_RULE] * len(tones)
        return tones, sources

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _is_vowel_grapheme(self, grapheme: str) -> bool:
        """A grapheme is a vowel if it is in the known vowel sets or
        its IPA contains a vowel symbol."""
        if grapheme in _LONG_VOWELS or grapheme in _DIPHTHONGS:
            return True
        # Single-letter vowels: a, e, i, o, u, plus Zomi-specific.
        if grapheme in {"a", "e", "i", "o", "u", "aw"}:
            return True
        # Fallback: check the IPA mapping.
        for seg in self.segments:
            if seg.grapheme == grapheme:
                # Unicode IPA vowel range covers most vowels.
                return any(ch in "aeiouɛɔəɨʉɯ" for ch in seg.ipa)
        return False

    def _tokenize(self, word: str) -> list[tuple[str, int]]:
        """Longest-match tokenization of a word into graphemes.

        Returns list of (grapheme, start_index). Unknown characters
        are emitted as single-character tokens.
        """
        tokens = []
        i = 0
        while i < len(word):
            for seg in self.segments:
                if word.startswith(seg.grapheme, i):
                    tokens.append((seg.grapheme, i))
                    i += len(seg.grapheme)
                    break
            else:
                tokens.append((word[i], i))
                i += 1
        return tokens

    def _syllable_boundaries(
        self, tokens: list[tuple[str, int]], vowel_indices: list[int]
    ) -> list[int]:
        """Return token indices where syllables start.

        Simple rule: each vowel starts a new syllable, except that the
        first token of the word is always part of the first syllable.
        """
        boundaries = set(vowel_indices)
        boundaries.discard(0)   # first token belongs to first syllable
        if 0 not in boundaries:
            boundaries.add(0)
        return sorted(boundaries)

    def _split_at(
        self, tokens: list[tuple[str, int]], boundaries: list[int]
    ) -> list[str]:
        """Split the token list at the given token indices."""
        if not boundaries or boundaries[0] != 0:
            boundaries = [0] + boundaries
        result = []
        for start, end in zip(boundaries, boundaries[1:] + [len(tokens)]):
            syl = "".join(g for g, _ in tokens[start:end])
            result.append(syl)
        return result

    def _default_tone(self, syllable: str) -> str:
        """Default tone for a syllable, based on its vowel shape."""
        # Glottal stop grapheme at the end → low-short tone.
        if syllable.endswith("'"):
            return "10"
        for g in _LONG_VOWELS:
            if g in syllable:
                return "33"
        for g in _DIPHTHONGS:
            if g in syllable:
                return "33"
        return "30"
    
    