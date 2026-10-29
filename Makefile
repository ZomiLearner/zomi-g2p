# |workspace|out.txt|log.txt|src/*.egg-info|htmlcov
.PHONY: tree
EXCLUDE ?= node_modules|.git|__pycache__|dist|*.egg-info|htmlcov|out.txt|log.txt|tmp

tree:
	@if command -v tree > /dev/null; then \
		tree -I "$(EXCLUDE)"; \
	else \
		echo "Error: 'tree' command is not installed."; \
	fi

fetch-lexicon:
	python3 scripts/fetch_lexicon.py # --output src/zomi_g2p/data/lexicon.csv

.PHONY: build-pickle
build-pickle:
	python scripts/build_pickle.py

.PHONY: release-check
release-check:
	python scripts/build_pickle.py
	pytest -q
	python -m build
	twine check dist/*
	unzip -l dist/*.whl | grep -E "lexicon\.(csv|pkl)|segments\.yaml|tones\.yaml"

.PHONY: test_pipeline
test_pipeline:
	python3 scripts/test_pipeline.py

test:
	coverage run -m pytest && coverage report -m

quicktest:
	python -c "from zomi_g2p.lexicon import DataValidationError; print(DataValidationError)"
	pytest tests/test_lexicon.py -q

# pytest tests/test_lexicon.py::TestDefaultLexicon::test_loads_packaged_data
coverage: 
	coverage report -m --include='src/zomi_g2p/converter.py' --show-missing

.PHONY: clean
clean:
	rm -rf __pycache__ dist

build:
	# Clean build artifacts
	rm -rf dist/ build/ src/zomi_g2p.egg-info/ src/*.egg-info/
	# Rebuild
	python -m build

checkdist:
	twine check dist/*

html_coverage:
	coverage html

.PHONY: cli-test
cli-test:
	pytest tests/test_cli.py -q

.PHONY: try-cli
try-cli:
	zomi-g2p info
	zomi-g2p convert ankham
	zomi-g2p convert ankham --output ascii
	zomi-g2p -vv convert ankham
	zomi-g2p -q batch tests/data/words.txt
	zomi-g2p info -v
	zomi-g2p -q convert unknownword

.PHONY: batch
batch:
	zomi-g2p -q batch tests/data/words.txt --json

generate_lexicon:
	python scripts/generate_lexicon.py tests/data/words.txt > generated.csv
####### To check if the package-data + importlib.resources are correctly wired #######

# python -m venv /tmp/zg-test
# source /tmp/zg-test/bin/activate
# # pip install -e .
# pip install dist/zomi_g2p-0.1.0-py3-none-any.whl 
# python -c "
# from zomi_g2p.lexicon import load_default_lexicon
# lex = load_default_lexicon()
# print('entries:', len(lex))
# print('tones:', sorted(lex.tones))
# print('words:', list(lex.words())[:5])
# "
# deactivate

####### Build the wheel and inspect it #######
# python -m build
# unzip -l dist/zomi_g2p-0.1.0-py3-none-any.whl | grep data/
# unzip -l dist/zomi_g2p-0.1.0-py3-none-any.whl

####### Next steps #######
#     twine check dist/* — validates metadata and README rendering.
#     If clean, twine upload --repository testpypi dist/* to TestPyPI first.
#     Install from TestPyPI in a fresh venv and run the smoke test above.
#     If that works, upload to real PyPI.

activate-test-venv:
	python -m venv /tmp/zg-test
	source /tmp/zg-test/bin/activate

activate-base-venv:
	@bash -c "source /mnt/d/venv/bin/activate"
	@echo "source /mnt/d/venv/bin/activate"

####### Pre-upload checklist #######
# # 1. Fill LICENSE
# vi LICENSE   # add SPDX header + text

# # 2. Add readme to pyproject.toml
# # [project] readme = "README.md"

# # 3. Rebuild
# rm -rf dist/ build/ src/zomi_g2p.egg-info/
# python -m build

# # 4. Verify
# unzip -l dist/*.whl | grep -E 'LICENSE|METADATA'
# twine check dist/*

# # 5. TestPyPI
# python -m twine upload --repository testpypi dist/*

# # 6. Fresh venv smoke test
# python -m venv /tmp/zg && source /tmp/zg/bin/activate
# pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ zomi-g2p==0.1.0
# python -c "from zomi_g2p import ZomiG2P; from zomi_g2p.lexicon import load_default_lexicon; g=ZomiG2P(load_default_lexicon()); print(g.convert('ankham').joined())"
# deactivate

# python -c "
# from zomi_g2p import ZomiG2P
# from zomi_g2p.lexicon import load_default_lexicon
# g=ZomiG2P(load_default_lexicon())
# print(g.convert('ankham').joined())
# "

####### Does it still load in reasonable time? #######
# python -c "
# import time
# from zomi_g2p.lexicon import load_default_lexicon
# t=time.perf_counter()
# lex=load_default_lexicon()
# print(f'{len(lex)} entries loaded in {time.perf_counter()-t:.3f}s')
# "

# python -c "
# import time
# from zomi_g2p.lexicon import load_default_lexicon
# t = time.perf_counter()
# lex = load_default_lexicon()
# print(f'{len(lex)} entries in {time.perf_counter()-t:.2f}s')
# "

# # 7. If all good, upload to real PyPI
# python -m twine upload dist/*

####### ✅ Verify after rebuilding #######
# # 1. Rebuild the pickle
# python scripts/fetch_lexicon.py

# # 2. Confirm the file exists and has reasonable size
# ls -lh src/zomi_g2p/data/lexicon.pkl   # expect ~5–15 MB

# # 3. Rebuild the wheel and check it's included
# rm -rf dist/ build/ src/*.egg-info/
# python -m build
# unzip -l dist/*.whl | grep -E "lexicon\.(csv|pkl)"

# # 4. Time the CLI
# time zomi-g2p convert ankham
# # expect ~0.5s or less (vs 2.08s before)

# # 5. Confirm the pickle path is actually used
# zomi-g2p -vv convert ankham 2>&1 | grep -i "pickle\|parsing csv"
# # expect: "loading lexicon from cache" or silence (no "parsing CSVs")
