"""ADR-0008 — the AI only says which names are the same thing; it never picks a number."""
from types import SimpleNamespace

from assist.finding_matcher import make_name_matcher, match_names


class _FakeClient:
    def __init__(self, answers):
        self.answers, self.requests = answers, []
        self.messages = self

    def create(self, **kw):
        self.requests.append(kw)
        block = SimpleNamespace(type="tool_use", name="match_names", input={"matches": self.answers})
        return SimpleNamespace(content=[block], usage=SimpleNamespace(input_tokens=800, output_tokens=120))


def test_answers_can_only_name_what_was_offered():
    client = _FakeClient([
        {"pdf_name": "KIOSK busbar", "dwg_name": "KIOSK", "verdict": "same", "reason": "busbar of the kiosk"},
        {"pdf_name": "DB-9", "dwg_name": "", "verdict": "different", "reason": "no such board"},
    ])
    found, cost = match_names("equipment", ["KIOSK", "DB-A"], ["KIOSK busbar", "DB-9"], client=client)
    assert found == {"KIOSK busbar": ("KIOSK", "same", "busbar of the kiosk"),
                     "DB-9": ("", "different", "no such board")}
    assert cost > 0
    req = client.requests[0]
    assert req["tool_choice"] == {"type": "tool", "name": "match_names"}
    item = req["tools"][0]["input_schema"]["properties"]["matches"]["items"]["properties"]
    assert item["dwg_name"]["enum"] == ["KIOSK", "DB-A", ""]          # the model can only choose these
    assert item["pdf_name"]["enum"] == ["KIOSK busbar", "DB-9"]
    assert item["verdict"]["enum"] == ["same", "different", "unsure"]


def test_a_same_verdict_without_a_dwg_name_is_not_trusted():
    client = _FakeClient([{"pdf_name": "X", "dwg_name": "", "verdict": "same", "reason": "?"}])
    found, _ = match_names("equipment", ["A"], ["X"], client=client)
    assert found == {"X": ("", "unsure", "?")}


def test_the_matcher_adds_up_what_it_cost_and_survives_an_api_failure():
    class Broken:
        messages = None

        def __init__(self):
            self.messages = self

        def create(self, **kw):
            raise RuntimeError("network down")

    costs = []
    matcher = make_name_matcher(client=Broken(), on_cost=costs.append)
    assert matcher("equipment", ["A"], ["B"]) == {}          # combining carries on with exact matches
    ok = make_name_matcher(client=_FakeClient([
        {"pdf_name": "B", "dwg_name": "A", "verdict": "same", "reason": "r"}]), on_cost=costs.append)
    assert ok("equipment", ["A"], ["B"]) == {"B": ("A", "same", "r")}
    assert len(costs) == 1 and costs[0] > 0
