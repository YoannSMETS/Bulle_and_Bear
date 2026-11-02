"""Portfolio ledger: market orders in euros, per-asset fees, fractional quantities."""
from .price_model import ASSETS

FEES = {"BTCX": 0.015, "CORPO": 0.0075, "OR": 0.0025}
START_CASH = 10_000.0
EPS = 1e-9


class Account:
    def __init__(self, cash=START_CASH):
        self.cash = cash
        self.holdings = {a: 0.0 for a in ASSETS}
        self.history = []

    def wealth(self, prices):
        return self.cash + sum(self.holdings[a] * prices[a] for a in ASSETS)

    def trade(self, side, asset, amount, prices, stamp=""):
        """Execute a market order of `amount` euros (gross, fee included).

        Buy:  cash decreases by amount; fee = amount*rate; qty = (amount-fee)/price.
        Sell: amount is the gross value sold; cash += amount-fee; qty = amount/price.
        The amount is clamped to what the player can afford / hold.
        Returns (ok, message, record).
        """
        if asset not in ASSETS or side not in ("buy", "sell"):
            return False, "Ordre invalide", None
        if not amount or amount <= 0:
            return False, "Montant invalide", None
        price, rate = prices[asset], FEES[asset]
        if side == "buy":
            amount = min(amount, self.cash)
            if amount < 0.01:
                return False, "Fonds insuffisants", None
            fee = amount * rate
            qty = (amount - fee) / price
            self.cash -= amount
            self.holdings[asset] += qty
        else:
            amount = min(amount, self.holdings[asset] * price)
            if amount < 0.01:
                return False, "Rien à vendre", None
            fee = amount * rate
            qty = amount / price
            self.holdings[asset] = max(0.0, self.holdings[asset] - qty)
            if self.holdings[asset] < EPS:
                self.holdings[asset] = 0.0
            self.cash += amount - fee
        rec = {"t": stamp, "asset": asset, "side": side, "qty": qty, "price": price, "fee": fee, "amount": amount}
        self.history.append(rec)
        return True, "Ordre exécuté", rec

    def snapshot(self, prices):
        return {
            "cash": self.cash,
            "holdings": dict(self.holdings),
            "wealth": self.wealth(prices),
            "history": self.history[-10:],
        }


def winner(wealth1, wealth2):
    """0 = tie, 1 = player 1, 2 = player 2 (compared at cent precision)."""
    a, b = round(wealth1, 2), round(wealth2, 2)
    return 0 if a == b else (1 if a > b else 2)
