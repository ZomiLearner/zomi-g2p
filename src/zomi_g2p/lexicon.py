"""
zomi_g2p.lexicon
================

Data loading and indexing for zomi-g2p.

Responsibilities
----------------
- Load packaged data files (segments.yaml, tones.yaml, lexicon.csv)
  via importlib.resources so the package works after ``pip install``.
- Parse the CSV lexicon into ``LexiconEntry`` objects.
- Build indexes:
    * word -> list[LexiconEntry]        (supports polyphones via ``sense``)
    * syllable -> set[tone_code]        (for OOV fallback / diagnostics)
- Validate data consistency at load time and raise informative errors.

The CSV is expected to have columns: word, syllables, tone [, sense]
- ``syllables`` uses ``-`` to separate syllables.
- ``tone`` uses ``-`` to separate tone codes (one per syllable).
- ``sense`` is optional and used only for polyphones.
"""

from __future__ import annotations

import csv
import pathlib
import pickle
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from typing import Iterable, Mapping, NamedTuple, Sequence

# import yaml

from .exceptions import (
    AmbiguousWordError,
    DataValidationError,
    SyllableToneMismatchError,
    UnknownToneError,
    UnknownWordError,
    ZomiG2PError,
)

import logging
logger = logging.getLogger("zomi_g2p.lexicon")

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

# class LexiconEntry:
# @dataclass(frozen=True)
class LexiconEntry(NamedTuple):
    """One row of the lexicon CSV."""

    word: str
    syllables: tuple[str, ...]
    tones: tuple[str, ...]
    tone_sources: tuple[str, ...] # parallel to tones
    sense: str | None = None
    language: str | None = None # = "zol"
    orthography: str | None = None

    @property
    def key(self) -> tuple[str, str | None]:
        """(word, sense) — used to detect duplicate rows."""
        return (self.word, self.sense)


# @dataclass(frozen=True)
# class Segment:
class Segment(NamedTuple):
    """One grapheme -> (ipa, ascii) mapping."""

    grapheme: str
    ipa: str
    ascii: str


# ---------------------------------------------------------------------------
# Lexicon
# ---------------------------------------------------------------------------
class Lexicon:
    """Loaded, indexed lexicon plus segment and tone tables.

    Attributes
    ----------
    segments : tuple[Segment, ...]
        Sorted by grapheme length descending so longest-match wins.
    tones : dict[str, dict[str, str]]
        tone_code -> {"ipa": ..., "ascii": ...}
    """

    def __init__(
        self,
        segments: Sequence[Segment],
        tones: Mapping[str, Mapping[str, str]],
        entries: Iterable[LexiconEntry],
    ) -> None:
        logger.debug(
            "building lexicon index: %d words, %d segments, %d tone codes",
            # len(self._by_word), 
            # len(self.segments), len(self.tones),
            len(segments), len(tones),
        )
        
        # Sort segments longest-first to support longest-match conversion.
        self.segments: tuple[Segment, ...] = tuple(
            sorted(segments, key=lambda s: (-len(s.grapheme), s.grapheme))
        )
        self.tones: dict[str, dict[str, str]] = {
            code: {"ipa": marks["ipa"], "ascii": marks["ascii"]}
            for code, marks in tones.items()
        }

        self._by_word: dict[str, list[LexiconEntry]] = {}
        self._syllable_tones: dict[str, set[str]] = {}

        for entry in entries:
            # if len(entry.syllables) != len(entry.tones):
            #     raise SyllableToneMismatchError(
            #         f"Word '{entry.word}' (sense={entry.sense!r}): "
            #         f"{len(entry.syllables)} syllables but "
            #         f"{len(entry.tones)} tones."
            #     )
            self._by_word.setdefault(entry.word, []).append(entry)
            for syl, tone in zip(entry.syllables, entry.tones):
                self._syllable_tones.setdefault(syl, set()).add(tone)

        # Detect duplicate (word, sense) pairs — data error.
        seen: set[tuple[str, str | None]] = set()
        for word, entries_ in self._by_word.items():
            for entry in entries_:
                if entry.key in seen:
                    raise DataValidationError(
                        f"Duplicate lexicon row for word '{word}' "
                        f"with sense={entry.sense!r}."
                    )
                seen.add(entry.key)

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------
    def entries_for(self, word: str) -> list[LexiconEntry]:
        """Return all entries for a word (empty list if unknown)."""
        return list(self._by_word.get(word, ()))

    def tone_candidates(self, syllable: str) -> set[str]:
        """Return the set of tone codes observed for a syllable."""
        return set(self._syllable_tones.get(syllable, ()))

    def __len__(self) -> int:
        return sum(len(v) for v in self._by_word.values())

    def __contains__(self, word: object) -> bool:
        return isinstance(word, str) and word in self._by_word

    def words(self) -> Iterable[str]:
        return self._by_word.keys()


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
_PICKLE_FORMAT_VERSION = 3  # bump from 1 when class layout changes

