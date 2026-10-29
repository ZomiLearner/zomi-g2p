# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-10-29

### ✨ New Features
- feat(scripts): add changelog generation script `17c5c4c`
- feat(validation): validate required columns after fetching the lexicon csv file `40128de`
- feat(pipeline): add scripts for lexicon generation and fetching `020aa9f`
- feat(core): implement zomi_g2p converter engine and CLI `a4bd12b`

### 🐛 Bug Fixes
- fix: use verrsion in pyproject.toml as single source of truth \n- Update cli arguments to include __version__ `0dedd82`

### 📚 Documentation
- docs: add code of conduct and contributing guide `20481d2`

### ✅ Tests
- test: add unit test suite for core converter and CLI `90d3be7`

### ⚙️ CI/CD
- ci: use CHANGELOG.md for GitHub Release notes `fe1edfd`
- ci(github): add publish workflow `066e9c2`

### 🧹 Chores
- chore: create tests/data folder and update Makefile that uses the files under it and update gitignore accordingly `d7137ba`
- chore: stop tracking workspace/todo, move workspace/words.txt to tests/data/words.txt `7c55cc1`
- chore(workspace): add local todo tracker and test_words helper file `dcdad46`
- chore(dev-env): configure development environment, tools, and scripts `093685a`
- chore(repo): ignore workspace/tmp, build artifacts, and other development files `67b8879`
- chore: initialize project configuration and repository scaffolding `53cc5b5`
- chore: initial commit `f95376e`

---
