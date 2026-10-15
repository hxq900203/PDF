from collections import deque
from pathlib import Path
from typing import Callable

from .formats import detect_format
from .options import Options

# (src 文件, 临时输出目录, 选项) -> 按顺序的输出文件
Converter = Callable[[Path, Path, Options], list[Path]]

_EDGES: dict[tuple[str, str], Converter] = {}

# 第一版界面不提供的组合
DISABLED: set[tuple[str, str]] = {
    ("image", "word"), ("image", "excel"), ("word", "excel"), ("excel", "word"),
}

TARGET_ORDER = ["pdf", "word", "image", "excel"]


def register(src: str, dst: str):
    def decorator(fn: Converter) -> Converter:
        _EDGES[(src, dst)] = fn
        return fn
    return decorator


def find_route(src: str, dst: str) -> list[tuple[str, str, Converter]] | None:
    """BFS 求 src 到 dst 的最短转换路径。"""
    if src == dst:
        return None
    prev: dict[str, tuple[str, str, Converter]] = {}
    queue = deque([src])
    seen = {src}
    while queue:
        node = queue.popleft()
        if node == dst:
            route = []
            while node != src:
                edge = prev[node]
                route.append(edge)
                node = edge[0]
            return route[::-1]
        for (a, b), fn in _EDGES.items():
            if a == node and b not in seen:
                seen.add(b)
                prev[b] = (a, b, fn)
                queue.append(b)
    return None


def _targets_for(fmt: str) -> set[str]:
    return {t for t in TARGET_ORDER
            if (fmt, t) not in DISABLED and find_route(fmt, t) is not None}


def available_targets(paths: list[Path]) -> list[str]:
    formats = {f for f in (detect_format(Path(p)) for p in paths) if f}
    if not formats:
        return []
    common = set.intersection(*(_targets_for(f) for f in formats))
    return [t for t in TARGET_ORDER if t in common]
