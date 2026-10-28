# zomi-g2p

[![PyPI version](https://img.shields.io/pypi/v/zomi-g2p.svg)](https://pypi.org/project/zomi-g2p/)
[![Python versions](https://img.shields.io/pypi/pyversions/zomi-g2p.svg)](https://pypi.org/project/zomi-g2p/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Grapheme-to-Phoneme (G2P) conversion for the **Zomi language**, with
**IPA** and **ASCII** output and full support for the **six-tone system**.

`zomi-g2p` is a rule-based, data-driven converter. It does **not** infer
tones from spelling. Tones come from a lexicon, which is the authoritative
source. The packaged lexicon is a starter set; you can supply your own
via `load_lexicon_from_dir()`.

---

## Installation

```bash
pip install zomi-g2p
```

Requires Python 3.9+ and `pyyaml`.

---

## Command-line usage

Installing the package also installs the `zomi-g2p` command:

```bash
zomi-g2p convert ankham                          # IPA: an˥ kʰam˥
zomi-g2p convert ankham --output ascii           # ASCII: an5 kham5
zomi-g2p convert ankham --no-tone                # an kʰam
zomi-g2p convert ankham --sep - --json           # JSON, sep ignored in JSON
zomi-g2p text "ankham apkaai" --unknown keep
zomi-g2p batch words.txt --json
zomi-g2p info                                    # lexicon stats
zomi-g2p convert ankham --lexicon /path/to/data  # custom lexicon
```

Run `zomi-g2p --help` or `zomi-g2p <command> --help` for details.

## Quick start

```python
from zomi_g2p import ZomiG2P, load_default_lexicon

g2p = ZomiG2P(load_default_lexicon())

result = g2p.convert("ankham")
print(result.joined())          # IPA output
print(result.joined(sep="-"))   # custom separator
```

`convert()` returns a `ConversionResult` with structured fields:

```python
result = g2p.convert("ankham", output="ipa", with_tone=True)
result.word        # "ankham"
result.syllables   # ("an", "kham")
result.tones       # ("30", "30")
result.phonemes    # ("an˧", "kʰam˧")
result.joined()    # "an˧ kʰam˧"
```

### Output representations

Two representations are supported:

| `output=` | Description | Example |
|---|---|---|
| `"ipa"` | International Phonetic Alphabet with tone letters | `an˧ kʰam˧` |
| `"ascii"` | ASCII-only, TTS-pipeline friendly | `an3 kham3` |

### Tone suppression

```python
g2p.convert("ankham", with_tone=False).joined()
# "an kʰam"  (IPA, no tone letters)
```

---

## The six-tone system

Zomi uses six tones, each with a numeric code and a pitch contour:

| Tone | Code | IPA mark | ASCII mark |
|---|---|---|---|
| mid-short | `30` | `˧` | `3` |
| low-short (glottal) | `10` | `˩ʔ` | `1q` |
| high-short | `50` | `˥` | `5` |
| mid-long | `33` | `˧ː` | `33` |
| rising | `35` | `˧˥` | `35` |
| falling | `31` | `˧˩` | `31` |

Tone marks are appended per syllable. The low-short tone (`10`) includes
a glottal stop (`ʔ` in IPA, `q` in ASCII).

Tone values live in `data/tones.yaml` and are data-driven — you can adjust
the pitch letters without touching the code.

---

## Polyphones (same word, different pronunciations)

Some words have multiple pronunciations distinguished by **sense**. When
a word has more than one entry, pass `sense=` to select the right one:

```python
# Suppose "pai" has senses "throw" and "go":
g2p.convert("pai", sense="throw").joined()   # one pronunciation
g2p.convert("pai", sense="go").joined()      # another

# Without sense=, you get a clear error:
g2p.convert("pai")
# AmbiguousWordError: Word 'pai' is a polyphone with senses: 'throw', 'go'.
# Pass sense= to disambiguate.
```

The exception carries structured attributes:

```python
from zomi_g2p import AmbiguousWordError

try:
    g2p.convert("pai")
except AmbiguousWordError as exc:
    exc.word       # "pai"
    exc.senses     # ("throw", "go")
    exc.requested  # None
```

---

## Text-level conversion

`convert_text()` handles whitespace-separated input with a configurable
policy for out-of-vocabulary words:

```python
g2p.convert_text("ankham apkaai")
# "an˧kʰam˧ ap˧kaːi̯˧"  (IPA)

g2p.convert_text("ankham unknownword apkaai", unknown="keep")
# unknown tokens are preserved as-is

g2p.convert_text("ankham unknownword apkaai", unknown="skip")
# unknown tokens are dropped
```

`unknown="raise"` (the default) raises `UnknownWordError` on the first
OOV token.

---

## Using your own lexicon

The bundled lexicon is a **starter set**. For production use, supply your
own data directory containing three files:

```bash
your_data/
├── lexicon.csv      # word, syllables, tone [, sense]
├── segments.yaml    # grapheme -> IPA / ASCII mappings
└── tones.yaml       # tone code -> IPA / ASCII marks
```

Then:

```python
from zomi_g2p import ZomiG2P
from zomi_g2p.lexicon import load_lexicon_from_dir

lexicon = load_lexicon_from_dir("/path/to/your_data")
g2p = ZomiG2P(lexicon)
```

### `lexicon.csv` format

```csv
word,syllables,tone,sense
itna,it-na,30-30,
pai,pai,30,throw
pai,paai,33,go
```

- **`word`** — the orthographic form, looked up verbatim.
- **`syllables`** — syllables separated by `-`. Each syllable is converted
  by `segments.yaml` using longest-match-first.
- **`tone`** — tone codes separated by `-`, one per syllable. Must be one
  of the six codes above.
- **`sense`** — optional. Only needed for polyphones; leave empty otherwise.

The number of syllables must equal the number of tones. The loader
validates this at load time and raises `SyllableToneMismatchError` if
a row is inconsistent.

### `segments.yaml` format

```yaml
segments:
  - grapheme: "ng"
    ipa: "ŋ"
    ascii: "ng"
  - grapheme: "aw"
    ipa: "ɔ"
    ascii: "o"
  - grapheme: "a"
    ipa: "a"
    ascii: "a"
```

Order does not matter — the loader sorts by grapheme length descending
so longest-match wins. Every character that can start a syllable must be
covered by at least one segment; the validator rejects data that violates
this.

### `tones.yaml` format

```yaml
tones:
  - name: mid-short
    code: "30"
    ipa_mark: "˧"
    ascii_mark: "3"
  # ... the other five
```

All six codes must be present. Every tone code used in `lexicon.csv` must
exist in `tones.yaml`.

---

## Error handling

All errors inherit from `ZomiG2PError`:

```python
from zomi_g2p import ZomiG2PError

try:
    g2p.convert("unknown")
except ZomiG2PError:
    ...
```

The hierarchy:

```bash
ZomiG2PError
├── LexiconError
│   ├── UnknownWordError
│   ├── AmbiguousWordError
│   ├── SyllableToneMismatchError
│   └── DataValidationError
├── UnknownToneError
└── ConversionError
    └── InvalidOutputError
```

Catch `ZomiG2PError` for "any zomi-g2p problem", or a specific subclass
for fine-grained handling (e.g., fall back to character input on
`UnknownWordError`).

---

## Data validation

When a lexicon directory is loaded, `zomi-g2p` validates:

- Every `lexicon.csv` row has equal syllable and tone counts.
- Every tone code in the CSV exists in `tones.yaml`.
- No duplicate `(word, sense)` pairs.
- Every syllable's first character is covered by `segments.yaml`.
- No duplicate graphemes or tone codes.

Violations raise `DataValidationError`, `UnknownToneError`, or
`SyllableToneMismatchError` with a message naming the offending row or
file. This catches most data-entry mistakes before conversion begins.

---

## Development

```bash
git clone https://github.com/<you>/zomi-g2p.git
cd zomi-g2p
pip install -e ".[dev]"
pytest
```

The test suite covers the lexicon loader, the converter, and the packaged
data files. See `tests/` for details.

### Configuration

Maintainer scripts read configuration from environment variables. Copy
the template and fill in the values:

```bash
cp .env.template .env
# edit .env — set ZOMI_LEXICON_SHEET_ID, etc.
```

`.env` is gitignored. Only `.env.template` is committed.

### Refreshing the packaged lexicon

The lexicon is maintained in a Google Sheet and snapshotted to
src/zomi_g2p/data/lexicon.csv. To refresh it, run
make fetch-lexicon (requires network access), review the CSV diff,
and commit the result. The lexicon.pkl is a build artifact and is
not committed — CI regenerates it from the CSV before building
the wheel. This script is **not** installed with the package
and is only used when updating the bundled data:

```bash
make fetch-lexicon
# then to build pickle locally 
# build_pickle.py converts (CSV → PKL)
make build-pickle
```

---

## License

MIT. See [LICENSE](LICENSE).

---

## Acknowledgements

Built for the Zomi language community. Tone values and phoneme mappings
follow published Tedim (Zomi) phonological descriptions; corrections and
contributions are welcome via issues and pull requests.

### Notes on this README

**1. The data-format sections are the most important part**

Since the bundled lexicon is a starter set, most real users will bring their own `lexicon.csv`. The README documents all three file formats with concrete examples, and explains the validation rules the loader enforces. Without this, users will hit `DataValidationError` and not know why.

**2. Polyphones get their own section**

The `sense=` parameter is the least obvious part of the API. The example shows both the success path and the `AmbiguousWordError` with its structured attributes, so users can write `except AmbiguousWordError as exc: retry with exc.senses[0]` if they want a fallback.

**3. The six-tone table is repeated from `tones.yaml`**

Having it in the README means users can eyeball a lexicon row and know what `30-30` means without opening a YAML file. If you change tone letters in `tones.yaml`, update the table too — or better, note in the README that `tones.yaml` is the source of truth.

**4. "Using your own lexicon" is prominent**

It comes before error handling and development, because for a real TTS pipeline, supplying your own data is the primary workflow. The bundled lexicon is explicitly described as a starter set — no surprises about its size.

**5. Error hierarchy is shown as a tree**

Users can scan it and immediately see what to catch. `ZomiG2PError` for coarse handling, subclasses for fine.

**6. Development section documents `scripts/fetch_lexicon.py`**

Since you decided to commit the script, the README says what it does, that it's maintainer-only, and how to invoke it via `make fetch-lexicon`. This matches the `Makefile` target.

**7. No false claims about dialect coverage**

The README says "Zomi language" and "Tedim (Zomi) phonological descriptions" in acknowledgements. If your lexicon is specifically Tedim, consider changing "Zomi language" to "Tedim (a Zomi variety)" in the header and description — precision here avoids users of other Zomi varieties expecting their orthography to work. If the lexicon covers multiple varieties, say so explicitly and note how they're distinguished (e.g., separate `sense` values or separate data files).

**8. One thing to fix before publishing**

Replace `<you>` in the clone URL and `<your name>` in `LICENSE` with actual values. Both are placeholders that shouldn't ship.

## Project Structure

```bash
zomi-g2p/
├── src/
│   └── zomi_g2p/
│       ├── __init__.py          # Exports ZomiG2P
│       ├── converter.py         # Core conversion logic (CSV lookup, syllable segmentation, phoneme mapping, tone tagging)
│       ├── lexicon.py           # CSV loading, parsing, index building
│       ├── exceptions.py        # UnknownWordError, UnknownToneError, SyllableToneMismatchError
│       └── data/
│           ├── segments.yaml    # Grapheme → IPA/ASCII mapping (distinguishes vowel length)
│           ├── tones.yaml       # 6-tone system: code → IPA tone letter / ASCII marker
│           └── lexicon.csv      # Your CSV: word, syllables, tone
├── tests/
│   ├── test_lexicon.py          # CSV parsing, syllable-tone count consistency
│   ├── test_converter.py        # End-to-end conversion (e.g., itna → it˧ na˧ / it3 na3)
│   └── test_data.py             # Mapping table integrity, tone code coverage
├── pyproject.toml               # package-data includes data/*.yaml and data/*.csv
├── README.md
└── LICENSE
```
