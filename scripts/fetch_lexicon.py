from google_data_utils import *
import pandas as pd
# import pickle

# df = google_sheet_to_df("https://docs.google.com/spreadsheets/d/1xDGQTL8QXFKK2t_FFZhswfuZc_BwznsWKHeOkFRRXYY/edit?gid=1888352546#gid=1888352546")
# df = df[df['is_zomi'].isna()]
# df = df[['word', 'syllables', 'tones']]
# df = df[~df['word'].isna()]
# # df = df[~df['tones'].isna()]
# print(df.shape)
# data_path = "src/zomi_g2p/data"
# df.to_csv(f"{data_path}/lexicon.csv", index=False)

# def build_pickle(lexicon: Lexicon, output: Path) -> None:
#     with output.open("wb") as f:
#         pickle.dump(lexicon, f, protocol=pickle.HIGHEST_PROTOCOL)
        

# build_pickle(Lexicon(df), Path(f"{data_path}/lexicon.pkl"))

"""
Maintainer utility: fetch/refresh src/zomi_g2p/data/lexicon.csv
and rebuild the runtime pickle.

Not used at runtime. Run manually when the lexicon needs updating.
"""

import pickle
from pathlib import Path

# from zomi_g2p.lexicon import Lexicon, load_lexicon_from_dir
from zomi_g2p.lexicon import load_lexicon_from_dir, _save_pickle

DATA_DIR = Path("src/zomi_g2p/data")


def main() -> None:
    # 1. If fetching from an external source, do it here and write
    #    DATA_DIR / "lexicon.csv" via csv.writer or pandas.
    #    (This step is already done by whatever code produced the CSV.)
    df = google_sheet_to_df("https://docs.google.com/spreadsheets/d/1xDGQTL8QXFKK2t_FFZhswfuZc_BwznsWKHeOkFRRXYY/edit?gid=1888352546#gid=1888352546")
    df = df[df['is_zomi'].isna()]
    df = df[['word', 'syllables', 'tones']]
    df = df[~df['word'].isna()]
    # df = df[~df['tones'].isna()]
    print(df.shape)
    df.to_csv(DATA_DIR / "lexicon.csv", index=False)

    # 2. Load the CSV + YAML via the SAME loader the runtime uses.
    lexicon = load_lexicon_from_dir(DATA_DIR)
    print(f"loaded {len(lexicon)} entries")

    # 3. Build the pickle from that Lexicon object.
    output_path = DATA_DIR / "lexicon.pkl"
    _save_pickle(lexicon, output_path)
    # with output.open("wb") as f:
    #     pickle.dump(lexicon, f, protocol=pickle.HIGHEST_PROTOCOL)
    # print(f"wrote lexicon.pkl ({len(lexicon)} entries)")
    print(f"wrote {output_path} ({len(lexicon)} entries) ({output_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()