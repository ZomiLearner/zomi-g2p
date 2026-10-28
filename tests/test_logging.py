from __future__ import annotations

import logging
import textwrap

import pytest

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


def test_null_handler_attached():
    from zomi_g2p import ZomiG2P  # noqa: F401
    handlers = logging.getLogger("zomi_g2p").handlers
    assert any(isinstance(h, logging.NullHandler) for h in handlers)


def test_default_tones_logged(data_dir, caplog):
    caplog.set_level(logging.INFO, logger="zomi_g2p.lexicon")
    from zomi_g2p.lexicon import load_lexicon_from_dir
    load_lexicon_from_dir(data_dir)
    assert any("default tones" in rec.message for rec in caplog.records)