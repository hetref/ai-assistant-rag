from pathlib import Path


def delete_all_txt(businesses_dir: Path) -> int:
    removed = 0
    for txt_path in businesses_dir.glob("*.txt"):
        try:
            txt_path.unlink(missing_ok=True)
            removed += 1
        except FileNotFoundError:
            pass
    return removed


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    businesses_dir = project_root / "data" / "businesses"
    businesses_dir.mkdir(parents=True, exist_ok=True)
    deleted = delete_all_txt(businesses_dir)
    print(f"Deleted {deleted} .txt files from {businesses_dir}")


