import csv
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from upload_api import DataRecord, ensure_dirs_and_csv, write_business_file, DATA_DIR, TXT_MIRROR_PATH  # noqa: E402


def backfill_from_txt(txt_path: Path | None = None) -> int:
    ensure_dirs_and_csv()
    source = txt_path or TXT_MIRROR_PATH
    if not source.exists():
        print(f"No source file found at {source}")
        return 0

    written = 0
    with source.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)

        # Accept either normalized header (name,business_name,lat,lon,category,tags)
        # or original CSV header (name,business_name,lat_long,category,tags)
        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue

            # Flexible parsing depending on columns count
            if len(row) >= 6:
                name = row[0].strip()
                business_name = row[1].strip()
                third = row[2].strip()
                fourth = row[3].strip()
                category = row[4].strip()
                tags = row[5].strip()

                if "," in third and fourth.replace("-", "").replace(".", "").isdigit() is False:
                    # Likely lat_long in third and category in fourth (original csv format)
                    lat_long = third
                else:
                    # Treat as lat, lon separate (normalized format)
                    lat_long = f"{third},{fourth}"
            elif len(row) >= 5:
                name = row[0].strip()
                business_name = row[1].strip()
                lat_long = row[2].strip()
                category = row[3].strip()
                tags = row[4].strip()
            else:
                continue

            record = DataRecord(
                name=name,
                business_name=business_name,
                lat_long=lat_long,
                business_category=category,
                business_tags=tags,
            )
            write_business_file(record)
            written += 1

    print(f"Backfilled {written} business files from {source}")
    return written


if __name__ == "__main__":
    custom = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    backfill_from_txt(custom)


