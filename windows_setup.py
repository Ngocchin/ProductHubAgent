"""Stable PyInstaller entry point and headless frozen-module smoke test."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


SELF_TEST_MODULES = (
    "setup",
    "setup.async_utils",
    "setup.github_config",
    "setup.product_hub_enrollment",
    "setup.windows_wizard",
    "playwright",
    "playwright.async_api",
    "telethon",
    "telethon.sessions",
    "nacl.public",
)


def run_self_test() -> int:
    """Import the frozen dependency graph without creating the Tk interface."""
    results = []
    for module_name in SELF_TEST_MODULES:
        try:
            importlib.import_module(module_name)
            results.append(f"OK {module_name}")
        except Exception as exc:
            missing_name = getattr(exc, "name", None)
            detail = f"{type(exc).__name__} ({missing_name})" if missing_name else type(exc).__name__
            results.append(f"FAIL {module_name}: {detail}")
            break

        report_path = os.environ.get("VUA_THO_SETUP_SELF_TEST_REPORT")
        if report_path:
            try:
                Path(report_path).write_text("\n".join(results) + "\n", encoding="utf-8")
            except OSError:
                pass

    failed = any(line.startswith("FAIL ") for line in results)
    results.append("SELF-TEST FAILED" if failed else f"SELF-TEST OK: imported {len(results)} required modules")
    report_path = os.environ.get("VUA_THO_SETUP_SELF_TEST_REPORT")
    if report_path:
        try:
            Path(report_path).write_text("\n".join(results) + "\n", encoding="utf-8")
        except OSError:
            pass
    stream = sys.stderr if failed else sys.stdout
    if stream is not None:
        print("\n".join(results), file=stream)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["--self-test"]:
        return run_self_test()
    if arguments:
        if sys.stderr is not None:
            print("Usage: VuaThoQASetup.exe [--self-test]", file=sys.stderr)
        return 2
    from setup.windows_wizard import main as wizard_main
    return wizard_main()


if __name__ == "__main__":
    raise SystemExit(main())
