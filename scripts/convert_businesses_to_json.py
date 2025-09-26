import json
from pathlib import Path
from typing import Dict, Any


def parse_kv_text(content: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for line in content.split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip().lower().replace(" ", "_")] = value.strip()
    return data


def convert_txt_file_to_json(txt_path: Path) -> Path:
    content = txt_path.read_text(encoding="utf-8")
    kv = parse_kv_text(content)

    business_name = kv.get("business_name", "")
    owner_name = kv.get("owner_name", kv.get("name", ""))
    category = kv.get("business_category", kv.get("category", ""))
    tags = kv.get("business_tags", kv.get("tags", ""))
    lat_str = kv.get("latitude", "")
    lon_str = kv.get("longitude", "")
    lat_long = kv.get("lat_long", "")

    latitude = None
    longitude = None
    try:
        if lat_str:
            latitude = float(lat_str)
        if lon_str:
            longitude = float(lon_str)
    except ValueError:
        latitude, longitude = None, None

    if (latitude is None or longitude is None) and lat_long and "," in lat_long:
        try:
            parts = [p.strip() for p in lat_long.split(",", 1)]
            if len(parts) == 2:
                latitude = float(parts[0])
                longitude = float(parts[1])
        except ValueError:
            latitude, longitude = None, None

    payload: Dict[str, Any] = {
        "name": owner_name,
        "owner_name": owner_name,
        "business_name": business_name,
        "business_category": category,
        "business_tags": tags,
        "latitude": latitude,
        "longitude": longitude,
        "lat_long": lat_long or (f"{latitude},{longitude}" if latitude is not None and longitude is not None else ""),
    }

    json_path = txt_path.with_suffix(".json")
    # Non-destructive: do not overwrite existing JSON
    if not json_path.exists():
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return json_path


def convert_all(businesses_dir: Path) -> int:
    count = 0
    for txt_path in businesses_dir.glob("*.txt"):
        convert_txt_file_to_json(txt_path)
        count += 1
    return count


if __name__ == "__main__":
    # Default directory: project_root/data/businesses
    project_root = Path(__file__).resolve().parents[1]
    businesses_dir = project_root / "data" / "businesses"
    businesses_dir.mkdir(parents=True, exist_ok=True)
    converted = convert_all(businesses_dir)
    print(f"Converted {converted} .txt files to .json in {businesses_dir}")


