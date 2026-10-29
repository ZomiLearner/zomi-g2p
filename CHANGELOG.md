# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.2](https://github.com/ZomiLearner/zomi-g2p/releases/tag/v0.1.2) — 2026-10-29

### ✨ New Features
- feat(scripts): add changelog generation script ([`17c5c4c`](../../commit/17c5c4c))
- feat(validation): validate required columns after fetching the lexicon csv file ([`40128de`](../../commit/40128de))
- feat(pipeline): add scripts for lexicon generation and fetching ([`020aa9f`](../../commit/020aa9f))
- feat(core): implement zomi_g2p converter engine and CLI ([`a4bd12b`](../../commit/a4bd12b))

### 🐛 Bug Fixes
- fix: use verrsion in pyproject.toml as single source of truth \n- Update cli arguments to include __version__ ([`0dedd82`](../../commit/0dedd82))

### 📚 Documentation
- docs: add code of conduct and contributing guide ([`20481d2`](../../commit/20481d2))

### ✅ Tests
- test: add unit test suite for core converter and CLI ([`90d3be7`](../../commit/90d3be7))

### ⚙️ CI/CD
- ci: add checkout step in 'release' job' ([`830c404`](../../commit/830c404))
- ci: use CHANGELOG.md for GitHub Release notes ([`fe1edfd`](../../commit/fe1edfd))
- ci(github): add publish workflow ([`066e9c2`](../../commit/066e9c2))

### 🧹 Chores
- chore: bump version to 0.1.2 ([`56c0ca0`](../../commit/56c0ca0))
- chore: bump version to 0.1.1 ([`f00b658`](../../commit/f00b658))
- chore: create tests/data folder and update Makefile that uses the files under it and update gitignore accordingly ([`d7137ba`](../../commit/d7137ba))
- chore: stop tracking workspace/todo, move workspace/words.txt to tests/data/words.txt ([`7c55cc1`](../../commit/7c55cc1))
- chore(workspace): add local todo tracker and test_words helper file ([`dcdad46`](../../commit/dcdad46))
- chore(dev-env): configure development environment, tools, and scripts ([`093685a`](../../commit/093685a))
- chore(repo): ignore workspace/tmp, build artifacts, and other development files ([`67b8879`](../../commit/67b8879))
- chore: initialize project configuration and repository scaffolding ([`53cc5b5`](../../commit/53cc5b5))
- chore: initial commit ([`f95376e`](../../commit/f95376e))

---
