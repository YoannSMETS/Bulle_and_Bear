"""Match state machine (no I/O): prices, accounts, tick schedule, winner."""
from .ledger import Account, winner
from .price_model import ASSETS, MONTHS, TICKS_PER_MONTH, PriceModel

TOTAL_TICKS = MONTHS * TICKS_PER_MONTH
MONTH_NAMES = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août",
               "Septembre", "Octobre", "Novembre", "Décembre"]
YEAR = 2026


def clock_label(tick):
    m = min(MONTHS - 1, tick // TICKS_PER_MONTH)
    return f"{MONTH_NAMES[m]} {YEAR}"


class MarketSession:
    def __init__(self, seed=None):
        self.seed = seed
        self.model = PriceModel(seed)
        self.tick = 0
        self.accounts = {1: Account(), 2: Account()}
        self.history = {a: [self.model.prices[a]] for a in ASSETS}
        self.news = []

    @property
    def prices(self):
        return dict(self.model.prices)

    @property
    def finished(self):
        return self.tick >= TOTAL_TICKS

    def event_due(self):
        """True when a news item must be applied at the current tick."""
        return self.tick % TICKS_PER_MONTH == 0 and self.tick < TOTAL_TICKS

    def apply_event(self, event):
        self.model.apply_event(event["levels"])
        self.news.append({**event, "month": self.tick // TICKS_PER_MONTH, "date": clock_label(self.tick)})
        for a in ASSETS:  # replace the tick's last point so the jump shows on the chart
            self.history[a][-1] = self.model.prices[a]

    def advance(self):
        """Move one tick forward (price step). Events are applied afterwards by the caller."""
        if self.finished:
            return
        self.model.step()
        self.tick += 1
        for a in ASSETS:
            self.history[a].append(self.model.prices[a])

    def order(self, player, side, asset, amount):
        if self.finished:
            return False, "Partie terminée", None
        return self.accounts[player].trade(side, asset, amount, self.prices, stamp=clock_label(self.tick))

    def result(self):
        w1 = self.accounts[1].wealth(self.prices)
        w2 = self.accounts[2].wealth(self.prices)
        return {"winner": winner(w1, w2), "wealth1": w1, "wealth2": w2}
