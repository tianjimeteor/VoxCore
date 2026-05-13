"""Allow ``python -m voxcore.cli gen-secret`` from inside the package."""
from .cli import main

if __name__ == "__main__":
    main()
