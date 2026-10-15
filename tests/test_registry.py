from pathlib import Path

import pytest

from app.core import registry
from app.core.registry import available_targets, find_route


@pytest.fixture
def fake_edges(monkeypatch):
    noop = lambda src, out_dir, opts: []
    edges = {e: noop for e in [("word", "pdf"), ("excel", "pdf"), ("pdf", "image"),
                               ("image", "pdf"), ("pdf", "word"), ("pdf", "excel")]}
    monkeypatch.setattr(registry, "_EDGES", edges)


def hops(route):
    return [e[:2] for e in route]


def test_direct_route(fake_edges):
    assert hops(find_route("word", "pdf")) == [("word", "pdf")]


def test_two_hop_route(fake_edges):
    assert hops(find_route("excel", "image")) == [("excel", "pdf"), ("pdf", "image")]


def test_same_format_none(fake_edges):
    assert find_route("pdf", "pdf") is None


def test_unreachable_none(monkeypatch):
    monkeypatch.setattr(registry, "_EDGES", {("word", "pdf"): None})
    assert find_route("pdf", "word") is None


def test_targets_word(fake_edges):
    assert available_targets([Path("a.docx")]) == ["pdf", "image"]


def test_targets_pdf(fake_edges):
    assert available_targets([Path("a.pdf")]) == ["word", "image", "excel"]


def test_targets_image(fake_edges):
    assert available_targets([Path("a.png")]) == ["pdf"]


def test_targets_mixed_intersection(fake_edges):
    assert available_targets([Path("a.pdf"), Path("b.png")]) == []
    assert available_targets([Path("a.docx"), Path("b.xlsx")]) == ["pdf", "image"]


def test_targets_unknown_ignored(fake_edges):
    assert available_targets([Path("a.txt"), Path("b.png")]) == ["pdf"]
    assert available_targets([Path("a.txt")]) == []


def test_register_adds_edge(monkeypatch):
    monkeypatch.setattr(registry, "_EDGES", {})

    @registry.register("pdf", "image")
    def conv(src, out_dir, opts):
        return []

    assert hops(find_route("pdf", "image")) == [("pdf", "image")]
    assert find_route("pdf", "image")[0][2] is conv
