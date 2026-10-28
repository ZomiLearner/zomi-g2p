

# from __future__ import annotations

# from zomi_g2p.rules import RuleEngine

# import logging
# import pytest
# import textwrap


# # ---------------------------------------------------------------------------
# # Fixtures
# # ---------------------------------------------------------------------------
# SEGMENTS_YAML = textwrap.dedent(
#     """\
#     segments:
#       - grapheme: "a"
#         ipa: "a"
#         ascii: "a"
#       - grapheme: "i"
#         ipa: "i"
#         ascii: "i"
#       - grapheme: "p"
#         ipa: "p"
#         ascii: "p"
#       - grapheme: "t"
#         ipa: "t"
#         ascii: "t"
#       - grapheme: "n"
#         ipa: "n"
#         ascii: "n"
#       - grapheme: "ng"
#         ipa: "ŋ"
#         ascii: "ng"
#     """
# )

# TONES_YAML = textwrap.dedent(
#     """\
#     tones:
#       - name: mid-short
#         code: "30"
#         ipa_mark: "˧"
#         ascii_mark: "3"
#       - name: low-short
#         code: "10"
#         ipa_mark: "˩ʔ"
#         ascii_mark: "1q"
#       - name: rising
#         code: "35"
#         ipa_mark: "˧˥"
#         ascii_mark: "35"
#       - name: falling
#         code: "31"
#         ipa_mark: "˧˩"
#         ascii_mark: "31"
#     """
# )

# LEXICON_CSV = textwrap.dedent(
#     """\
#     word,syllables,tones
#     itna,it-na,30-30
#     pai,pai,30
#     """
# )


# @pytest.fixture
# def data_dir(tmp_path):
#     """Write a minimal valid data directory and return its path."""
#     (tmp_path / "segments.yaml").write_text(SEGMENTS_YAML, encoding="utf-8")
#     (tmp_path / "tones.yaml").write_text(TONES_YAML, encoding="utf-8")
#     (tmp_path / "lexicon.csv").write_text(LEXICON_CSV, encoding="utf-8")
#     return tmp_path
# #

# def _write(data_dir, name: str, content: str) -> None:
    
#     (data_dir / name).write_text(content, encoding="utf-8")


# def test_syllabify_simple_cv():
#     engine = RuleEngine([...segments...])
#     assert engine.syllabify("itna") == ["it", "na"]

# def test_syllabify_cvc():
#     engine = RuleEngine([...segments...])
#     assert engine.syllabify("kham") == ["kham"]

# def test_syllabify_diphthong():
#     engine = RuleEngine([...segments...])
#     assert engine.syllabify("pai") == ["pai"]

# def test_default_tone_short():
#     engine = RuleEngine([...segments...])
#     tones, sources = engine.predict_tones(["an"])
#     assert tones == ["30"]
#     assert sources == ["rule"]

# def test_default_tone_long():
#     engine = RuleEngine([...segments...])
#     tones, _ = engine.predict_tones(["paai"])
#     assert tones == ["33"]

# def test_analyze_returns_entry():
#     engine = RuleEngine([...segments...])
#     result = engine.analyze("itna")
#     entry = result.to_entry()
#     assert entry.word == "itna"
#     assert entry.tone_sources == ("rule", "rule")