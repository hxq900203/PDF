from pathlib import Path


def unique_path(directory: Path, filename: str) -> Path:
    """返回 directory 下不存在的路径；重名时插入 ' (n)'，绝不覆盖。"""
    candidate = Path(directory) / filename
    stem, suffix = candidate.stem, candidate.suffix
    n = 1
    while candidate.exists():
        candidate = Path(directory) / f"{stem} ({n}){suffix}"
        n += 1
    return candidate
