# Contributing to zomi-g2p

Thank you for your interest in improving `zomi-g2p`! This document covers
how to set up a development environment, run the tests, work with the
lexicon data, and submit changes.

---

## Table of contents

- [Code of conduct](#code-of-conduct)
- [Ways to contribute](#ways-to-contribute)
- [Development setup](#development-setup)
- [Project layout](#project-layout)
- [Running the tests](#running-the-tests)
- [Working with the lexicon](#working-with-the-lexicon)
- [Adding or changing segments/tones](#adding-or-changing-segmentstones)
- [Code style](#code-style)
- [Submitting a pull request](#submitting-a-pull-request)
- [Release process](#release-process)

---

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). By
participating, you agree to abide by its terms.

---

## Ways to contribute

You don't need to write code to help:

- **Report data errors.** If a word converts incorrectly, open an issue
  with the word, its expected IPA, and its expected tones. Data fixes are
  as valuable as code fixes.
- **Improve `segments.yaml`.** If a grapheme is missing or maps to the
  wrong IPA, that's a one-line fix that benefits every user.
- **Add tones.** The lexicon's `tone` column is partially filled. Adding
  validated tones for a batch of words is a high-impact contribution.
- **Document dialect variation.** If your dialect differs from the
  standard used in the bundled lexicon, document the differences in an
  issue — that's the first step toward multi-dialect support.
- **Write tests.** Coverage of the rule engine and CLI is always
  welcome.

---

## Development setup

### Requirements

- Python 3.9 or newer
- Git
- (Optional) `make` for the convenience targets

### Clone and install

```bash
git clone https://github.com/<org>/zomi-g2p.git
cd zomi-g2p

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"
```

The `dev` extra installs `pytest`, `pytest-cov`, `python-dotenv`, `build`, `google-data-utils`, and `twine`.

### Verify the setup

```bash
pytest -q
```

All tests should pass. If any fail on a fresh clone, please open an issue —
that's a bug in the setup, not in your environment.

---

## Project layout

```
zomi-g2p/
├── src/zomi_g2p/
│   ├── __init__.py          # Public API, __version__
│   ├── __main__.py          # `python -m zomi_g2p`
│   ├── cli.py               # argparse-based CLI
│   ├── converter.py         # ZomiG2P, ConversionResult
│   ├── lexicon.py           # Lexicon, LexiconEntry, Segment, loaders
│   ├── rules.py             # RuleEngine (syllabification + tone defaults)
│   ├── provenance.py        # TONES_SOURCE_* constants
│   ├── exceptions.py        # ZomiG2PError hierarchy
│   └── data/
│       ├── lexicon.csv      # Source of truth (committed)
│       ├── segments.yaml    # grapheme → IPA / ASCII
│       ├── tones.yaml       # six-tone system
│       └── lexicon.pkl      # Derived artifact (gitignored, built in CI)
├── scripts/                 # Maintainer utilities (not installed)
├── tests/                   # pytest suite
└── workspace/               # Scratch files (mostly gitignored)
```

### Rules of thumb

- **Don't edit `lexicon.pkl`.** It's generated. Edit `lexicon.csv` and
  rebuild the pickle (see below).
- **Don't add code to `scripts/`** that the package needs at runtime.
  Scripts are maintainer tools; runtime code lives in `src/zomi_g2p/`.
- **Don't import `yaml` at module level** in `src/`. It's lazy-imported
  inside the loaders to keep CLI startup fast.

---

## Running the tests

```bash
# All tests
pytest -q

# One file
pytest tests/test_converter.py -q

# One test
pytest tests/test_converter.py::TestConvertBasic::test_itna_ipa -v

# With coverage
pytest --cov=zomi_g2p --cov-report=term-missing
```

The suite has three layers:

| File | What it tests |
|---|---|
| `test_data.py` | Integrity of the **packaged** data files |
| `test_lexicon.py` | CSV/YAML parsing, indexing, validation |
| `test_converter.py` | End-to-end conversion (IPA, ASCII, tones, polyphones) |
| `test_rules.py` | Rule engine (syllabification, tone defaults) |
| `test_cli.py` | CLI commands, exit codes, JSON output |
| `test_logging.py` | Logger setup, `NullHandler` |

If you change `segments.yaml` or `tones.yaml`, `test_data.py` will tell
you what broke. Read its assertions before "fixing" the test — they
usually encode a real invariant.

---

## Working with the lexicon

The lexicon lives in a Google Sheet maintained by the project. The CSV in
`src/zomi_g2p/data/lexicon.csv` is a **snapshot** of that sheet, committed
to git so releases are reproducible.

### Refreshing the lexicon (maintainers)

```bash
# 1. Copy the env template and fill in the sheet ID
cp .env.template .env
# edit .env — set ZOMI_LEXICON_SHEET_ID

# 2. Download the sheet and rebuild the pickle
make fetch-lexicon

# 3. Review the diff before committing
git diff src/zomi_g2p/data/lexicon.csv

# 4. Commit the CSV (never the pickle)
git add src/zomi_g2p/data/lexicon.csv
git commit -m "data: refresh lexicon from sheet"
```

### Rebuilding the pickle (everyone)

If you've edited `lexicon.csv` locally and want the CLI to use the fast
path:

```bash
python scripts/build_pickle.py
```

Or just delete `lexicon.pkl` — `load_default_lexicon()` will fall back to
parsing the CSV, which is slower but correct. `make test` doesn't require
the pickle.

### Adding a word manually

For a single-word fix, editing the CSV directly is fine:

```csv
word,syllables,tone,sense
itna,it-na,30-30,
```

Then rebuild the pickle and run `pytest`. `test_data.py` will catch
malformed rows (mismatched syllable/tone counts, unknown tone codes,
uncovered characters).

---

## Adding or changing segments/tones

`segments.yaml` and `tones.yaml` are the phonological core of the package.
Changes here affect every conversion, so they need care.

### `segments.yaml`

```yaml
segments:
  - grapheme: "kh"
    ipa: "kʰ"
    ascii: "kh"
```

Checklist before adding a segment:

- [ ] The grapheme appears in `lexicon.csv`'s `syllables` column (or in a
      word you're about to add).
- [ ] The IPA is phonemic, not phonetic — use `kʰ`, not `kʰʲ` unless the
      palatalization is contrastive.
- [ ] If the grapheme is a digraph, every character it starts with has a
      single-character entry. (`ng` requires `n`; `kh` requires `k`.)
- [ ] `test_data.py::test_no_duplicate_graphemes` still passes.

### `tones.yaml`

The six-tone system is fixed. Don't add or remove tone codes without
discussing it in an issue first — the lexicon's `tone` column and
`provenance.py` both depend on the set `{30, 10, 50, 33, 35, 31}`.

Changing a **tone mark** (e.g., `˧` → `˧˩`) is fine if the IPA letter is
wrong. Changing a **tone code** breaks the lexicon.

### After any change

```bash
python scripts/build_pickle.py
pytest -q
zomi-g2p -vv convert itna      # spot-check a known word
```

---

## Code style

- **Formatting**: 88-column lines, 4-space indent. `ruff format` or
  `black` are both acceptable; there's no enforced formatter in CI yet.
- **Imports**: `from __future__ import annotations` at the top of every
  module. Standard library, then third-party, then local — alphabetized
  within each group.
- **Type hints**: public functions and methods should have them. Internal
  helpers can omit them if obvious.
- **Docstrings**: Google style for public APIs. One-line summary, then
  `Parameters`/`Returns`/`Raises` as needed.
- **Logging**: use `logging.getLogger("zomi_g2p.<module>")`. Never call
  `logging.basicConfig()` outside `cli.main()`. Never `print()` from
  library code.
- **Exceptions**: raise from the `ZomiG2PError` hierarchy. Don't raise
  bare `Exception` or `ValueError` for data problems — add a subclass.
- **No new runtime dependencies** without discussion. The package
  currently depends only on `pyyaml`.

### Running linters locally

```bash
pip install ruff
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
```

---

## Submitting a pull request

1. **Open an issue first** for anything larger than a typo or a one-line
   data fix. That avoids wasted work if the change isn't a good fit.
2. **Fork and branch**:
```bash
git checkout -b fix/kh-mapping
```
3. **Keep commits focused.** A data fix and a code refactor should be
   separate commits (ideally separate PRs).
4. **Write tests** for code changes. For data changes, make sure
   `test_data.py` passes and consider adding a fixture word that
   exercises the fix.
5. **Update `CHANGELOG.md`** if the change is user-visible. Run
   `python scripts/generate_changelog.py` or add an entry by hand.
6. **Push and open the PR** against `main`.
7. **CI must pass.** The workflow runs `pytest` and builds the wheel. If
   CI fails on a data test, read the assertion — it usually tells you
   exactly which row or grapheme is wrong.

### Commit message convention

Roughly Conventional Commits:

```text
feat: add rule engine for OOV fallback
fix: kh maps to kʰ not x
data: add 120 words from the 2026-10 sheet snapshot
docs: clarify tone_sources in README
test: cover polyphone sense selection
chore: bump pyyaml to 6.0.1
```

The changelog generator categorizes by these prefixes, so following the
convention keeps `CHANGELOG.md` tidy.

---

## Release process

Releases are cut by maintainers. The short version:

```bash
# 1. Bump version in pyproject.toml (the ONLY place it's defined)
# 2. Regenerate the changelog
python scripts/generate_changelog.py --repo-url https://github.com/<org>/zomi-g2p

# 3. Commit and push
git add pyproject.toml CHANGELOG.md
git commit -m "chore: release v0.2.0"
git push origin main

# 4. Tag and push the tag — this triggers CI publishing
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

The tag push triggers `.github/workflows/publish.yml`, which:

1. Builds `lexicon.pkl` from the committed CSV
2. Runs the full test suite
3. Builds wheel + sdist
4. Publishes to TestPyPI
5. Publishes to PyPI (skipping pre-release tags like `v0.2.0-rc1`)
6. Creates a GitHub Release with the built artifacts

### Pre-release testing

To test on TestPyPI without publishing to PyPI, use a pre-release tag:

```bash
git tag -a v0.2.0-rc1 -m "Release candidate"
git push origin v0.2.0-rc1
```

Then install from TestPyPI and verify:

```bash
python -m venv /tmp/zg-test && source /tmp/zg-test/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            zomi-g2p==0.2.0rc1
zomi-g2p convert itna
deactivate
```

If it works, tag `v0.2.0` for the real release.

### Manual TestPyPI upload

You can also trigger the workflow manually from the Actions tab
(`workflow_dispatch` with `target=testpypi`). This publishes to TestPyPI
only — never to PyPI. PyPI releases always require a tag.

---

## Questions?

Open an issue with the `question` label, or start a discussion if the
repository has Discussions enabled. For data corrections, include:

- The word
- Expected syllables and tones
- Current output (`zomi-g2p convert WORD --json`)
- Your dialect / orthography reference, if relevant

Thank you for contributing!
