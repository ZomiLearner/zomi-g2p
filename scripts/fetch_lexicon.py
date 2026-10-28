# scripts/fetch_lexicon.py
"""
Maintainer utility: fetch the Zomi lexicon from the public Google Sheet
and write it to src/zomi_g2p/data/lexicon.csv.

Not used at runtime. Run manually when the lexicon needs updating. Commits the resulting CSV.
The pickle is generated separately by build_pickle.py (or in CI) from
the committed CSV, so it stays in sync with what's in git.
"""

from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass   # .env not installed; rely on shell env

import os
import pandas as pd

from google_data_utils import google_sheet_to_df


SHEET_ID = os.environ["ZOMI_LEXICON_SHEET_ID"]
SHEET_GID = os.environ.get("ZOMI_LEXICON_SHEET_GID", "0")
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"
DATA_DIR = Path("src/zomi_g2p/data")


def main() -> None:
    
    df = google_sheet_to_df(CSV_URL)
    df = df[df['is_zomi'].isna()]
    df = df[['word', 'syllables', 'tones']]
    df = df[~df['word'].isna()]
    # df = df[~df['tones'].isna()]
    
    # Validate expected columns.
    header = df.columns
    required = {"word", "syllables"}
    missing = required - set(header)
    if missing:
        print(f"error: sheet missing columns: {sorted(missing)}", file=sys.stderr)
        return 1
    
    print(df.shape)
    
    output_path = DATA_DIR / "lexicon.csv"
    df.to_csv(DATA_DIR / "lexicon.csv", index=False)

    print(f"wrote {output_path} ({df.shape[0]} entries) ({output_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()