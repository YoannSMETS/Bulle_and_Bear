import math

import pytest

from engine.ai_strategy import AIBrain
from engine.events import EVENT_POOL, draw_events
from engine.ledger import FEES, Account, winner
from engine.player_controller import PlayerController
from engine.price_model import ASSETS, PriceModel
from engine.session import TOTAL_TICKS, MarketSession


def test_volatility_ranking():
    """V2: BTCX > CORPO > OR over several runs."""
    vols = {a: [] for a in ASSETS}
    for seed in range(20):
        m = PriceModel(seed)
        series = {a: [m.prices[a]] for a in ASSETS}
        for _ in range(TOTAL_TICKS):
            p = m.step()
            for a in ASSETS:
                series[a].append(p[a])
        for a in ASSETS:
            r = [math.log(b / a_) for a_, b in zip(series[a], series[a][1:])]
            mean = sum(r) / len(r)
            vols[a].append(math.sqrt(sum((x - mean) ** 2 for x in r) / len(r)))
    avg = {a: sum(v) / len(v) for a, v in vols.items()}
    assert avg["BTCX"] > avg["CORPO"] > avg["OR"]


def test_gold_is_safe_haven_on_crisis():
    m = PriceModel(1)
    before = dict(m.prices)
    after = m.apply_event({"BTCX": -2, "CORPO": -2, "OR": 2})
    assert after["BTCX"] < before["BTCX"] and after["CORPO"] < before["CORPO"] and after["OR"] > before["OR"]


def test_buy_fee_and_quantity():
    """V3: fee deducted per asset type; crypto > stock > gold."""
    assert FEES["BTCX"] > FEES["CORPO"] > FEES["OR"]
    prices = {"BTCX": 100.0, "CORPO": 50.0, "OR": 20.0}
    for asset, rate in FEES.items():
        acc = Account()
        ok, _, rec = acc.trade("buy", asset, 1000, prices)
        assert ok and rec["fee"] == pytest.approx(1000 * rate)
        assert acc.cash == pytest.approx(9000)
        assert acc.holdings[asset] == pytest.approx(1000 * (1 - rate) / prices[asset])


def test_sell_fee_and_clamping():
    prices = {"BTCX": 100.0, "CORPO": 50.0, "OR": 20.0}
    acc = Account()
    acc.trade("buy", "OR", 1000, prices)
    ok, _, rec = acc.trade("sell", "OR", 1e9, prices)  # clamped to holdings value
    assert ok and acc.holdings["OR"] == 0
    assert acc.cash == pytest.approx(10000 - 1000 * FEES["OR"] - rec["amount"] * FEES["OR"])
    assert not acc.trade("sell", "OR", 10, prices)[0]
    assert not acc.trade("buy", "BTCX", 0, prices)[0]


def test_buy_clamped_to_cash_and_fractional():
    prices = {"BTCX": 40000.0, "CORPO": 50.0, "OR": 20.0}
    acc = Account()
    ok, _, _ = acc.trade("buy", "BTCX", 50_000, prices)
    assert ok and acc.cash == 0 and 0 < acc.holdings["BTCX"] < 1


def test_winner_and_tie():
    assert winner(10, 5) == 1 and winner(5, 10) == 2 and winner(7.001, 7.004) == 0


def test_events_one_per_month_distinct():
    events = draw_events(12, seed=3)
    assert len(events) == 12 and len({e["id"] for e in events}) == 12
    assert len(EVENT_POOL) >= 20
    assert all(set(e["levels"]) == set(ASSETS) for e in events)


def test_session_event_visible_on_tick_and_ends():
    s = MarketSession(5)
    due = 0
    while True:
        if s.event_due():
            due += 1
            before = s.prices
            s.apply_event({"id": 0, "headline": "x", "levels": {"BTCX": 3, "CORPO": 0, "OR": 0}})
            assert s.prices["BTCX"] > before["BTCX"] and s.history["BTCX"][-1] == s.prices["BTCX"]
        if s.finished:
            break
        s.advance()
    assert due == 12 and s.tick == TOTAL_TICKS and len(s.history["OR"]) == TOTAL_TICKS + 1
    assert s.result()["winner"] == 0  # nobody traded


def test_player_controller_flow():
    p = PlayerController(1)
    assert p.handle("z") is None and p.selected == 1
    assert p.handle("e") == {"side": "buy", "asset": "CORPO", "amount": 1000.0}
    p.handle("y")
    for d in "250":
        p.handle(f"digit:{d}")
    p.handle("y")
    assert p.handle("r") == {"side": "sell", "asset": "CORPO", "amount": 250.0}
    p.handle("u")
    assert p.handle("e")["amount"] > 1e9
    p.handle("t")
    assert p.handle("e") is None  # portfolio focus disables trading
    p2 = PlayerController(2)
    assert p2.handle("e") is None and p2.handle("d")["side"] == "buy"  # P1 keys don't act on P2


def _view(history_scale=1.0, cash=10000.0, holdings=None):
    prices = {"BTCX": 100.0, "CORPO": 50.0, "OR": 20.0}
    hist = {a: [p * (1 + 0.01 * i * history_scale) for i in range(10)] for a, p in prices.items()}
    prices = {a: h[-1] for a, h in hist.items()}
    return {"prices": prices, "history": hist,
            "account": {"cash": cash, "holdings": holdings or {a: 0.0 for a in ASSETS}}}


def test_ai_levels_react_with_expected_delay():
    event = {"id": 1, "headline": "h", "levels": {"BTCX": 3, "CORPO": 0, "OR": 0}}
    delays = {}
    for level in ("facile", "normal", "difficile"):
        brain = AIBrain(level, seed=1)
        brain.reset(0)
        brain.next_decision = 1e9  # isolate the news reaction
        brain.rng.random = lambda: 0.0  # always follow the news
        brain.observe_news(0, event)
        t = 0.0
        while brain.step(t, _view()) is None and t < 60:
            t += 0.1
        delays[level] = t
    assert delays["difficile"] < delays["normal"] < delays["facile"]


def test_ai_difficile_sells_losers_and_buys_winner_on_news():
    brain = AIBrain("difficile", seed=2)
    brain.reset(0)
    brain.next_decision = 1e9
    brain.rng.random = lambda: 0.5
    brain.observe_news(0, {"id": 1, "headline": "h", "levels": {"BTCX": -3, "CORPO": 0, "OR": 2}})
    view = _view(holdings={"BTCX": 20.0, "CORPO": 0.0, "OR": 0.0})
    order = brain.step(5, view)
    assert order and order["side"] == "sell" and order["asset"] == "BTCX"
    view["account"]["holdings"]["BTCX"] = 0.0
    assert brain.step(5, view) is None  # reaction consumed
    brain.observe_news(5, {"id": 2, "headline": "g", "levels": {"BTCX": 0, "CORPO": 0, "OR": 2}})
    order = brain.step(10, view)
    assert order and order["side"] == "buy" and order["asset"] == "OR"


def test_ai_normal_follows_momentum_and_facile_is_irregular():
    brain = AIBrain("normal", seed=3)
    brain.reset(0)
    order = brain.step(100, _view(history_scale=3.0))
    assert order and order["side"] == "buy"
    easy = AIBrain("facile", seed=4)
    easy.reset(0)
    assert easy.step(100, _view()) is not None
    with pytest.raises(ValueError):
        AIBrain("expert")
