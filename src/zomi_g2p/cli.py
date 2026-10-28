"""
zomi_g2p.cli
============

Command-line interface for zomi-g2p.

Usage:
    zomi-g2p convert an5kham
    zomi-g2p convert an5kham --output ascii
    zomi-g2p text "an5kham apkaai" --no-tone
    zomi-g2p batch words.txt --json
    zomi-g2p info
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .converter import ZomiG2P
from .exceptions import ZomiG2PError
from .lexicon import load_default_lexicon, load_lexicon_from_dir


# ---------------------------------------------------------------------------
# Lexicon loading
# ---------------------------------------------------------------------------
def _load_g2p(
    lexicon_dir: str | None, 
    *,
    language: str | None = None,
    orthography: str | None = None,
    ) -> ZomiG2P:
    if lexicon_dir:
        path = Path(lexicon_dir)
        if not path.is_dir():
            raise ValueError(f"lexicon directory not found: {path}")
        lex = load_lexicon_from_dir(lexicon_dir)
        # return ZomiG2P(load_lexicon_from_dir(path))
    else:
        lex = load_default_lexicon()
    
    kwargs = {}
    if language is not None:
        kwargs["language"] = language
    if orthography is not None:
        kwargs["orthography"] = orthography
    return ZomiG2P(lex, **kwargs)
    # return ZomiG2P(lex, language=language, orthography=orthography)
    # return ZomiG2P(load_default_lexicon())


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_convert(args: argparse.Namespace) -> int:
    logger = logging.getLogger("zomi_g2p.cli")
    logger.info("convert %r", args.word)
    g2p = _load_g2p(
        args.lexicon,
        language=getattr(args, "language", None),
        orthography=getattr(args, "orthography", None)
        )
    
    # if args.language is not None:
    #         g2p.language = args.language          # or make it a constructor param
    # if args.orthography is not None:
    #     g2p.orthography = args.orthography
    
    try:
        result = g2p.convert(
            args.word,
            output=args.output,
            with_tone=not args.no_tone,
            sense=args.sense,
        )
    except ZomiG2PError as exc:
        # _print_error(exc, args.json)
        # return 1
        if args.json:
            print(json.dumps({"error": type(exc).__name__, "message": str(exc)}))
        else:
            logger.error("%s", exc)
            print(f"error: {exc}", file=sys.stderr)   # ← stderr, always visible
        return 1

    if args.json:
        print(json.dumps(_result_to_dict(result), ensure_ascii=False, indent=2))
    else:
        print(result.joined(sep=args.sep))
    return 0


def cmd_text(args: argparse.Namespace) -> int:
    g2p = _load_g2p(args.lexicon)
    if args.language is not None:
        g2p.language = args.language          # or make it a constructor param
    if args.orthography is not None:
        g2p.orthography = args.orthography
    try:
        output = g2p.convert_text(
            args.text,
            output=args.output,
            with_tone=not args.no_tone,
            sense=args.sense,
            unknown=args.unknown,
        )
    except ZomiG2PError as exc:
        _print_error(exc, args.json)
        return 1

    print(output)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    g2p = _load_g2p(args.lexicon)
    
    if args.language is not None:
        g2p.language = args.language          # or make it a constructor param
    if args.orthography is not None:
        g2p.orthography = args.orthography
    source = Path(args.file)
    if not source.is_file():
        raise ValueError(f"file not found: {source}")
        # print(f"error: file not found: {source}", file=sys.stderr)
        # return 2

    exit_code = 0
    with source.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            word = line.strip()
            if not word or word.startswith("#"):
                continue
            try:
                result = g2p.convert(
                    word,
                    output=args.output,
                    with_tone=not args.no_tone,
                    sense=args.sense,
                )
            except ZomiG2PError as exc:
                if args.json:
                    print(json.dumps({
                        "line": line_no, "word": word, "error": str(exc)
                    }, ensure_ascii=False))
                else:
                    print(f"line {line_no}: {word}: {exc}", file=sys.stderr)
                exit_code = 1
                if args.stop_on_error:
                    return exit_code
                continue

            if args.json:
                payload = _result_to_dict(result)
                payload["line"] = line_no
                print(json.dumps(payload, ensure_ascii=False))
            else:
                print(f"{word}\t{result.joined(sep=args.sep)}")
    return exit_code


def cmd_info(args: argparse.Namespace) -> int:
    g2p = _load_g2p(args.lexicon)
    
    if args.language is not None:
        g2p.language = args.language          # or make it a constructor param
    if args.orthography is not None:
        g2p.orthography = args.orthography
    lex = g2p.lexicon

    polyphones = sum(1 for w in lex.words() if len(lex.entries_for(w)) > 1)
    info = {
        "entries": len(lex),
        "words": len(list(lex.words())),
        "polyphones": polyphones,
        "tones": sorted(lex.tones),
        "segments": len(lex.segments),
    }

    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print(f"entries   : {info['entries']}")
        print(f"words     : {info['words']}")
        print(f"polyphones: {info['polyphones']}")
        print(f"tones     : {', '.join(info['tones'])}")
        print(f"segments  : {info['segments']}")
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _result_to_dict(result) -> dict:
    return {
        "word": result.word,
        "output": result.output,
        "with_tone": result.with_tone,
        "language": result.language,
        "orthography": result.orthography,
        "syllables": list(result.syllables),
        "tones": list(result.tones),
        "tone_sources": list(result.tone_sources),
        "phonemes": list(result.phonemes),
        "joined": result.joined(),
    }


def _print_error(exc: Exception, as_json: bool) -> None:
    if as_json:
        print(json.dumps({
            "error": type(exc).__name__,
            "message": str(exc),
        }, ensure_ascii=False))
    else:
        print(f"error: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zomi-g2p",
        description="Grapheme-to-Phoneme conversion for the Zomi language.",
    )
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="increase logging verbosity (-v: INFO, -vv: DEBUG)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="suppress warnings")
    sub = parser.add_subparsers(dest="command", required=True)

    # Shared arguments for commands that convert.
    def _add_convert_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--output", choices=["ipa", "ascii"], default="ipa",
                       help="output representation (default: ipa)")
        p.add_argument("--no-tone", action="store_true",
                       help="suppress tone marks")
        p.add_argument("--sense", default=None,
                       help="sense tag for polyphone disambiguation")
        p.add_argument("--lexicon", default=None, metavar="DIR",
                       help="use a custom lexicon directory")
        p.add_argument("--sep", default=" ",
                       help="syllable separator in output (default: space)")
        p.add_argument("--json", action="store_true",
                       help="emit machine-readable JSON")
        p.add_argument("--show-sources", action="store_true",
                        help="emit machine-readable JSON")
        p.add_argument("--language", default=None,
                        help="ISO 639-3 language code (default: from lexicon, or 'zol')")
        p.add_argument("--orthography", default=None,
                        help="orthography name (e.g., 'standard', 'tedim')")

    # convert
    p_convert = sub.add_parser("convert", help="convert a single word")
    p_convert.add_argument("word", help="word to convert")
    _add_convert_args(p_convert)
    p_convert.set_defaults(func=cmd_convert)

    # text
    p_text = sub.add_parser("text", help="convert whitespace-separated text")
    p_text.add_argument("text", help="text to convert")
    p_text.add_argument("--unknown", choices=["raise", "keep", "skip"],
                        default="raise",
                        help="policy for out-of-vocabulary words (default: raise)")
    _add_convert_args(p_text)
    p_text.set_defaults(func=cmd_text)

    # batch
    p_batch = sub.add_parser("batch", help="convert a file, one word per line")
    p_batch.add_argument("file", help="input file (one word per line; # comments)")
    p_batch.add_argument("--unknown", choices=["raise", "keep", "skip"],
                         default="raise")
    p_batch.add_argument("--stop-on-error", action="store_true",
                         help="abort on the first conversion error")
    _add_convert_args(p_batch)
    p_batch.set_defaults(func=cmd_batch)

    # info
    p_info = sub.add_parser("info", help="show lexicon statistics")
    p_info.add_argument("--lexicon", default=None, metavar="DIR")
    p_info.add_argument("--json", action="store_true")
    p_info.add_argument("--language", default=None)
    p_info.add_argument("--orthography", default=None)
    p_info.set_defaults(func=cmd_info)

    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    level = logging.WARNING
    if args.quiet:
        level = logging.ERROR
    elif args.verbose >= 2:
        level = logging.DEBUG
    elif args.verbose >= 1:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,   # keep stdout clean for results
    )
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        logging.getLogger("zomi_g2p.cli").error("%s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())