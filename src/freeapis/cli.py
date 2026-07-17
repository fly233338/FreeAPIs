from __future__ import annotations

import argparse
import logging
import sys

from freeapis.constants import DATA_PATH, PROVIDER_ORDER, README_PATHS
from freeapis.models import FreeAPIsError
from freeapis.pipeline import check_repository, load_document, update_repository
from freeapis.render import render_readmes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m freeapis",
        description="Refresh and validate the FreeAPIs model directory.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    update = subparsers.add_parser("update", help="fetch and merge official sources")
    update.add_argument("--provider", choices=PROVIDER_ORDER)
    subparsers.add_parser("render", help="rebuild READMEs from models.json")
    subparsers.add_parser("check", help="validate data and generated READMEs")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args(argv)
    try:
        if args.command == "update":
            failed = update_repository(provider=args.provider)
            if failed:
                print(
                    "Updated valid provider data; failed providers kept as stale: "
                    + ", ".join(failed),
                    file=sys.stderr,
                )
                return 1
            print("Updated models.json, README navigation, and provider pages.")
            return 0
        if args.command == "render":
            document = load_document(DATA_PATH)
            render_readmes(document, README_PATHS)
            print("Rendered README navigation and provider pages from models.json.")
            return 0
        errors = check_repository()
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print("Data and generated READMEs are valid and synchronized.")
        return 0
    except (FreeAPIsError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
