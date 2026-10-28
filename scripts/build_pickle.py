"""
Build src/zomi_g2p/data/lexicon.pkl from the committed src/zomi_g2p/data/lexicon.csv.
Safe to run in CI and locally; does not touch the network.
"""
import sys
from pathlib import Path

from zomi_g2p.lexicon import _save_pickle, load_lexicon_from_dir

DATA_DIR = Path("src/zomi_g2p/data")


def main() -> int:
    lex = load_lexicon_from_dir(DATA_DIR)
    _save_pickle(lex, DATA_DIR / "lexicon.pkl")
    print(f"wrote {DATA_DIR / 'lexicon.pkl'} ({len(lex)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())