import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from backend.app.db.vector import ensure_schema

    ensure_schema()
    print("schema_ok")


if __name__ == "__main__":
    main()


