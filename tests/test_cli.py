"""Tests for the zomi-g2p CLI."""

from __future__ import annotations

import json
import logging
import textwrap

import pytest

from zomi_g2p.cli import main


SEGMENTS_YAML = textwrap.dedent("""\
segments:
  - {grapheme: "a", ipa: "a", ascii: "a"}
  - {grapheme: "i", ipa: "i", ascii: "i"}
  - {grapheme: "t", ipa: "t", ascii: "t"}
  - {grapheme: "n", ipa: "n", ascii: "n"}
  - {grapheme: "k", ipa: "k", ascii: "k"}
  - {grapheme: "h", ipa: "h", ascii: "h"}
  - {grapheme: "m", ipa: "m", ascii: "m"}
  - {grapheme: "kh", ipa: "kʰ", ascii: "kh"}
""")

TONES_YAML = textwrap.dedent("""\
tones:
  - {code: "30", ipa_mark: "˧", ascii_mark: "3"}
  - {code: "50", ipa_mark: "˥", ascii_mark: "5"}
  - {code: "10", ipa_mark: "˩ʔ", ascii_mark: "1q"}
  - {code: "33", ipa_mark: "˧ː", ascii_mark: "33"}
  - {code: "35", ipa_mark: "˧˥", ascii_mark: "35"}
  - {code: "31", ipa_mark: "˧˩", ascii_mark: "31"}
""")

LEXICON_CSV = textwrap.dedent("""\
word,syllables,tones
itna,it-na,30-30
ankham,an-kham,50-50
""")


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "segments.yaml").write_text(SEGMENTS_YAML, encoding="utf-8")
    (tmp_path / "tones.yaml").write_text(TONES_YAML, encoding="utf-8")
    (tmp_path / "lexicon.csv").write_text(LEXICON_CSV, encoding="utf-8")
    return tmp_path


def test_convert_ipa(data_dir, capsys):
    rc = main(["convert", "ankham", "--lexicon", str(data_dir)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "an˥ kʰam˥"


def test_convert_ascii(data_dir, capsys):
    rc = main(["convert", "ankham", "--output", "ascii", "--lexicon", str(data_dir)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "an5 kham5"


def test_convert_custom_sep(data_dir, capsys):
    rc = main(["convert", "ankham", "--sep", "-", "--lexicon", str(data_dir)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "an˥-kʰam˥"


def test_convert_no_tone(data_dir, capsys):
    rc = main(["convert", "ankham", "--no-tone", "--lexicon", str(data_dir)])
    assert rc == 0
    assert "˥" not in capsys.readouterr().out


def test_convert_unknown_word(data_dir, capsys, caplog):
    caplog.set_level(logging.ERROR, logger="zomi_g2p.cli")
    rc = main(["convert", "zzz", "--lexicon", str(data_dir)])
    assert rc == 1
    assert any("zzz" in rec.message for rec in caplog.records) # correspond to logging
    # correspond to print to stderr
    # this can be deleted with the corresponding print statment in cli.py
    assert "zzz" in capsys.readouterr().err 


def test_convert_json(data_dir, capsys):
    rc = main(["convert", "itna", "--json", "--lexicon", str(data_dir)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["word"] == "itna"
    assert payload["phonemes"] == ["it˧", "na˧"]


def test_text_unknown_keep(data_dir, capsys):
    rc = main(["text", "itna zzz", "--unknown", "keep", "--lexicon", str(data_dir)])
    assert rc == 0
    assert "zzz" in capsys.readouterr().out


def test_batch(data_dir, tmp_path, capsys):
    words = tmp_path / "words.txt"
    words.write_text("itna\nankham\n# comment\n", encoding="utf-8")
    rc = main(["batch", str(words), "--lexicon", str(data_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "itna\tit˧ na˧" in out
    assert "ankham\tan˥ kʰam˥" in out


def test_batch_stop_on_error(data_dir, tmp_path, capsys):
    words = tmp_path / "words.txt"
    words.write_text("itna\nzzz\nankham\n", encoding="utf-8")
    rc = main(["batch", str(words), "--lexicon", str(data_dir), "--stop-on-error"])
    assert rc == 1


def test_info(data_dir, capsys):
    rc = main(["info", "--lexicon", str(data_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "entries   : 2" in out
    assert "tones     : 10, 30, 31, 33, 35, 50" in out


def test_info_json(data_dir, capsys):
    rc = main(["info", "--json", "--lexicon", str(data_dir)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["entries"] == 2
    assert payload["tones"] == ["10", "30", "31", "33", "35", "50"]


def test_missing_lexicon_dir(capsys, caplog):
    caplog.set_level(logging.ERROR, logger="zomi_g2p.cli")
    rc = main(["convert", "itna", "--lexicon", "/nonexistent/path"])
    assert rc != 0
    assert rc == 2
    assert "not found" in capsys.readouterr().err # correspond to logging
    # correspond to print to stderr
    # this can be deleted with the corresponding print statment in cli.py
    assert any("not found" in rec.message for rec in caplog.records)

def test_json_includes_language_and_orthography(data_dir, capsys):
    rc = main(["convert", "itna", "--json",
               "--language", "ctd", "--orthography", "standard",
               "--lexicon", str(data_dir)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["language"] == "ctd"
    assert payload["orthography"] == "standard"