def _save_pickle(lexicon: Lexicon, path: Path) -> None:
    payload ={"version": _PICKLE_FORMAT_VERSION, "lexicon": lexicon}
    with path.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
        
# def _load_pickle(path) -> Lexicon | None:
#     try:
#         with path.open("rb") as f:
#             payload = pickle.load(f)
#     except (pickle.UnpicklingError, AttributeError, TypeError, EOFError) as exc:
#         logger.warning("lexicon.pkl unusable (%s); falling back to CSV", exc)
#         return None
#     if not isinstance(payload, dict) or payload.get("version") != _PICKLE_FORMAT_VERSION:
#         logger.warning("lexicon.pkl has old format; falling back to CSV")
#         return None
#     return payload["lexicon"]
def _load_pickle(path) -> Lexicon | None:
    try:
        with path.open("rb") as f:
            payload = pickle.load(f)
    except (pickle.UnpicklingError, AttributeError, TypeError,
            EOFError, ModuleNotFoundError) as exc:
        logger.warning("lexicon.pkl unreadable (%s); falling back to CSV", exc)
        return None

    if not isinstance(payload, dict) or "version" not in payload:
        logger.warning("lexicon.pkl has no version field; falling back to CSV")
        return None

    if payload["version"] != _PICKLE_FORMAT_VERSION:
        logger.warning(
            "lexicon.pkl format %r != expected %r; falling back to CSV",
            payload["version"], _PICKLE_FORMAT_VERSION,
        )
        return None

    return payload["lexicon"]

# @lru_cache(maxsize=1)
# def load_default_lexicon() -> Lexicon:
#     """Load the packaged lexicon (cached)."""
#     data_root = files("zomi_g2p").joinpath("data")
#     # print(data_root)
#     return load_lexicon_from_dir(data_root)

# @lru_cache(maxsize=1)
# def load_default_lexicon() -> Lexicon:
#     data_root = files("zomi_g2p").joinpath("data")
#     pkl = data_root.joinpath("lexicon.pkl")
#     if pkl.is_file():
#         with pkl.open("rb") as f:
#             return pickle.load(f)
#     logger.debug("lexicon.pkl not found; parsing CSVs")
#     return load_lexicon_from_dir(data_root)

@lru_cache(maxsize=1)
def load_default_lexicon() -> Lexicon:
    data_root = files("zomi_g2p").joinpath("data")
    pkl = data_root.joinpath("lexicon.pkl")
    if pkl.is_file():
        try:
            # with pkl.open("rb") as f:
            #     return pickle.load(f)
            lex = _load_pickle(pkl)
            if lex is not None:
                return lex
        except (pickle.UnpicklingError, AttributeError,TypeError, 
                EOFError, ModuleNotFoundError, OSError) as exc:
            logger.warning("lexicon.pkl unusable (%s); falling back to CSV", exc)
            return None
    # return load_lexicon_from_dir(data_root)
    lex = load_lexicon_from_dir(data_root)
    # Optional: try to rewrite the stale pickle (skip if read-only install,
    # e.g., system site-packages).
    try:
        _save_pickle(lex, pkl)
    except OSError:
        pass
    return lex

