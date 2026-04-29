#!/usr/bin/env python3
"""Run the PAFS silver and gold pipelines sequentially."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_pipeline(script_name: str) -> None:
    script_path = Path(__file__).resolve().parent / script_name
    print(f"Running {script_name}...")
    subprocess.check_call([sys.executable, str(script_path)])
    print(f"{script_name} completed.\n")


def main() -> None:
    run_pipeline("./silver/silver_pafs.py")
    run_pipeline("./gold/gold_pafs.py")
    run_pipeline("./gold/goldiris.py")
    print("All PAFS pipelines finished.")


if __name__ == "__main__":
    main()
