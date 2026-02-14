from __future__ import annotations

import argparse
import io
import pathlib
import urllib.request
import zipfile


DEFAULT_URL = "https://ucdp.uu.se/downloads/brd/ucdp-brd-conf-251-csv.zip"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download and extract UCDP BRD (conflict-level) into data/raw/ucdp/.")
    p.add_argument("--url", default=DEFAULT_URL, help=f"Zip URL to download (default: {DEFAULT_URL})")
    p.add_argument("--outdir", default="data/raw/ucdp", help="Output directory (default: data/raw/ucdp)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading: {args.url}")
    with urllib.request.urlopen(args.url, timeout=300) as resp:
        data = resp.read()
    print(f"Downloaded bytes: {len(data):,}")

    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()
    print(f"Zip entries: {len(names)}")
    z.extractall(outdir)
    print(f"Extracted to: {outdir}")
    for name in names[:20]:
        print(f"- {name}")


if __name__ == "__main__":
    main()

