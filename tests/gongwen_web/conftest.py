import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests" / "gongwen")]
CLI = ROOT / "gongwen-web" / "tests" / "cli.js"


def node(*args):
    return subprocess.run(["node", str(CLI), *map(str, args)], capture_output=True, text=True, encoding="utf-8")


@pytest.fixture
def js():
    """调用 JS 核心：js("classify", path) -> 解析后的 JSON；出错抛 RuntimeError(stderr, returncode)。"""
    def call(*args):
        r = node(*args)
        if r.returncode != 0:
            raise RuntimeError(r.stderr, r.returncode)
        return json.loads(r.stdout) if r.stdout else None
    return call
