from __future__ import annotations

import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"


def run_step(name: str, command: list[str]) -> None:
    print(f"\n=== {name} ===")
    completed = subprocess.run(command, cwd=BASE_DIR, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    python_executable = sys.executable

    run_step(
        "Czyszczenie CSV i JSON",
        [python_executable, str(SCRIPTS_DIR / "cleanup_spatial_data.py")],
    )
    run_step(
        "Czyszczenie SQLite",
        [python_executable, str(SCRIPTS_DIR / "cleanup_sqlite_bounds.py")],
    )
    run_step(
        "Odswiezenie danych z API",
        [
            python_executable,
            str(SCRIPTS_DIR / "api_refresh.py"),
            "--mode",
            "all",
            "--import-to-db",
        ],
    )

    print("\nProjekt odswiezony poprawnie.")


if __name__ == "__main__":
    main()
