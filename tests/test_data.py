"""
Tests for packaged data integrity
=================================

These tests validate the REAL data files shipped in
``src/zomi_g2p/data/`` (segments.yaml, tones.yaml, lexicon.csv).

They are intentionally separate from test_lexicon.py:
- test_lexicon.py uses synthetic fixtures to test parser/index logic.
- test_data.py checks that the data itself is well-formed and consistent
  with the contracts the converter relies on.

If these tests fail, the package is broken for every user — do not
publish to PyPI until they pass.
"""

from __future__ import annotations

import pytest

from zomi_g2p.lexicon import load_default_lexicon

# The six-tone system agreed on for Zomi.
EXPECTED_TONE_CODES = {"30", "10", "50", "33", "35", "31"}

# Output modes the converter supports.
EXPECTED_OUTPUT_KEYS = {"ipa", "ascii"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def lexicon():
    """Load the packaged lexicon once for all tests in this module."""
    return load_default_lexicon()


# ---------------------------------------------------------------------------
# segments.yaml
# ---------------------------------------------------------------------------
class TestSegmentsData:
    def test_segments_not_empty(self, lexicon):
        assert len(lexicon.segments) > 0

    def test_every_segment_has_nonempty_fields(self, lexicon):
        for seg in lexicon.segments:
            assert seg.grapheme, f"empty grapheme in segments: {seg!r}"
            assert seg.ipa, f"empty ipa for grapheme {seg.grapheme!r}"
            assert seg.ascii, f"empty ascii for grapheme {seg.grapheme!r}"

    def test_no_duplicate_graphemes(self, lexicon):
        graphemes = [s.grapheme for s in lexicon.segments]
        assert len(graphemes) == len(set(graphemes)), (
            f"duplicate graphemes: "
            f"{sorted(g for g in set(graphemes) if graphemes.count(g) > 1)}"
        )

    def test_segments_sorted_longest_first(self, lexicon):
        """converter._convert_segments relies on longest-match-first order."""
        lengths = [len(s.grapheme) for s in lexicon.segments]
        assert lengths == sorted(lengths, reverse=True), (
            "segments are not sorted by grapheme length descending; "
            "longest-match conversion will be wrong"
        )

    def test_single_char_segments_exist(self, lexicon):
        """Every multi-char grapheme should have its first char covered,
        so a partial match is still possible if the digraph is absent."""
        single = {s.grapheme for s in lexicon.segments if len(s.grapheme) == 1}
        for seg in lexicon.segments:
            if len(seg.grapheme) > 1:
                assert seg.grapheme[0] in single, (
                    f"digraph {seg.grapheme!r} has no single-char entry "
                    f"for its first character {seg.grapheme[0]!r}"
                )

    def test_no_empty_ipa_marks(self, lexicon):
        for seg in lexicon.segments:
            assert seg.ipa.strip(), f"blank ipa for {seg.grapheme!r}"
            assert seg.ascii.strip(), f"blank ascii for {seg.grapheme!r}"


# ---------------------------------------------------------------------------
# tones.yaml
# ---------------------------------------------------------------------------
class TestTonesData:
    def test_all_six_tones_present(self, lexicon):
        assert EXPECTED_TONE_CODES <= set(lexicon.tones), (
            f"missing tone codes: "
            f"{sorted(EXPECTED_TONE_CODES - set(lexicon.tones))}"
        )

    def test_no_unexpected_tone_codes(self, lexicon):
        extra = set(lexicon.tones) - EXPECTED_TONE_CODES
        assert not extra, f"unexpected tone codes in tones.yaml: {sorted(extra)}"

    def test_every_tone_has_both_outputs(self, lexicon):
        for code, marks in lexicon.tones.items():
            assert set(marks) == EXPECTED_OUTPUT_KEYS, (
                f"tone {code!r} has keys {sorted(marks)}, "
                f"expected {sorted(EXPECTED_OUTPUT_KEYS)}"
            )

    def test_tone_marks_nonempty(self, lexicon):
        for code, marks in lexicon.tones.items():
            assert marks["ipa"].strip(), f"empty ipa mark for tone {code!r}"
            assert marks["ascii"].strip(), f"empty ascii mark for tone {code!r}"

    def test_low_short_tone_has_glottal_stop(self, lexicon):
        """Tone 10 (low-short) carries a glottal stop in IPA output."""
        ipa_mark = lexicon.tones["10"]["ipa"]
        assert "ʔ" in ipa_mark, (
            f"tone 10 IPA mark {ipa_mark!r} should contain glottal stop ʔ"
        )


# ---------------------------------------------------------------------------
# lexicon.csv
# ---------------------------------------------------------------------------
class TestLexiconData:
    def test_lexicon_not_empty(self, lexicon):
        assert len(lexicon) > 0

    def test_every_word_has_at_least_one_entry(self, lexicon):
        for word in lexicon.words():
            assert lexicon.entries_for(word), f"word {word!r} has no entries"

    def test_syllable_tone_count_matches(self, lexicon):
        for word in lexicon.words():
            for entry in lexicon.entries_for(word):
                assert len(entry.syllables) == len(entry.tones), (
                    f"word {word!r} (sense={entry.sense!r}): "
                    f"{len(entry.syllables)} syllables, "
                    f"{len(entry.tones)} tones"
                )

    def test_all_tone_codes_resolve(self, lexicon):
        """Every tone code used in the lexicon must exist in tones.yaml."""
        missing: set[str] = set()
        for word in lexicon.words():
            for entry in lexicon.entries_for(word):
                for tone in entry.tones:
                    if tone not in lexicon.tones:
                        missing.add(tone)
        assert not missing, (
            f"tone codes used in lexicon.csv but missing from tones.yaml: "
            f"{sorted(missing)}"
        )

    def test_no_empty_syllables(self, lexicon):
        for word in lexicon.words():
            for entry in lexicon.entries_for(word):
                for syl in entry.syllables:
                    assert syl, f"word {word!r} has an empty syllable"

    def test_syllables_only_contain_known_first_chars(self, lexicon):
        """Every syllable's first character must be coverable by segments."""
        first_chars = {s.grapheme[0] for s in lexicon.segments if s.grapheme}
        bad: set[str] = set()
        for word in lexicon.words():
            for entry in lexicon.entries_for(word):
                for syl in entry.syllables:
                    if syl and syl[0] not in first_chars:
                        bad.add(syl[0])
        assert not bad, (
            f"characters in syllables with no matching segment: {sorted(bad)}"
        )

    def test_no_whitespace_in_words_or_syllables(self, lexicon):
        for word in lexicon.words():
            assert word == word.strip(), f"word {word!r} has leading/trailing space"
            for entry in lexicon.entries_for(word):
                for syl in entry.syllables:
                    assert syl == syl.strip(), (
                        f"word {word!r}: syllable {syl!r} has whitespace"
                    )

    def test_polyphones_have_distinct_senses(self, lexicon):
        """If a word has multiple entries, each must have a unique sense."""
        for word in lexicon.words():
            entries = lexicon.entries_for(word)
            if len(entries) > 1:
                senses = [e.sense for e in entries]
                assert all(s is not None for s in senses), (
                    f"polyphone {word!r} has entries without sense tags"
                )
                assert len(senses) == len(set(senses)), (
                    f"polyphone {word!r} has duplicate senses: {senses}"
                )


# ---------------------------------------------------------------------------
# Cross-file consistency
# ---------------------------------------------------------------------------
class TestCrossFileConsistency:
    def test_every_syllable_tone_is_known(self, lexicon):
        """Index-level check: every (syllable, tone) pair is resolvable."""
        for word in lexicon.words():
            for entry in lexicon.entries_for(word):
                for syl, tone in zip(entry.syllables, entry.tones):
                    assert tone in lexicon.tones, (
                        f"word {word!r}: syllable {syl!r} uses unknown "
                        f"tone {tone!r}"
                    )

    def test_tone_candidates_consistent_with_lexicon(self, lexicon):
        """tone_candidates(syl) must contain every tone observed for syl."""
        for word in lexicon.words():
            for entry in lexicon.entries_for(word):
                for syl, tone in zip(entry.syllables, entry.tones):
                    assert tone in lexicon.tone_candidates(syl), (
                        f"tone {tone!r} for syllable {syl!r} not in "
                        f"tone_candidates: {lexicon.tone_candidates(syl)}"
                    )