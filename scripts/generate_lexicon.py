"""
Generate lexicon entries from a raw word list using the rule engine.

Usage:
    python scripts/generate_lexicon.py words.txt > generated.csv

The output CSV has columns: word,syllables,tone,tone_sources
Every entry's tones are rule-sourced (marked as "rule").
A human linguist should review and correct the output before using
it as training data or shipping it in the lexicon.
"""

import argparse
import csv
import sys
from pathlib import Path

from zomi_g2p.lexicon import load_default_lexicon
from zomi_g2p.rules import RuleEngine


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("words", help="input file, one word per line")
    parser.add_argument("--output", "-o", default="-",
                        help="output CSV path (default: stdout)")
    args = parser.parse_args()

    lexicon = load_default_lexicon()
    engine = RuleEngine(lexicon.segments)

    source = Path(args.words)
    if not source.is_file():
        print(f"error: file not found: {source}", file=sys.stderr)
        return 2

    out = sys.stdout if args.output == "-" else open(args.output, "w", newline="")
    try:
        writer = csv.writer(out)
        writer.writerow(["word", "syllables", "tone", "tone_sources"])
        with source.open("r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if not word or word.startswith("#"):
                    continue
                result = engine.analyze(word)
                writer.writerow([
                    result.word,
                    "-".join(result.syllables),
                    "-".join(result.tones),
                    "-".join(result.tone_sources),
                ])
    finally:
        if out is not sys.stdout:
            out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())