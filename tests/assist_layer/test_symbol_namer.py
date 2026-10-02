"""ADR-0007 — the AI names shapes from a fixed list; remembered names are never paid for again."""
from types import SimpleNamespace

from agent.dxf_pipeline.passes.shapes import ShapeGroup
from assist.symbol_namer import NAME_SYMBOLS_TOOL, make_shape_namer, name_shapes


class _FakeClient:
    def __init__(self, answers):
        self.answers, self.requests = answers, []
        self.messages = self

    def create(self, **kw):
        self.requests.append(kw)
        block = SimpleNamespace(type="tool_use", name="name_symbols", input={"symbols": self.answers})
        return SimpleNamespace(content=[block], usage=SimpleNamespace(input_tokens=2000, output_tokens=100))


def _g(sig, n=3):
    return ShapeGroup(signature=sig, count=n, sheet="L-01", image_png_b64="iVBORw0KGgo=")


def test_each_picture_is_sent_numbered_with_the_legend_and_the_fixed_list():
    client = _FakeClient([{"id": "S1", "item": "Vapour Proof Light", "legend_line": "2x18W vapour proof"},
                          {"id": "S2", "item": "Not an electrical symbol", "legend_line": ""}])
    names, cost = name_shapes([_g("a"), _g("b")], ["2x18W vapour proof LED"], client=client)
    assert names["a"].item == "Vapour Proof Light" and names["b"].item == "Not an electrical symbol"
    assert cost > 0
    req = client.requests[0]
    assert req["tool_choice"] == {"type": "tool", "name": "name_symbols"}
    images = [c for c in req["messages"][0]["content"] if c["type"] == "image"]
    assert len(images) == 2
    assert "Vapour Proof Light" in NAME_SYMBOLS_TOOL["input_schema"]["properties"]["symbols"]["items"]["properties"]["item"]["enum"]


def test_an_answer_outside_the_list_is_ignored():
    client = _FakeClient([{"id": "S1", "item": "Magic lamp", "legend_line": ""}])
    names, _ = name_shapes([_g("a")], [], client=client)
    assert names == {}


def test_remembered_shapes_are_reused_and_only_new_ones_are_asked():
    client = _FakeClient([{"id": "S1", "item": "LED Downlight", "legend_line": ""}])
    saved = []
    namer = make_shape_namer(client=client, remembered={"known": ("Bulkhead Light", "person")},
                             on_named=lambda sig, item: saved.append((sig, item)))
    names, _ = namer([_g("known"), _g("new")], [])
    assert names == {"known": ("Bulkhead Light", "person"), "new": ("LED Downlight", "ai")}
    sent = [c for c in client.requests[0]["messages"][0]["content"] if c["type"] == "image"]
    assert len(sent) == 1 and saved == [("new", "LED Downlight")]


def test_nothing_new_means_no_ai_call():
    client = _FakeClient([])
    names, cost = make_shape_namer(client=client, remembered={"k": ("Pole Light", "ai")})([_g("k")], [])
    assert names == {"k": ("Pole Light", "ai")} and cost == 0 and client.requests == []
