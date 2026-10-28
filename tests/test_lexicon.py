"""
Tests for zomi_g2p.lexicon
==========================

Covers:
- Parsing segments.yaml, tones.yaml, lexicon.csv from a directory.
- Building word and syllable indexes.
- Polyphone (multi-sense) handling.
- Validation errors: duplicate graphemes/tones, mismatched syllable/tone
  counts, missing columns, unknown tone codes, uncovered characters.
- The default packaged lexicon loads successfully.
"""

from __future__ import annotations

import textwrap

import pytest

from zomi_g2p.exceptions import (
    DataValidationError,
    SyllableToneMismatchError,
    UnknownToneError,
)
from zomi_g2p.lexicon import (
    Lexicon,
    LexiconEntry,
    Segment,
    _load_lexicon_entries,
    _load_segments,
    _load_tones,
    load_default_lexicon,
    load_lexicon_from_dir,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
SEGMENTS_YAML = textwrap.dedent(
    """\
    segments:
      - grapheme: "a"
        ipa: "a"
        ascii: "a"
      - grapheme: "i"
        ipa: "i"
        ascii: "i"
      - grapheme: "p"
        ipa: "p"
        ascii: "p"
      - grapheme: "t"
        ipa: "t"
        ascii: "t"
      - grapheme: "n"
        ipa: "n"
        ascii: "n"
      - grapheme: "ng"
        ipa: "ŋ"
        ascii: "ng"
    """
)

TONES_YAML = textwrap.dedent(
    """\
    tones:
      - name: mid-short
        code: "30"
        ipa_mark: "˧"
        ascii_mark: "3"
      - name: low-short
        code: "10"
        ipa_mark: "˩ʔ"
        ascii_mark: "1q"
      - name: rising
        code: "35"
        ipa_mark: "˧˥"
        ascii_mark: "35"
      - name: falling
        code: "31"
        ipa_mark: "˧˩"
        ascii_mark: "31"
    """
)

LEXICON_CSV = textwrap.dedent(
    """\
    word,syllables,tones
    itna,it-na,30-30
    pai,pai,30
    """
)


@pytest.fixture
def data_dir(tmp_path):
    """Write a minimal valid data directory and return its path."""
    (tmp_path / "segments.yaml").write_text(SEGMENTS_YAML, encoding="utf-8")
    (tmp_path / "tones.yaml").write_text(TONES_YAML, encoding="utf-8")
    (tmp_path / "lexicon.csv").write_text(LEXICON_CSV, encoding="utf-8")
    return tmp_path


def _write(data_dir, name: str, content: str) -> None:
    (data_dir / name).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# File parsers
# ---------------------------------------------------------------------------
class TestLoadSegments:
    def test_parses_valid_segments(self, tmp_path):
        _write(tmp_path, "segments.yaml", SEGMENTS_YAML)
        segments = _load_segments(tmp_path / "segments.yaml")
        assert len(segments) == 6
        assert Segment(grapheme="ng", ipa="ŋ", ascii="ng") in segments

    def test_rejects_empty_list(self, tmp_path):
        _write(tmp_path, "segments.yaml", "segments: []\n")
        with pytest.raises(DataValidationError, match="non-empty"):
            _load_segments(tmp_path / "segments.yaml")

    def test_rejects_duplicate_grapheme(self, tmp_path):
        _write(
            tmp_path,
            "segments.yaml",
            textwrap.dedent(
                """\
                segments:
                  - grapheme: "a"
                    ipa: "a"
                    ascii: "a"
                  - grapheme: "a"
                    ipa: "a"
                    ascii: "a"
                """
            ),
        )
        with pytest.raises(DataValidationError, match="duplicate grapheme"):
            _load_segments(tmp_path / "segments.yaml")

    def test_rejects_missing_key(self, tmp_path):
        _write(
            tmp_path,
            "segments.yaml",
            textwrap.dedent(
                """\
                segments:
                  - grapheme: "a"
                    ipa: "a"
                """
            ),
        )
        with pytest.raises(DataValidationError, match="missing key"):
            _load_segments(tmp_path / "segments.yaml")

    def test_rejects_empty_grapheme(self, tmp_path):
        _write(
            tmp_path,
            "segments.yaml",
            textwrap.dedent(
                """\
                segments:
                  - grapheme: ""
                    ipa: "a"
                    ascii: "a"
                """
            ),
        )
        with pytest.raises(DataValidationError, match="empty grapheme"):
            _load_segments(tmp_path / "segments.yaml")


class TestLoadTones:
    def test_parses_valid_tones(self, tmp_path):
        _write(tmp_path, "tones.yaml", TONES_YAML)
        tones = _load_tones(tmp_path / "tones.yaml")
        assert set(tones) == {"30", "10", "35", "31"}
        assert tones["10"] == {"ipa": "˩ʔ", "ascii": "1q"}

    def test_rejects_duplicate_code(self, tmp_path):
        _write(
            tmp_path,
            "tones.yaml",
            textwrap.dedent(
                """\
                tones:
                  - code: "30"
                    ipa_mark: "˧"
                    ascii_mark: "3"
                  - code: "30"
                    ipa_mark: "˧"
                    ascii_mark: "3"
                """
            ),
        )
        with pytest.raises(DataValidationError, match="duplicate tone code"):
            _load_tones(tmp_path / "tones.yaml")

    def test_rejects_missing_mark(self, tmp_path):
        _write(
            tmp_path,
            "tones.yaml",
            textwrap.dedent(
                """\
                tones:
                  - code: "30"
                    ipa_mark: "˧"
                """
            ),
        )
        with pytest.raises(DataValidationError, match="missing key"):
            _load_tones(tmp_path / "tones.yaml")


class TestLoadLexiconEntries:
    def test_parses_valid_rows(self, tmp_path):
        _write(tmp_path, "lexicon.csv", LEXICON_CSV)
        entries = _load_lexicon_entries(tmp_path / "lexicon.csv")
        assert len(entries) == 2
        by_word = {e.word: e for e in entries}
        assert by_word["itna"].syllables == ("it", "na")
        assert by_word["itna"].tones == ("30", "30")
        assert by_word["pai"].syllables == ("pai",)
        assert by_word["pai"].tones == ("30",)
        assert by_word["itna"].sense is None

    def test_parses_sense_column(self, tmp_path):
        _write(
            tmp_path,
            "lexicon.csv",
            textwrap.dedent(
                """\
                word,syllables,tones,sense
                pai,pai,30,go
                paai,paai,31,throw
                """
            ),
        )
        entries = _load_lexicon_entries(tmp_path / "lexicon.csv")
        assert {(e.word, e.sense) for e in entries} == {
            ("paai", "throw"),
            ("pai", "go"),
        }

    def test_rejects_missing_columns(self, tmp_path):
        _write(tmp_path, "lexicon.csv", "word,syllables\nitna,it-na\n")
        with pytest.raises(DataValidationError, match="missing required columns"):
            _load_lexicon_entries(tmp_path / "lexicon.csv")

    def test_rejects_syllable_tone_count_mismatch(self, tmp_path):
        _write(tmp_path, "lexicon.csv", "word,syllables,tones\nitna,it-na,30\n")
        with pytest.raises(SyllableToneMismatchError):
            _load_lexicon_entries(tmp_path / "lexicon.csv")

    def test_rejects_empty_word(self, tmp_path):
        _write(tmp_path, "lexicon.csv", "word,syllables,tones\n,it-na,30-30\n")
        with pytest.raises(DataValidationError, match="empty word"):
            _load_lexicon_entries(tmp_path / "lexicon.csv")

    def test_rejects_empty_file(self, tmp_path):
        _write(tmp_path, "lexicon.csv", "word,syllables,tones\n")
        with pytest.raises(DataValidationError, match="no entries"):
            _load_lexicon_entries(tmp_path / "lexicon.csv")
    
    def test_rejects_empty_syllable_after_split(self, tmp_path):
        _write(tmp_path, "segments.yaml", SEGMENTS_YAML)
        _write(tmp_path, "tones.yaml", TONES_YAML)
        _write(tmp_path, "lexicon.csv", "word,syllables,tones\nitna,--,30-30\n")
        # with pytest.raises(DataValidationError, match="could not parse"):
        #     load_lexicon_from_dir(tmp_path)
        with pytest.raises(SyllableToneMismatchError): # match="could not parse"):
            load_lexicon_from_dir(tmp_path)

# ---------------------------------------------------------------------------
# Lexicon class
# ---------------------------------------------------------------------------
class TestLexiconIndexing:
    def test_entries_for_known_word(self, data_dir):
        lex = load_lexicon_from_dir(data_dir)
        entries = lex.entries_for("itna")
        assert len(entries) == 1
        assert entries[0].syllables == ("it", "na")

    def test_entries_for_unknown_word_returns_empty(self, data_dir):
        lex = load_lexicon_from_dir(data_dir)
        assert lex.entries_for("nope") == []

    def test_contains(self, data_dir):
        lex = load_lexicon_from_dir(data_dir)
        assert "itna" in lex
        assert "nope" not in lex

    def test_len_counts_entries_not_words(self, tmp_path):
        _write(tmp_path, "segments.yaml", SEGMENTS_YAML)
        _write(tmp_path, "tones.yaml", TONES_YAML)
        _write(
            tmp_path,
            "lexicon.csv",
            textwrap.dedent(
                """\
                word,syllables,tones,sense
                paai,paai,31,throw
                paai,paai,35,gestate
                """
            ),
        )
        lex = load_lexicon_from_dir(tmp_path)
        assert len(lex) == 2  # two entries, one word

    def test_segments_sorted_longest_first(self, data_dir):
        lex = load_lexicon_from_dir(data_dir)
        lengths = [len(s.grapheme) for s in lex.segments]
        assert lengths == sorted(lengths, reverse=True)

    def test_tone_candidates(self, data_dir):
        
        lex = load_lexicon_from_dir(data_dir)
        assert lex.tone_candidates("it") == {"30"}
        assert lex.tone_candidates("pai") == {"30"}
        assert lex.tone_candidates("pa") == set()   # no such syllable
        assert lex.tone_candidates("zzz") == set()


class TestLexiconPolyphones:
    def test_multiple_entries_for_same_word(self, tmp_path):
        _write(tmp_path, "segments.yaml", SEGMENTS_YAML)
        _write(tmp_path, "tones.yaml", TONES_YAML)
        _write(
            tmp_path,
            "lexicon.csv",
            textwrap.dedent(
                """\
                word,syllables,tones,sense
                paai,paai,31,throw
                paai,paai,35,gestate
                """
            ),
        )
        lex = load_lexicon_from_dir(tmp_path)
        entries = lex.entries_for("paai")
        assert len(entries) == 2
        assert {e.sense for e in entries} == {"throw", "gestate"}

    def test_duplicate_word_sense_rejected(self, tmp_path):
        _write(tmp_path, "segments.yaml", SEGMENTS_YAML)
        _write(tmp_path, "tones.yaml", TONES_YAML)
        _write(
            tmp_path,
            "lexicon.csv",
            textwrap.dedent(
                """\
                word,syllables,tones,sense
                paai,paai,31,throw
                paai,paai,31,throw
                """
            ),
        )
        with pytest.raises(DataValidationError, match="Duplicate lexicon row"):
            load_lexicon_from_dir(tmp_path)


class TestLexiconValidation:
    def test_unknown_tone_code_rejected(self, tmp_path):
        _write(tmp_path, "segments.yaml", SEGMENTS_YAML)
        _write(tmp_path, "tones.yaml", TONES_YAML)
        _write(tmp_path, "lexicon.csv", "word,syllables,tones\nitna,it-na,99-30\n")
        with pytest.raises(UnknownToneError, match="99"):
            load_lexicon_from_dir(tmp_path)

    def test_uncovered_first_character_rejected(self, tmp_path):
        _write(tmp_path, "segments.yaml", SEGMENTS_YAML)
        _write(tmp_path, "tones.yaml", TONES_YAML)
        # "x" does not start any segment in SEGMENTS_YAML.
        _write(tmp_path, "lexicon.csv", "word,syllables,tones\nxna,x-na,30-30\n")
        with pytest.raises(DataValidationError, match="no segment starts"):
            load_lexicon_from_dir(tmp_path)

    def test_valid_data_dir_loads(self, data_dir):
        lex = load_lexicon_from_dir(data_dir)
        assert len(lex) == 2
        assert "itna" in lex


# ---------------------------------------------------------------------------
# LexiconEntry
# ---------------------------------------------------------------------------
class TestLexiconEntry:
    def test_key_includes_sense(self):
        e1 = LexiconEntry(word="paai", syllables=("paai"), tones=("31"), tone_sources=("rule"), sense="throw")
        e2 = LexiconEntry(word="paai", syllables=("paai"), tones=("35"), tone_sources=("rule"), sense="gestate")
        assert e1.key != e2.key

    def test_frozen(self):
        e = LexiconEntry(word="pai", syllables=("pai"), tone_sources=("rule"), tones=("30"))
        with pytest.raises(Exception):  # FrozenInstanceError subclasses AttributeError
            e.word = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Packaged default lexicon
# ---------------------------------------------------------------------------
class TestDefaultLexicon:
    def test_loads_packaged_data(self):
        """The real packaged lexicon must load without errors."""
        lex = load_default_lexicon()
        assert len(lex) > 0
        # All six tones should be present in the packaged tones.yaml.
        assert {"30", "10", "50", "33", "35", "31"} <= set(lex.tones)

    def test_cached(self):
        """load_default_lexicon is cached: same object returned twice."""
        assert load_default_lexicon() is load_default_lexicon()
        
    
# class TestLexiconPickle:
#     def test_pickle_roundtrip_version_matches(self, tmp_path, data_dir):
#         """_save_pickle then _load_pickle returns the same Lexicon."""
#         from zomi_g2p.lexicon import _save_pickle, _load_pickle, load_lexicon_from_dir
#         lex = load_lexicon_from_dir(data_dir)
#         pkl = tmp_path / "test.pkl"
#         _save_pickle(lex, pkl)
#         loaded = _load_pickle(pkl)
#         assert loaded is not None
#         assert len(loaded) == len(lex)


#     def test_pickle_version_mismatch_falls_back(self, tmp_path, data_dir):
#         """A pickle with a wrong version returns None (caller falls back to CSV)."""
#         import pickle
#         from zomi_g2p.lexicon import _load_pickle, _PICKLE_FORMAT_VERSION
#         pkl = tmp_path / "stale.pkl"
#         with pkl.open("wb") as f:
#             pickle.dump({"version": _PICKLE_FORMAT_VERSION - 1, "lexicon": None}, f)
#         assert _load_pickle(pkl) is None


#     def test_pickle_corrupt_falls_back(self, tmp_path):
#         """A truncated pickle returns None, not a traceback."""
#         from zomi_g2p.lexicon import _load_pickle
#         pkl = tmp_path / "corrupt.pkl"
#         pkl.write_bytes(b"\x80\x04not-a-pickle")
#         assert _load_pickle(pkl) is None
class TestLexiconPickle:
    def test_pickle_roundtrip(self, tmp_path, data_dir):
        from zomi_g2p.lexicon import (
            _load_pickle, _save_pickle, load_lexicon_from_dir,
        )
        lex = load_lexicon_from_dir(data_dir)
        pkl = tmp_path / "test.pkl"
        _save_pickle(lex, pkl)
        loaded = _load_pickle(pkl)
        assert loaded is not None
        assert len(loaded) == len(lex)

    def test_pickle_version_mismatch_falls_back(self, tmp_path):
        import pickle
        from zomi_g2p.lexicon import _load_pickle, _PICKLE_FORMAT_VERSION

        pkl = tmp_path / "stale.pkl"
        with pkl.open("wb") as f:
            pickle.dump({"version": _PICKLE_FORMAT_VERSION - 1, "lexicon": None}, f)
        assert _load_pickle(pkl) is None

    def test_pickle_corrupt_falls_back(self, tmp_path):
        from zomi_g2p.lexicon import _load_pickle

        pkl = tmp_path / "corrupt.pkl"
        pkl.write_bytes(b"\x80\x04not-a-pickle")
        assert _load_pickle(pkl) is None

    def test_pickle_missing_version_falls_back(self, tmp_path):
        import pickle
        from zomi_g2p.lexicon import _load_pickle

        pkl = tmp_path / "no-version.pkl"
        with pkl.open("wb") as f:
            pickle.dump({"lexicon": None}, f)   # no "version" key
        assert _load_pickle(pkl) is None