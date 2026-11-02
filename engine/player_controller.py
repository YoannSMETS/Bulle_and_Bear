"""Keyboard controller for one human player (pure logic, no I/O)."""
from .price_model import ASSETS

# Top letter row of an AZERTY keyboard for P1, home row for P2.
KEYMAPS = {
    1: {"left": "a", "right": "z", "buy": "e", "sell": "r", "focus": "t", "edit": "y", "max": "u"},
    2: {"left": "q", "right": "s", "buy": "d", "sell": "f", "focus": "g", "edit": "h", "max": "j"},
}
MAX_DIGITS = 7
BIG = 1e12  # "all in": clamped by the ledger to cash / holdings


class PlayerController:
    def __init__(self, player_id):
        self.pid = player_id
        self.keys = KEYMAPS[player_id]
        self.reset()

    def reset(self):
        self.selected = 0
        self.focus = "marche"  # or "portefeuille"
        self.editing = False
        self.buffer = "1000"
        self.use_max = False
        self.message = ""

    @property
    def amount(self):
        return BIG if self.use_max else float(self.buffer or 0)

    def handle(self, key):
        """Returns an order dict {'side','asset','amount'} or None."""
        k = self.keys
        if key.startswith("digit:"):
            if self.editing:
                if self.use_max:
                    self.use_max, self.buffer = False, ""
                if self.buffer == "0":
                    self.buffer = ""
                if len(self.buffer) < MAX_DIGITS:
                    self.buffer += key[6:]
            return None
        if key == "backspace":
            if self.editing and not self.use_max:
                self.buffer = self.buffer[:-1]
            return None
        if key == k["edit"]:
            self.editing = not self.editing
            if self.editing:
                self.use_max, self.buffer = False, ""
            elif not self.buffer:
                self.buffer = "0"
            return None
        if key == k["max"]:
            self.use_max, self.editing = True, False
            return None
        if key == k["focus"]:
            self.focus = "portefeuille" if self.focus == "marche" else "marche"
            return None
        if key == k["left"]:
            self.selected = (self.selected - 1) % len(ASSETS)
        elif key == k["right"]:
            self.selected = (self.selected + 1) % len(ASSETS)
        elif key in (k["buy"], k["sell"]) and self.focus == "marche":
            self.editing = False
            if self.amount <= 0:
                self.message = "Saisissez un montant"
                return None
            return {"side": "buy" if key == k["buy"] else "sell", "asset": ASSETS[self.selected], "amount": self.amount}
        return None

    def view(self):
        return {
            "selected": ASSETS[self.selected],
            "focus": self.focus,
            "editing": self.editing,
            "amount": "MAX" if self.use_max else (self.buffer or "0"),
            "message": self.message,
        }
