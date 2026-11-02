"""Human-like AI strategies (facile / normal / difficile).

The brain only sees what a human sees: prices history, its own account and the news feed.
`step(now, view)` is polled often; it returns at most one order dict when it "decides" to act.
"""
import random

ASSETS = ("BTCX", "CORPO", "OR")
LEVELS = ("facile", "normal", "difficile")
# Typical per-tick volatility used to normalise momentum (monthly sigma / sqrt(10))
TICK_SIGMA = {"BTCX": 0.079, "CORPO": 0.022, "OR": 0.0095}

PROFILE = {
    "facile": {"interval": (12.0, 22.0), "news_delay": (15.0, 25.0), "news_follow": 0.35},
    "normal": {"interval": (7.0, 12.0), "news_delay": (5.0, 9.0), "news_follow": 0.85},
    "difficile": {"interval": (3.0, 6.0), "news_delay": (0.8, 2.0), "news_follow": 0.97},
}


class AIBrain:
    def __init__(self, level="normal", seed=None):
        if level not in LEVELS:
            raise ValueError(f"niveau inconnu: {level}")
        self.level = level
        self.rng = random.Random(seed)
        self.p = PROFILE[level]
        self.next_decision = None
        self.pending_news = []  # (react_at, event)
        self.seen_news = set()

    def reset(self, now):
        self.pending_news.clear()
        self.seen_news.clear()
        self.next_decision = now + self.rng.uniform(*self.p["interval"])

    def observe_news(self, now, event):
        key = (event.get("id"), event.get("headline"))
        if key in self.seen_news:
            return
        self.seen_news.add(key)
        self.pending_news.append((now + self.rng.uniform(*self.p["news_delay"]), event))

    def step(self, now, view):
        """view: {'prices': {...}, 'history': {asset: [prices]}, 'account': {'cash', 'holdings'}}"""
        if self.next_decision is None:
            self.reset(now)
        for item in list(self.pending_news):
            if now >= item[0]:
                self.pending_news.remove(item)
                order = self._react_to_news(item[1], view)
                if order:
                    return order
        if now >= self.next_decision:
            self.next_decision = now + self.rng.uniform(*self.p["interval"])
            return getattr(self, "_decide_" + self.level)(view)
        return None

    # --- helpers -----------------------------------------------------------------
    def _order(self, side, asset, amount):
        return {"side": side, "asset": asset, "amount": round(amount, 2)}

    def _held_value(self, view, asset):
        return view["account"]["holdings"].get(asset, 0.0) * view["prices"][asset]

    def _momentum(self, view, asset, n=6):
        h = view["history"].get(asset, [])
        if len(h) < 3:
            return 0.0
        ref = h[max(0, len(h) - 1 - n)]
        return (h[-1] / ref - 1.0) / (TICK_SIGMA[asset] * max(1, min(n, len(h) - 1)) ** 0.5)

    def _sell_pct(self, view, asset, pct):
        value = self._held_value(view, asset)
        return self._order("sell", asset, value * pct) if value > 1 else None

    def _buy_pct(self, view, asset, pct):
        cash = view["account"]["cash"]
        return self._order("buy", asset, cash * pct) if cash > 1 else None

    # --- news reactions ----------------------------------------------------------
    def _react_to_news(self, event, view):
        levels = event.get("levels", {})
        if self.rng.random() > self.p["news_follow"]:
            return None
        if self.level == "facile":
            # slow and sloppy: acts on a random asset, sometimes the wrong way round
            asset = self.rng.choice(ASSETS)
            lvl = levels.get(asset, 0)
            if lvl == 0:
                return None
            side = "buy" if lvl > 0 else "sell"
            if self.rng.random() < 0.3:
                side = "sell" if side == "buy" else "buy"
            return (self._buy_pct(view, asset, 0.15) if side == "buy" else self._sell_pct(view, asset, 0.3))
        if self.level == "normal":
            major = max(ASSETS, key=lambda a: abs(levels.get(a, 0)))
            lvl = levels.get(major, 0)
            if abs(lvl) < 2:
                return None
            return self._buy_pct(view, major, 0.3) if lvl > 0 else self._sell_pct(view, major, 0.6)
        # difficile: sell losers first, then pour cash into the best expected winner
        for a in sorted(ASSETS, key=lambda x: levels.get(x, 0)):
            if levels.get(a, 0) < 0:
                order = self._sell_pct(view, a, 1.0)
                if order and order["amount"] > 200:
                    return order
        best = max(ASSETS, key=lambda x: levels.get(x, 0) * (1.0 if x != "OR" else 1.6))
        if levels.get(best, 0) > 0:
            order = self._buy_pct(view, best, 0.6 if levels[best] >= 2 else 0.4)
            if order and order["amount"] > 200:
                return order
        return None

    # --- periodic decisions ------------------------------------------------------
    def _decide_facile(self, view):
        asset = self.rng.choice(ASSETS)
        if self.rng.random() < 0.55:
            return self._buy_pct(view, asset, self.rng.uniform(0.1, 0.4))
        return self._sell_pct(view, asset, self.rng.uniform(0.2, 0.8))

    def _decide_normal(self, view):
        moms = {a: self._momentum(view, a) for a in ASSETS}
        best = max(ASSETS, key=lambda a: moms[a])
        worst = min(ASSETS, key=lambda a: moms[a])
        if moms[worst] < -1.0 and self._held_value(view, worst) > 100:
            return self._sell_pct(view, worst, 0.7)
        if moms[best] > 0.8:
            return self._buy_pct(view, best, 0.35)
        return None

    def _decide_difficile(self, view):
        if self.rng.random() < 0.1:
            return None  # occasional hesitation
        moms = {a: self._momentum(view, a, 4) for a in ASSETS}
        # exploit volatility: sell sharp spikes, buy sharp dips on volatile assets
        for a in ("BTCX", "CORPO"):
            h = view["history"].get(a, [])
            if len(h) < 8:
                continue
            avg = sum(h[-8:]) / 8
            dev = (view["prices"][a] / avg - 1.0) / TICK_SIGMA[a]
            if dev > 2.0 and self._held_value(view, a) > 200:
                return self._sell_pct(view, a, 0.8)
            if dev < -2.0:
                order = self._buy_pct(view, a, 0.4)
                if order and order["amount"] > 200:
                    return order
        # otherwise keep a sensible mix: park idle cash in gold, ride strong trends
        cash = view["account"]["cash"]
        total = cash + sum(self._held_value(view, a) for a in ASSETS)
        best = max(ASSETS, key=lambda a: moms[a])
        if moms[best] > 1.2 and cash > 0.15 * total:
            return self._buy_pct(view, best, 0.4)
        if cash > 0.5 * total and self._held_value(view, "OR") < 0.2 * total:
            return self._order("buy", "OR", cash * 0.25)
        return None