# def load_lexicon_from_dir(data_root) -> Lexicon:
#     """Load segments/tones/lexicon from a directory (Traversable)."""
#     segments = _load_segments(data_root.joinpath("segments.yaml"))
#     tones = _load_tones(data_root.joinpath("tones.yaml"))
#     entries = _load_lexicon_entries(data_root.joinpath("lexicon.csv"))
#     lexicon = Lexicon(segments=segments, tones=tones, entries=entries)
#     _validate(lexicon)
#     return lexicon

def _coerce_traversable(data_dir):
    if hasattr(data_dir, "joinpath"):
        return data_dir
    return pathlib.Path(data_dir)

def load_lexicon_from_dir(
    data_dir,
    *,
    validate: bool = True,
) -> Lexicon:
    """Load a Zomi G2P lexicon from a data directory.

    The directory must contain exactly three files:

    - ``lexicon.csv`` — required columns ``word``, ``syllables``, ``tone``;
      optional column ``sense``. Syllables and tone codes are separated
      by ``-``.
    - ``segments.yaml`` — a ``segments`` list of ``{grapheme, ipa, ascii}``
      mappings. Order does not matter; the loader sorts by grapheme length
      descending so longest-match wins.
    - ``tones.yaml`` — a ``tones`` list of ``{code, ipa_mark, ascii_mark}``
      entries. All six Zomi tones (``30``, ``10``, ``50``, ``33``, ``35``,
      ``31``) should be present.

    Parameters
    ----------
    data_dir : str | os.PathLike | importlib.resources.abc.Traversable
        Directory containing the three files. Accepts a real path or a
        ``Traversable`` returned by ``importlib.resources.files()``, so the
        same function works for installed packages and zip imports.
    validate : bool, default True
        If True, run cross-file consistency checks after parsing:

        - every tone code in ``lexicon.csv`` exists in ``tones.yaml``;
        - every syllable's first character is covered by ``segments.yaml``;
        - no duplicate ``(word, sense)`` pairs.

        Set to False only when loading intentionally malformed data
        (e.g., in tests that exercise the error paths). The returned
        ``Lexicon`` still validates syllable/tone counts per row in its
        constructor.

    Returns
    -------
    Lexicon
        Indexed lexicon with ``segments``, ``tones``, and per-word entries.

    Raises
    ------
    DataValidationError
        If a file is malformed, a required column is missing, a duplicate
        grapheme/tone code appears, or (when ``validate=True``) a syllable's
        first character is uncovered or a ``(word, sense)`` pair is duplicated.
    SyllableToneMismatchError
        If any ``lexicon.csv`` row has a different number of syllables and
        tones.
    UnknownToneError
        If (when ``validate=True``) a tone code in ``lexicon.csv`` is missing
        from ``tones.yaml``.
    FileNotFoundError
        If any of the three files is absent from ``data_dir``.
    """
    data_dir = _coerce_traversable(data_dir)

    segments = _load_segments(data_dir.joinpath("segments.yaml"))
    # print(f"type(segments): {type(segments), type(segments[0]), segments}")
    tones = _load_tones(data_dir.joinpath("tones.yaml"))
    entries = _load_lexicon_entries(data_dir.joinpath("lexicon.csv"), segments)

    lexicon = Lexicon(segments=segments, tones=tones, entries=entries)

    if validate:
        _validate(lexicon)

    return lexicon

# ---------------------------------------------------------------------------
# File parsers
# ---------------------------------------------------------------------------
def _load_segments(path) -> list[Segment]:
    import yaml   # deferred
    logger.debug("loading segments from %s", path)
    
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    items = raw.get("segments")
    if not isinstance(items, list) or not items:
        raise DataValidationError("segments.yaml must contain a non-empty 'segments' list.")

    segments: list[Segment] = []
    seen: set[str] = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise DataValidationError(f"segments.yaml item #{i} is not a mapping.")
        try:
            grapheme = item["grapheme"]
            ipa = item["ipa"]
            ascii_ = item["ascii"]
        except KeyError as exc:
            raise DataValidationError(
                f"segments.yaml item #{i} missing key: {exc.args[0]!r}"
            ) from exc
        if not isinstance(grapheme, str) or not grapheme:
            raise DataValidationError(f"segments.yaml item #{i}: empty grapheme.")
        if grapheme in seen:
            raise DataValidationError(f"segments.yaml: duplicate grapheme {grapheme!r}.")
        seen.add(grapheme)
        segments.append(Segment(grapheme=grapheme, ipa=str(ipa), ascii=str(ascii_)))
    
    logger.debug("loaded %d segments", len(segments))
    return segments


