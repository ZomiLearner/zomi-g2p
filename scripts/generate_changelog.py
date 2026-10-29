#!/usr/bin/env python3
"""
Generate CHANGELOG.md from git tags and conventional-commit messages.

Usage:
    python scripts/generate_changelog.py
    python scripts/generate_changelog.py --output CHANGELOG.md
    python scripts/generate_changelog.py --repo-url https://github.com/user/zomi-g2p

Behavior:
- Versions are sorted semantically (handles pre-releases like v0.1.0-rc1).
- The first release includes all commits reachable from its tag.
- Subsequent releases include commits between the previous and current tag.
- Commit messages are categorized by prefix (Conventional Commits style).
- Merge commits and release-bump commits are filtered out.
- Version headers link to GitHub compare URLs when --repo-url is given.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Version parsing and sorting
# ---------------------------------------------------------------------------
_SEMVER_RE = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:[-.](?P<pre>[0-9A-Za-z.-]+))?$"
)


@dataclass(frozen=True, order=True)
class SemVer:
    major: int
    minor: int
    patch: int
    pre: tuple[str, ...] = field(default_factory=tuple)
    raw: str = field(compare=False, default="")

    @classmethod
    def parse(cls, tag: str) -> "SemVer | None":
        m = _SEMVER_RE.match(tag)
        if not m:
            return None
        pre_raw = m.group("pre")
        pre: tuple[str, ...] = ()
        if pre_raw:
            # Split on "." and "-" so rc.1 == rc-1 == rc1-ish ordering.
            pre = tuple(p for p in re.split(r"[.-]", pre_raw) if p)
        return cls(
            major=int(m.group("major")),
            minor=int(m.group("minor")),
            patch=int(m.group("patch")),
            pre=pre,
            raw=tag,
        )


def sort_key(tag: str) -> tuple:
    """Sort key: semantic version, non-semver tags pushed to the bottom."""
    v = SemVer.parse(tag)
    if v is None:
        # Unknown tags sort before all semver tags so they appear last
        # in a descending sort.
        return (0,)
    return (1, v)


def version_sorted(tags: list[str]) -> list[str]:
    """Return tags sorted ascending by semantic version."""
    return sorted(tags, key=sort_key)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------
def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"git {' '.join(args)} failed:\n{result.stderr.strip()}"
        )
    return result.stdout


def get_tags() -> list[str]:
    raw = run_git("tag", "-l")
    tags = [t.strip() for t in raw.splitlines() if t.strip()]
    return version_sorted(tags)


def get_commits(rev_range: str | None, tag: str) -> list[tuple[str, str]]:
    """Return (subject, short_hash) commits for a tag.

    If rev_range is given (e.g. "v0.1.0..v0.2.0"), use it.
    Otherwise, return all commits reachable from ``tag`` (first release).
    """
    if rev_range:
        args = ["log", rev_range, "--no-merges", "--pretty=format:%s|%h"]
    else:
        args = ["log", tag, "--no-merges", "--pretty=format:%s|%h"]
    out = run_git(*args)
    commits: list[tuple[str, str]] = []
    for line in out.splitlines():
        if "|" in line:
            msg, h = line.rsplit("|", 1)
            commits.append((msg.strip(), h.strip()))
    return commits


def tag_date(tag: str) -> str:
    out = run_git("log", "-1", "--format=%ad", "--date=short", tag)
    return out.strip() or "unknown"


def tag_timestamp(tag: str) -> datetime:
    out = run_git("log", "-1", "--format=%aI", tag)
    try:
        return datetime.fromisoformat(out.strip())
    except ValueError:
        return datetime.now()


# ---------------------------------------------------------------------------
# Categorization
# ---------------------------------------------------------------------------
# Ordered: first match wins.
_CATEGORIES: list[tuple[str, re.Pattern]] = [
    ("⚠️ Breaking Changes", re.compile(r"^(breaking|incompatible)\b", re.I)),
    ("✨ New Features", re.compile(r"^(feat|feature|add|new)\b", re.I)),
    ("🐛 Bug Fixes", re.compile(r"^(fix|bug|resolve|correct|repair)\b", re.I)),
    ("🔄 Reverts", re.compile(r"^revert\b", re.I)),
    ("📚 Documentation", re.compile(r"^(docs?|readme|documentation)\b", re.I)),
    ("🔧 Refactoring", re.compile(r"^(refactor|clean|rename|move|restructure)\b", re.I)),
    ("✅ Tests", re.compile(r"^(test|spec|pytest)\b", re.I)),
    ("⚙️ CI/CD", re.compile(r"^(ci|cd|action|workflow|build)\b", re.I)),
    ("💄 Code Style", re.compile(r"^(style|format|lint)\b", re.I)),
    ("⚡ Performance", re.compile(r"^(perf|performance|optimize)\b", re.I)),
    ("📦 Dependencies", re.compile(r"^(chore\(deps\)|deps|bump)\b", re.I)),
    ("🧹 Chores", re.compile(r"^(chore|misc|cleanup)\b", re.I)),
]

_OTHER = "📦 Other Changes"

# Commits that should never appear in the changelog.
# merge stays skipped (merge commits are noise), and release bumps stay skipped.
_SKIP = re.compile(
    r"^(merge\b|release v?\d|chore: release|bump version)", re.I
)


def categorize_commit(msg: str) -> str:
    for label, pattern in _CATEGORIES:
        if pattern.match(msg):
            return label
    return _OTHER


# ---------------------------------------------------------------------------
# Changelog generation
# ---------------------------------------------------------------------------
def compare_url(repo_url: str, prev_tag: str | None, tag: str) -> str:
    if prev_tag:
        return f"{repo_url}/compare/{prev_tag}...{tag}"
    return f"{repo_url}/releases/tag/{tag}"


def generate_changelog(repo_url: str | None, output: Path) -> None:
    tags = get_tags()
    if not tags:
        raise SystemExit("No tags found. Create a tag first (e.g. `git tag v0.1.0`).")

    lines: list[str] = [
        "# Changelog",
        "",
        "All notable changes to this project will be documented in this file.",
        "",
        "The format is based on [Keep a Changelog](https://keepachangelog.com/),",
        "and this project adheres to [Semantic Versioning](https://semver.org/).",
        "",
    ]

    # Iterate newest → oldest. prev_tag is the tag *before* the current one
    # in chronological order (i.e. the next item in the ascending list).
    ascending = tags
    for idx in range(len(ascending) - 1, -1, -1):
        tag = ascending[idx]
        prev_tag = ascending[idx - 1] if idx > 0 else None

        version = tag.lstrip("v")
        date_str = tag_date(tag)
        rev_range = f"{prev_tag}..{tag}" if prev_tag else None
        commits = get_commits(rev_range, tag)

        # Filter out skipped commits.
        commits = [(m, h) for m, h in commits if not _SKIP.match(m)]

        # Link the version header if repo_url is provided.
        if repo_url:
            header = f"## [{version}]({compare_url(repo_url, prev_tag, tag)}) — {date_str}"
        else:
            header = f"## [{version}] — {date_str}"

        lines.append(header)
        lines.append("")

        if not commits:
            lines.append("_No changes recorded._")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        # Group by category, preserving category order from _CATEGORIES.
        grouped: dict[str, list[str]] = {}
        for msg, h in commits:
            cat = categorize_commit(msg)
            grouped.setdefault(cat, []).append(f"- {msg} ([`{h}`](../../commit/{h}))" if repo_url else f"- {msg} `{h}`")

        # Emit in category order, then "Other" last.
        ordered = [label for label, _ in _CATEGORIES] + [_OTHER]
        for cat in ordered:
            if cat not in grouped:
                continue
            lines.append(f"### {cat}")
            lines.extend(grouped[cat])
            lines.append("")

        lines.append("---")
        lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ wrote {output} ({len(tags)} releases)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", "-o", type=Path, default=Path("CHANGELOG.md"),
        help="output path (default: CHANGELOG.md)",
    )
    parser.add_argument(
        "--repo-url", default=None,
        help="GitHub repo URL for compare links, e.g. https://github.com/user/zomi-g2p",
    )
    args = parser.parse_args(argv)

    repo_url = args.repo_url.rstrip("/") if args.repo_url else None
    generate_changelog(repo_url, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())