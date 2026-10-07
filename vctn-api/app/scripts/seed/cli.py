"""Command line entry point.

    python -m app.scripts.seed                     # production system seed
    python -m app.scripts.seed --mode=test         # system seed + test data
    python -m app.scripts.seed --runs=3            # idempotency verification

The initial administrator password is read from ``VCTN_SEED_ADMIN_PASSWORD``; a
missing value aborts the run with ``SEED_ADMIN_PASSWORD_REQUIRED``.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from app.core.config import get_settings
from app.scripts.seed.errors import SeedError
from app.scripts.seed.report import render_final_block, render_markdown
from app.scripts.seed.runner import (
    ADMIN_PASSWORD_ENV,
    DEFAULT_ADMIN_USERNAME,
    MODE_SYSTEM,
    MODE_TEST,
    TEST_PASSWORD_ENV,
    execute,
)

DEFAULT_REPORT_PATH: str = "SEED_DATA_REPORT.md"

_EXIT_OK: int = 0
_EXIT_FAILED: int = 1
_EXIT_PRECONDITION: int = 2


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the seed CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m app.scripts.seed",
        description="Idempotent PostgreSQL seed data for the VCTN backend.",
    )
    parser.add_argument(
        "--mode",
        choices=(MODE_SYSTEM, MODE_TEST),
        default=MODE_SYSTEM,
        help="system = production data only; test = system data + test accounts",
    )
    parser.add_argument(
        "--admin-username",
        default=DEFAULT_ADMIN_USERNAME,
        help="username of the initial SUPER_ADMIN account",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="how many times to run the seed (used to verify idempotency)",
    )
    parser.add_argument(
        "--report-path",
        default=DEFAULT_REPORT_PATH,
        help="where the markdown report is written",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="do not write the markdown report",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the seed and print the final report block."""
    args = build_parser().parse_args(argv)

    # Test mode creates accounts whose passwords come from an environment
    # variable and are known to everyone with access to CI. There is no
    # legitimate reason to run it against production, and one careless run is
    # enough to leave a working login on the internet. Refuse it outright
    # rather than warn: a warning gets scrolled past.
    if args.mode == MODE_TEST and get_settings().APP_ENV == "production":
        print(
            "[seed] refused: --mode=test is never allowed when APP_ENV=production",
            file=sys.stderr,
        )
        return _EXIT_PRECONDITION

    command = f"python -m app.scripts.seed --mode={args.mode} --runs={args.runs}"

    try:
        outcome = asyncio.run(
            execute(
                mode=args.mode,
                admin_username=args.admin_username,
                runs=args.runs,
                progress=lambda message: print(f"[seed] {message}"),
            )
        )
    except SeedError as exc:
        print(f"[seed] FAILED code={exc.code}: {exc}")
        if exc.code == "SEED_ADMIN_PASSWORD_REQUIRED":
            print(f"[seed] set {ADMIN_PASSWORD_ENV} and retry")
        if exc.code == "SEED_TEST_PASSWORD_REQUIRED":
            print(f"[seed] set {TEST_PASSWORD_ENV} and retry")
        return _EXIT_PRECONDITION

    print(
        render_final_block(
            outcome,
            database="PostgreSQL",
            command=command,
            admin_username=args.admin_username,
        )
    )

    if not args.no_report:
        Path(args.report_path).write_text(
            render_markdown(outcome, command=command, admin_username=args.admin_username),
            encoding="utf-8",
        )
        print(f"[seed] report written to {args.report_path}")

    return _EXIT_OK if outcome.status == "PASS" else _EXIT_FAILED


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