def _load_tones(path) -> dict[str, dict[str, str]]:
    import yaml   # deferred
    logger.debug("loading tones from %s", path)
    
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    items = raw.get("tones")
    if not isinstance(items, list) or not items:
        raise DataValidationError("tones.yaml must contain a non-empty 'tones' list.")

    tones: dict[str, dict[str, str]] = {}
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise DataValidationError(f"tones.yaml item #{i} is not a mapping.")
        try:
            code = str(item["code"])
            ipa_mark = item["ipa_mark"]
            ascii_mark = item["ascii_mark"]
        except KeyError as exc:
            raise DataValidationError(
                f"tones.yaml item #{i} missing key: {exc.args[0]!r}"
            ) from exc
        if code in tones:
            raise DataValidationError(f"tones.yaml: duplicate tone code {code!r}.")
        tones[code] = {"ipa": str(ipa_mark), "ascii": str(ascii_mark)}
    
    logger.debug("loaded %d tone codes: %s", len(tones), sorted(tones))
    return tones

_VOWEL_GRAPHEMES: set[str] = set()      # filled from segments.yaml
_LONG_VOWELS: set[str] = {"aa", "ee", "ii", "oo", "uu"}
_DIPHTHONGS: set[str] = {"ia", "iu", "ua", "ui", "ei", "eu", "ou", "oi", "ai", "au"}

# def _default_tone_for_syllable(syllable: str, segments: Sequence[Segment]) -> str:
# def _default_tone_for_syllable(syllable: str, sorted_grams: Sequence[Segment]) -> str:
#     """Return the default tone code for a syllable.

#     Rule: if the syllable contains a long-vowel grapheme or a diphthong,
#     return "33" (mid-long); otherwise "30" (mid-short).
#     """
#     # grams = {s.grapheme for s in segments}
#     # Longest-match scan: identify which graphemes the syllable is made of.
#     matched: list[str] = []
#     i = 0
#     while i < len(syllable):
#         # for g in sorted(grams, key=len, reverse=True):
#         for g in sorted_grams:
#             if syllable.startswith(g, i):
#                 matched.append(g)
#                 i += len(g)
#                 break
#         else:
#             i += 1  # unknown character; skip
#     if any(g in _LONG_VOWELS for g in matched):
#         return "33"
#     if any(g in _DIPHTHONGS for g in matched):
#         return "33"
#     return "30"
_LONG_OR_DIPHTHONG = {"aa", "ee", "ii", "oo", "uu",
                       "ia", "iu", "ua", "ui", "ei", "eu", "ou", "oi", "ai", "au"}

def _default_tone_for_syllable(syllable: str, second) -> str:
    for g in _LONG_OR_DIPHTHONG:
        if g in syllable:
            return "33"
    return "30"

