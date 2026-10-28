"""
Tests for zomi_g2p.converter
============================

Covers:
- Segmental phoneme conversion in IPA and ASCII.
- Tone tagging per syllable (six-tone system).
- ``with_tone=False`` suppresses tone marks.
- ``ConversionResult`` structure and ``.joined()``.
- Polyphone disambiguation via ``sense``.
- ``convert_text`` with unknown="raise"/"keep"/"skip".
- Error paths: UnknownWordError, AmbiguousWordError, UnknownToneError,
  InvalidOutputError, SyllableToneMismatchError.

Uses synthetic fixtures (not the packaged data) so expectations are stable
regardless of what the real lexicon.csv contains. Packaged-data integrity is
covered by test_data.py.
"""

from __future__ import annotations

import textwrap

import pytest

from zomi_g2p.converter import ConversionResult, ZomiG2P
from zomi_g2p.exceptions import (
    AmbiguousWordError,
    InvalidOutputError,
    SyllableToneMismatchError,
    UnknownToneError,
    UnknownWordError,
)
from zomi_g2p.lexicon import load_lexicon_from_dir


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
      - grapheme: "t"
        ipa: "t"
        ascii: "t"
      - grapheme: "n"
        ipa: "n"
        ascii: "n"
      - grapheme: "p"
        ipa: "p"
        ascii: "p"
      - grapheme: "l"
        ipa: "l"
        ascii: "l"
      - grapheme: "ng"
        ipa: "ŋ"
        ascii: "ng"
      - grapheme: "aw"
        ipa: "ɔ"
        ascii: "o"
      - grapheme: "'"
        ipa: "ʔ"
        ascii: "q"
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
      - name: high-short
        code: "50"
        ipa_mark: "˥"
        ascii_mark: "5"
      - name: mid-long
        code: "33"
        ipa_mark: "˧ː"
        ascii_mark: "33"
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
    paai,paai,33
    lawng,lawng,10
    """
)


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "segments.yaml").write_text(SEGMENTS_YAML, encoding="utf-8")
    (tmp_path / "tones.yaml").write_text(TONES_YAML, encoding="utf-8")
    (tmp_path / "lexicon.csv").write_text(LEXICON_CSV, encoding="utf-8")
    return tmp_path


@pytest.fixture
def g2p(data_dir):
    return ZomiG2P(load_lexicon_from_dir(data_dir))


def _write(data_dir, name: str, content: str) -> None:
    (data_dir / name).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Basic conversion
# ---------------------------------------------------------------------------
class TestConvertBasic:
    def test_itna_ipa(self, g2p):
        result = g2p.convert("itna", output="ipa")
        assert result.phonemes == ("it˧", "na˧")
        assert result.joined() == "it˧ na˧"

    def test_itna_ascii(self, g2p):
        result = g2p.convert("itna", output="ascii")
        assert result.phonemes == ("it3", "na3")
        assert result.joined() == "it3 na3"

    def test_pai_single_syllable_ipa(self, g2p):
        result = g2p.convert("pai", output="ipa")
        assert result.syllables == ("pai",)
        assert result.tones == ("30",)
        assert result.joined() == "pai˧"

    def test_paai_mid_long_ipa(self, g2p):
        result = g2p.convert("paai", output="ipa")
        assert result.joined() == "paai˧ː"

    def test_paai_mid_long_ascii(self, g2p):
        result = g2p.convert("paai", output="ascii")
        assert result.joined() == "paai33"

    def test_lawng_low_short_glottal_ipa(self, g2p):
        # "aw" -> ɔ, "ng" -> ŋ, tone 10 -> ˩ʔ
        result = g2p.convert("lawng", output="ipa")
        assert result.joined() == "lɔŋ˩ʔ"

    def test_lawng_low_short_ascii(self, g2p):
        result = g2p.convert("lawng", output="ascii")
        assert result.joined() == "long1q"

    def test_longest_match_ng_before_n(self, g2p):
        # "ng" must be matched before "n" + "g" (g has no segment, so
        # if longest-match failed we'd see "n" + "g" passed through).
        result = g2p.convert("lawng", output="ipa")
        assert "ŋ" in result.joined()

    def test_result_fields(self, g2p):
        result = g2p.convert("itna", output="ipa")
        assert isinstance(result, ConversionResult)
        assert result.word == "itna"
        assert result.output == "ipa"
        assert result.with_tone is True

    def test_joined_custom_separator(self, g2p):
        result = g2p.convert("itna", output="ipa")
        assert result.joined(sep="-") == "it˧-na˧"
        assert result.joined(sep="") == "it˧na˧"


# ---------------------------------------------------------------------------
# with_tone
# ---------------------------------------------------------------------------
class TestWithTone:
    def test_with_tone_false_ipa(self, g2p):
        result = g2p.convert("itna", output="ipa", with_tone=False)
        assert result.joined() == "it na"
        assert result.with_tone is False

    def test_with_tone_false_ascii(self, g2p):
        result = g2p.convert("paai", output="ascii", with_tone=False)
        assert result.joined() == "paai"

    def test_with_tone_false_no_glottal_from_tone(self, g2p):
        # Tone 10 contributes ʔ; with_tone=False removes it.
        result = g2p.convert("lawng", output="ipa", with_tone=False)
        assert "ʔ" not in result.joined()


# ---------------------------------------------------------------------------
# Polyphones
# ---------------------------------------------------------------------------
POLYPHONE_CSV = textwrap.dedent(
    """\
    word,syllables,tones,sense
    pai,pai,30,throw
    pai,paai,33,go
    """
)


class TestPolyphones:
    @pytest.fixture
    def poly_g2p(self, data_dir):
        _write(data_dir, "lexicon.csv", POLYPHONE_CSV)
        return ZomiG2P(load_lexicon_from_dir(data_dir))

    def test_sense_selects_entry(self, poly_g2p):
        throw = poly_g2p.convert("pai", sense="throw")
        go = poly_g2p.convert("pai", sense="go")
        assert throw.joined() == "pai˧"
        assert go.joined() == "paai˧ː"

    def test_missing_sense_raises(self, poly_g2p):
        with pytest.raises(AmbiguousWordError) as exc_info:
            poly_g2p.convert("pai")
        err = exc_info.value
        assert err.word == "pai"
        assert set(err.senses) == {"throw", "go"}
        assert err.requested is None

    def test_unknown_sense_raises(self, poly_g2p):
        with pytest.raises(AmbiguousWordError) as exc_info:
            poly_g2p.convert("pai", sense="sing")
        err = exc_info.value
        assert err.word == "pai"
        assert err.requested == "sing"

    def test_sense_on_single_entry_word_mismatch_raises(self, data_dir):
        # Single-entry word with no sense: passing a matching sense is fine.
        # (In this fixture "itna" has sense=None, so any sense raises.)
        g2p = ZomiG2P(load_lexicon_from_dir(data_dir))
        with pytest.raises(AmbiguousWordError) as exc_info:
            g2p.convert("itna", sense="anything")
        assert exc_info.value.requested == "anything"


# ---------------------------------------------------------------------------
# Unknown words
# ---------------------------------------------------------------------------
class TestUnknownWord:
    def test_convert_unknown_raises(self, g2p):
        with pytest.raises(UnknownWordError) as exc_info:
            g2p.convert("zzz")
        assert exc_info.value.word == "zzz"

    def test_convert_text_unknown_raise(self, g2p):
        with pytest.raises(UnknownWordError):
            g2p.convert_text("itna zzz", unknown="raise")

    def test_convert_text_unknown_keep(self, g2p):
        out = g2p.convert_text("itna zzz", unknown="keep")
        assert out == "it˧ na˧ zzz"

    def test_convert_text_unknown_skip(self, g2p):
        out = g2p.convert_text("itna zzz pai", unknown="skip")
        assert out == "it˧ na˧ pai˧"

    def test_convert_text_invalid_policy(self, g2p):
        with pytest.raises(ValueError, match="unknown must be"):
            g2p.convert_text("itna", unknown="bogus")

    def test_convert_text_all_known(self, g2p):
        out = g2p.convert_text("itna pai")
        assert out == "it˧ na˧ pai˧"

    def test_convert_text_ascii(self, g2p):
        out = g2p.convert_text("itna pai", output="ascii")
        assert out == "it3 na3 pai3"


# ---------------------------------------------------------------------------
# Invalid output
# ---------------------------------------------------------------------------
class TestInvalidOutput:
    def test_unknown_output_raises(self, g2p):
        with pytest.raises(InvalidOutputError) as exc_info:
            g2p.convert("itna", output="x-sampa")
        assert exc_info.value.output == "x-sampa"
        assert "ipa" in exc_info.value.valid
        assert "ascii" in exc_info.value.valid


# ---------------------------------------------------------------------------
# Data-layer errors surfaced through conversion
# ---------------------------------------------------------------------------
class TestConversionDataErrors:
    def test_unknown_tone_code_raises_at_load(self, data_dir):
        """A tone code in the CSV that isn't in tones.yaml fails at load."""
        _write(
            data_dir,
            "lexicon.csv",
            "word,syllables,tones\nitna,it-na,99-30\n",
        )
        with pytest.raises(UnknownToneError, match="99"):
            load_lexicon_from_dir(data_dir)

    def test_syllable_tone_mismatch_raises_at_load(self, data_dir):
        _write(
            data_dir,
            "lexicon.csv",
            "word,syllables,tones\nitna,it-na,30\n",
        )
        with pytest.raises(SyllableToneMismatchError):
            load_lexicon_from_dir(data_dir)

    def test_conversion_result_is_frozen(self, g2p):
        result = g2p.convert("itna")
        with pytest.raises(Exception):  # FrozenInstanceError subclasses AttributeError
            result.word = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Pass-through of unknown characters
