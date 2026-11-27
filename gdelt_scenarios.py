"""Rebuild the offline theme catalog from one pinned public GKG archive."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile


BATCH = "20240115120000"
ARCHIVE = f"{BATCH}.gkg.csv.zip"
SHA256 = "cb76f10d4fced6f481c35d5641fa2d44368f3f73bccb845d798748f18e822f65"
CACHE = Path(__file__).resolve().parent / "scenarios" / "gdelt-themes.json"
SPLITS = {
    "GENERAL_HEALTH": "development",
    "PUBLIC_TRANSPORT": "development",
    "WATER_SECURITY": "held_out",
}


def load_catalog():
    return json.loads(CACHE.read_text(encoding="utf-8"))


def build_catalog(path):
    with path.open("rb") as source:
        if sha256(source.read()).hexdigest() != SHA256:
            raise ValueError(f"Expected the pinned GDELT archive {ARCHIVE}")
        source.seek(0)
        counts = dict.fromkeys(SPLITS, 0)
        records = 0
        with ZipFile(source) as archive, archive.open(f"{BATCH}.gkg.csv") as rows:
            for line in rows:
                fields = line.rstrip(b"\r\n").split(b"\t")
                if len(fields) != 27 or fields[1] != BATCH.encode("ascii"):
                    raise ValueError(f"Unexpected GKG record at row {records + 1}")
                records += 1
                tags = set(fields[7].decode("ascii").split(";"))
                for theme in counts.keys() & tags:
                    counts[theme] += 1

    if not all(counts.values()):
        raise ValueError("A selected theme is missing from the archive")
    return {
        "source_url": f"https://data.gdeltproject.org/gdeltv2/{ARCHIVE}",
        "archive_sha256": SHA256,
        "batch_utc": "2024-01-15T12:00:00Z",
        "scope": "Global GKG batch; each record counted once per V1THEMES tag.",
        "total_records": records,
        "themes": {
            theme: {"matching_records": count, "split": SPLITS[theme]}
            for theme, count in counts.items()
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_catalog(args.archive), indent=2))
