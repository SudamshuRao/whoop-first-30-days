"""Download HeartSteps V1 data (Klasnja et al., 2019; CC BY 4.0)."""
import argparse
import sys
from pathlib import Path

import requests

BASE_URL = "https://raw.githubusercontent.com/klasnja/HeartStepsV1/main"
OUT_DIR = Path("data/raw/heartsteps")
EXPECTED_ROWS = {
    "users.csv": 37,
    "suggestions.csv": 8274,
    "jbsteps.csv": 237865,
    "gfsteps.csv": 197524,
}


def download(url: str, dest: Path) -> None:
    """Stream url to dest. Writes to a .part file first so a failed download never looks finished."""
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    tmp = dest.with_suffix(dest.suffix + ".part")
    with open(tmp, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
    tmp.rename(dest)


def count_rows(path: Path) -> int:
    """Data rows in a CSV (lines minus the header)."""
    with open(path, "rb") as f:
        return sum(1 for _ in f) - 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Download HeartSteps V1 data.")
    parser.add_argument("--force", action="store_true", help="re-download files that already exist")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. download
    for name in [*EXPECTED_ROWS, "LICENSE"]:
        dest = OUT_DIR / name
        if dest.exists() and not args.force:
            print(f"skip      {name} (already downloaded)")
            continue
        folder = "data_files/" if name.endswith(".csv") else ""
        print(f"download  {name}")
        download(f"{BASE_URL}/{folder}{name}", dest)

    # 2. validate
    all_ok = True
    print(f"\n{'file':<18}{'MB':>7}{'rows':>10}{'expected':>10}  status")
    for name, expected in EXPECTED_ROWS.items():
        path = OUT_DIR / name
        rows = count_rows(path)
        size_mb = path.stat().st_size / 1e6
        status = "OK" if rows == expected else "MISMATCH"
        all_ok = all_ok and status == "OK"
        print(f"{name:<18}{size_mb:>7.1f}{rows:>10,}{expected:>10,}  {status}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())