def _load_lexicon_entries(path, segments: Sequence[Segment] = None) -> list[LexiconEntry]: 
    
    logger.debug("loading lexicon from %s", path)
    
    entries: list[LexiconEntry] = []
    default_filled = 0
    
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"word", "syllables", "tones"}
        fieldnames = set(reader.fieldnames or ())
        missing = required - fieldnames
        if missing:
            raise DataValidationError(
                f"lexicon.csv missing required columns: {sorted(missing)}"
            )
        if "sense" not in fieldnames:
            # Treat missing sense column as all-None.
            pass
        
        # if segments is None:
        #     segments = _load_segments(path.parent / "segments.yaml")
        if segments is not None:
            sorted_grams = sorted({s.grapheme for s in segments}, key=len, reverse=True)

        for line_no, row in enumerate(reader, start=2):  # header is line 1
            word = (row.get("word") or "").strip()
            syl_raw = (row.get("syllables") or "").strip()
            tone_raw = (row.get("tones") or "").strip()
            sense_raw = (row.get("sense") or "").strip()
            sense = sense_raw or None

            if not word:
                raise DataValidationError(f"lexicon.csv line {line_no}: empty word.")
            if not syl_raw: # or not tone_raw:
                raise DataValidationError(
                    f"lexicon.csv line {line_no}: empty syllables or tones."
                )

            syllables = tuple(s for s in syl_raw.split("-") if s)
            tones = tuple(t for t in tone_raw.split("-") if t)
            
            
            
            if not tone_raw:
                # tones = tuple(_default_tone_for_syllable(s, segments) for s in syllables)
                tones = tuple(_default_tone_for_syllable(s, sorted_grams) for s in syllables)
                tone_sources = tuple("rule" for _ in syllables)
                default_filled += 1
                logger.debug(
                    "line %d (word %r): applied default tones %s", line_no, word, tones
                )
            else:
                tones = tuple(t for t in tone_raw.split("-") if t)
                tone_sources = tuple("lexicon" for _ in tones)
                if len(syllables) != len(tones):
                    raise SyllableToneMismatchError(
                    f"lexicon.csv line {line_no} (word '{word}'): "
                    f"{len(syllables)} syllables but {len(tones)} tones."
                )
                    
            if not syllables:# or not tones:
                raise DataValidationError(
                    f"lexicon.csv line {line_no}: could not parse syllables/tones."
                )
            # if len(syllables) != len(tones):
            #     raise SyllableToneMismatchError(
            #         f"lexicon.csv line {line_no} (word '{word}'): "
            #         f"{len(syllables)} syllables but {len(tones)} tones."
            #     )

            entries.append(
                LexiconEntry(
                    word=word,
                    syllables=syllables,
                    tones=tones,
                    tone_sources=tone_sources,
                    sense=sense,
                    # language=row.get("language"),
                    # orthography=row.get("orthography"),
                )
            )

    logger.info(
        "loaded %d lexicon entries (%d with default tones) from %s",
        len(entries), default_filled, path,
    )
    if not entries:
        raise DataValidationError("lexicon.csv contains no entries.")
    return entries


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _validate(lexicon: Lexicon) -> None:
    """Cross-file consistency checks."""
    
    logger.debug("validating lexicon (%d entries, %d tones, %d segments)",
        len(lexicon), len(lexicon.tones), len(lexicon.segments))

    # 1. Every tone code used in the lexicon must exist in tones.yaml.
    known_tones = set(lexicon.tones)
    bad: set[str] = set()
    for word in lexicon.words():
        for entry in lexicon.entries_for(word):
            for tone in entry.tones:
                if tone not in known_tones:
                    bad.add(tone)
    if bad:
        logger.error("unknown tone codes in lexicon: %s", sorted(bad))
        raise UnknownToneError(
            f"Tone codes used in lexicon.csv but missing from tones.yaml: {sorted(bad)}"
        )

    # 2. Every character in every syllable must be coverable by segments.
    #    We check that at least one segment starts with the first character;
    #    the converter itself does longest-match and passes through unknown
    #    characters, but a completely uncovered alphabet is a data error.
    covered_first_chars = {seg.grapheme[0] for seg in lexicon.segments if seg.grapheme}
    uncovered: set[str] = set()
    for word in lexicon.words():
        for entry in lexicon.entries_for(word):
            for syl in entry.syllables:
                if not syl:
                    continue
                if syl[0] not in covered_first_chars:
                    uncovered.add(syl[0])
    if uncovered:
        logger.warning(
            "uncovered characters in syllables: %s — these will pass through "
            "unchanged during conversion", sorted(uncovered),
        )
        raise DataValidationError(
            f"Characters appear in syllables but no segment starts with them: "
            f"{sorted(uncovered)}"
        )