# ---------------------------------------------------------------------------
class TestPassThrough:
    def test_internal_unknown_char_passes_through(self, data_dir):
        """Characters not in segments.yaml are passed through unchanged.

        _validate() only checks the FIRST character of each syllable, so an
        internal unknown character reaches _convert_segments and is emitted
        as-is. This is the documented pass-through behavior.
        """
        _write(
            data_dir,
            "lexicon.csv",
            "word,syllables,tones\nitna,it!na,30\n",
        )
        g2p = ZomiG2P(load_lexicon_from_dir(data_dir))
        result = g2p.convert("itna", output="ipa")
        assert result.joined() == "it!na˧"


    def test_unknown_char_at_end_of_syllable(self, data_dir):
        """A trailing unknown char in a syllable is also passed through."""
        _write(
            data_dir,
            "lexicon.csv",
            "word,syllables,tones\nitna,it-na!,30-30\n",
        )
        g2p = ZomiG2P(load_lexicon_from_dir(data_dir))
        result = g2p.convert("itna", output="ipa")
        assert result.joined() == "it˧ na!˧"
        
class TestResultHasDefaultLanguageAndOrthography:
    def test_result_has_default_language_and_orthography(self, g2p):
        r = g2p.convert("itna")
        assert r.language == "zol"
        assert r.orthography is None

    def test_result_reflects_constructor_orthography(self, data_dir):
        from zomi_g2p.lexicon import load_lexicon_from_dir
        g2p = ZomiG2P(load_lexicon_from_dir(data_dir),
                    language="ctd", orthography="standard")
        r = g2p.convert("itna")
        assert r.language == "ctd"
        assert r.orthography == "standard"