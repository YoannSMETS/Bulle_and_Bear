"""Stochastic price model: correlated log-returns, drift, mean reversion, event shocks."""
import math
import random

ASSETS = ("BTCX", "CORPO", "OR")
START_PRICES = {"BTCX": 100.0, "CORPO": 50.0, "OR": 20.0}
# Monthly volatility (std dev of log-return) and monthly drift
MONTHLY_SIGMA = {"BTCX": 0.25, "CORPO": 0.07, "OR": 0.03}
MONTHLY_DRIFT = {"BTCX": 0.010, "CORPO": 0.007, "OR": 0.003}
MEAN_REVERSION = 0.02  # per tick pull toward the long-run anchor
TICKS_PER_MONTH = 10
MONTHS = 12
# Effect of one event "arrow" as an immediate jump (log-return), per asset
EVENT_SCALE = {"BTCX": 0.12, "CORPO": 0.035, "OR": 0.015}
EVENT_DRIFT_MONTHS = 3
# Correlation matrix, order = ASSETS (gold is a safe haven: negative vs stock/crypto)
CORR = (
    (1.0, 0.45, -0.15),
    (0.45, 1.0, -0.35),
    (-0.15, -0.35, 1.0),
)


def cholesky(m):
    n = len(m)
    low = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(low[i][k] * low[j][k] for k in range(j))
            low[i][j] = math.sqrt(m[i][i] - s) if i == j else (m[i][j] - s) / low[j][j]
    return low


_CHOL = cholesky(CORR)


class PriceModel:
    def __init__(self, seed=None, start=None):
        self.rng = random.Random(seed)
        self.prices = dict(start or START_PRICES)
        self.anchor = {a: math.log(p) for a, p in self.prices.items()}
        self.tick_index = 0
        self.effects = []

    def apply_event(self, levels):
        """Immediate jump + decaying drift/vol boost for the following months."""
        for a in ASSETS:
            lvl = levels.get(a, 0)
            if lvl:
                self.prices[a] *= math.exp(lvl * EVENT_SCALE[a])
                self.anchor[a] += lvl * EVENT_SCALE[a] * 0.6
        self.effects.append({"levels": dict(levels), "ticks_left": EVENT_DRIFT_MONTHS * TICKS_PER_MONTH})
        return dict(self.prices)

    def _event_mods(self, asset):
        drift, vol = 0.0, 1.0
        for e in self.effects:
            lvl = e["levels"].get(asset, 0)
            if not lvl:
                continue
            decay = e["ticks_left"] / (EVENT_DRIFT_MONTHS * TICKS_PER_MONTH)
            drift += lvl * EVENT_SCALE[asset] * 0.25 / TICKS_PER_MONTH * decay
            vol += 0.15 * abs(lvl) * decay
        return drift, vol

    def step(self):
        z = [self.rng.gauss(0, 1) for _ in ASSETS]
        corr_z = [sum(_CHOL[i][k] * z[k] for k in range(i + 1)) for i in range(len(ASSETS))]
        for i, a in enumerate(ASSETS):
            ev_drift, ev_vol = self._event_mods(a)
            sigma = MONTHLY_SIGMA[a] / math.sqrt(TICKS_PER_MONTH) * ev_vol
            drift = MONTHLY_DRIFT[a] / TICKS_PER_MONTH + ev_drift
            self.anchor[a] += MONTHLY_DRIFT[a] / TICKS_PER_MONTH
            logp = math.log(self.prices[a])
            reversion = MEAN_REVERSION * (self.anchor[a] - logp)
            logp += drift - 0.5 * sigma * sigma + reversion + sigma * corr_z[i]
            self.prices[a] = math.exp(logp)
        for e in self.effects:
            e["ticks_left"] -= 1
        self.effects = [e for e in self.effects if e["ticks_left"] > 0]
        self.tick_index += 1
        return dict(self.prices)
