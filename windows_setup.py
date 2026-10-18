"""Stable PyInstaller entry point importing the setup wizard as a package."""

from setup.windows_wizard import main


if __name__ == "__main__":
    raise SystemExit(main())
