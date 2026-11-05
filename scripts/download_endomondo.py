"""Download Endomondo workout metadata from the FitRec project
(Ni, Muhlstein & McAuley, WWW 2019)."""
import argparse
import sys
from pathlib import Path

from download_heartsteps import download

URL = "https://mcauleylab.ucsd.edu/public_datasets/gdrive/fitrec/endomondoMeta.json.gz"
DEST = Path("data/raw/endomondo/endomondoMeta.json.gz")
EXPECTED_BYTES = 1_088_266_461  # from the server's content-length, checked 2026-11-04


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Endomondo metadata.")
    parser.add_argument("--force", action="store_true", help="re-download if the file exists")
    args = parser.parse_args()

    DEST.parent.mkdir(parents=True, exist_ok=True)

    if DEST.exists() and not args.force:
        print(f"skip      {DEST.name} (already downloaded)")
    else:
        print(f"download  {DEST.name} (about 1.1 GB, this takes a few minutes)")
        download(URL, DEST)

    size = DEST.stat().st_size
    ok = size == EXPECTED_BYTES
    status = "OK" if ok else "MISMATCH"
    print(f"{DEST.name}: {size / 1e6:,.1f} MB (expected {EXPECTED_BYTES / 1e6:,.1f} MB)  {status}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
