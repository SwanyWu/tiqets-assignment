"""Allow ``python -m tiqets``."""

from tiqets.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
