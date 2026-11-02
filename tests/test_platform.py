"""Integration: full in-process Ingescape platform, accelerated match."""
import time

import ingescape as igs
import pytest

from agents.common import STR, add_inputs, add_outputs, listen, make_agent, parse
from agents.wiring import Platform


class FakeUI:
    def __init__(self):
        self.agent = make_agent("UI")
        add_inputs(self.agent, market=STR, view_p1=STR, view_p2=STR, news_event=STR)
        add_outputs(self.agent, key_p1=STR, key_p2=STR, command=STR)
        self.market, self.views, self.news = None, {}, []
        listen(self.agent, "market", lambda v: setattr(self, "market", parse(v)))
        listen(self.agent, "view_p1", lambda v: self.views.__setitem__(1, parse(v)))
        listen(self.agent, "view_p2", lambda v: self.views.__setitem__(2, parse(v)))
        listen(self.agent, "news_event", lambda v: self.news.append(parse(v)))

    def cmd(self, c):
        self.agent.output_set_string("command", c)

    def key(self, p, k):
        self.agent.output_set_string(f"key_p{p}", k)


def wait_for(cond, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture(scope="module")
def platform():
    # Ingescape is process-global: start it once for the whole module
    ui = FakeUI()
    p = Platform(ui_agent=ui, speed=120.0, seed=7)  # 360 s match -> 3 s
    p.start(igs.net_devices_list()[-1], 5681)
    time.sleep(2.0)
    yield p, ui
    p.stop()


def test_full_match_1v1_with_trades_and_rematch(platform):
    p, ui = platform
    ui.cmd("start:1v1")
    assert wait_for(lambda: ui.market and ui.market["state"] == "running")
    assert wait_for(lambda: ui.news)  # month-0 news published immediately
    ui.key(1, "e")  # P1 buys the selected asset (BTCX) with the default 1000 EUR
    ui.key(2, "d")
    assert wait_for(lambda: ui.views.get(1) and ui.views[1]["account"]["history"])
    assert ui.views[1]["account"]["cash"] == pytest.approx(9000)
    assert wait_for(lambda: ui.market["state"] == "finished", 30)
    m = ui.market
    assert m["tick"] == 120 and "result" in m
    assert len([e for e in ui.news if e["match_id"] == m["match_id"]]) == 12
    assert m["result"]["winner"] in (0, 1, 2)
    # shared market, independent impact: both bought the same asset at ~same price level
    first = m["match_id"]
    ui.cmd("rematch")
    assert wait_for(lambda: ui.market["match_id"] == first + 1 and ui.market["state"] == "running")
    assert wait_for(lambda: ui.views[1]["account"]["cash"] == pytest.approx(10000))


def test_ai_match_trades_and_finishes(platform):
    p, ui = platform
    ui.cmd("menu")
    assert wait_for(lambda: ui.market and ui.market["state"] == "menu")
    ui.cmd("start:ai:difficile")
    assert wait_for(lambda: ui.market and ui.market["mode"] == "ai")
    assert wait_for(lambda: ui.market["state"] == "finished", 30)
    assert ui.market["level"] == "difficile"
    assert ui.views[2]["account"]["history"], "AI should have traded at least once"
    assert ui.views[1]["account"]["history"] == []
