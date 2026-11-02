"""Bourse agent: owns prices, ticks the market, executes orders, applies news."""
import threading
import time

from engine.ledger import FEES
from engine.price_model import ASSETS, TICKS_PER_MONTH
from engine.session import TOTAL_TICKS, MarketSession, clock_label

from .common import INT, STR, add_inputs, add_outputs, emit, listen, make_agent, parse

MATCH_SECONDS = 360.0  # 6 real minutes for 12 simulated months
EVENT_TIMEOUT = 2.0


class Bourse:
    def __init__(self, speed=1.0, seed=None):
        self.agent = make_agent("Bourse")
        add_inputs(self.agent, command=STR, event=STR, order_p1=STR, order_p2=STR)
        add_outputs(self.agent, market=STR, account_p1=STR, account_p2=STR, month_start=INT, new_game=STR)
        self.tick_seconds = MATCH_SECONDS / TOTAL_TICKS / speed
        self.base_seed = seed
        self.lock = threading.RLock()
        self.event_ready = threading.Event()
        self.pending_event = None
        self.session = None
        self.state = "menu"  # menu | running | paused | finished
        self.mode, self.level = "1v1", None
        self.match_id = 0
        self.run_elapsed = 0.0
        self.messages = {1: "", 2: ""}
        self.stop_flag = threading.Event()
        listen(self.agent, "command", self.on_command)
        listen(self.agent, "event", self.on_event)
        listen(self.agent, "order_p1", lambda v: self.on_order(1, v))
        listen(self.agent, "order_p2", lambda v: self.on_order(2, v))
        self.thread = threading.Thread(target=self._clock, name="bourse-clock", daemon=True)

    def start(self):
        self.thread.start()
        self._publish_all()

    def stop(self):
        self.stop_flag.set()

    # --- inputs ----------------------------------------------------------------
    def on_command(self, value):
        parts = str(value).split(":")
        with self.lock:
            cmd = parts[0]
            if cmd == "start" and self.state in ("menu", "finished"):
                self.mode = parts[1] if len(parts) > 1 else "1v1"
                self.level = parts[2] if len(parts) > 2 else None
                self._new_match()
            elif cmd == "rematch" and self.state == "finished":
                self._new_match()
            elif cmd == "toggle_pause" and self.state in ("running", "paused"):
                self.state = "paused" if self.state == "running" else "running"
                self._publish_all()
            elif cmd == "menu" and self.state != "menu":
                self.state = "menu"
                self._publish_all()

    def on_event(self, value):
        event = parse(value)
        if event is None:
            return
        if event.get("match_id") == self.match_id:
            self.pending_event = event
            self.event_ready.set()

    def on_order(self, player, value):
        order = parse(value)
        if not order:
            return
        with self.lock:
            if self.state != "running" or self.session is None:
                self.messages[player] = "Marché fermé"
            else:
                ok, msg, rec = self.session.order(player, order.get("side"), order.get("asset"), float(order.get("amount", 0)))
                self.messages[player] = self._format_msg(ok, msg, rec)
            self._publish_account(player)

    @staticmethod
    def _format_msg(ok, msg, rec):
        if not ok:
            return msg
        verb = "Achat" if rec["side"] == "buy" else "Vente"
        return f"{verb} {rec['asset']} : {rec['qty']:.4f} @ {rec['price']:.2f} € (frais {rec['fee']:.2f} €)"

    # --- match lifecycle --------------------------------------------------------
    def _new_match(self):
        self.match_id += 1
        seed = None if self.base_seed is None else self.base_seed + self.match_id
        self.session = MarketSession(seed)
        self.messages = {1: "", 2: ""}
        self.run_elapsed = 0.0
        emit(self.agent, "new_game", {"match_id": self.match_id, "seed": seed})
        self.state = "running"
        self._month_event()
        self._publish_all()

    def _month_event(self):
        """Ask the Journal for this month's news and apply it immediately."""
        self.event_ready.clear()
        self.pending_event = None
        month = self.session.tick // TICKS_PER_MONTH
        self.agent.output_set_int("month_start", month)
        # on_event never takes self.lock, so waiting here cannot deadlock the Journal's reply
        event = self.pending_event if self.event_ready.wait(EVENT_TIMEOUT) else None
        if event and event.get("month") == month:
            self.session.apply_event(event)

    # --- clock -------------------------------------------------------------------
    def _clock(self):
        last = time.monotonic()
        while not self.stop_flag.is_set():
            time.sleep(0.02)
            now = time.monotonic()
            dt, last = now - last, now
            with self.lock:
                if self.state != "running" or self.session is None:
                    continue
                self.run_elapsed += dt
                while self.state == "running" and not self.session.finished and \
                        self.run_elapsed >= (self.session.tick + 1) * self.tick_seconds:
                    self.session.advance()
                    if self.session.event_due():
                        self._month_event()
                    if self.session.finished:
                        self.state = "finished"
                    self._publish_all()

    # --- outputs -----------------------------------------------------------------
    def _publish_all(self):
        emit(self.agent, "market", self._market_view())
        for p in (1, 2):
            self._publish_account(p)

    def _publish_account(self, player):
        if self.session is None:
            return
        snap = self.session.accounts[player].snapshot(self.session.prices)
        snap.update(player=player, message=self.messages[player], match_id=self.match_id)
        emit(self.agent, f"account_p{player}", snap)

    def _market_view(self):
        s = self.session
        view = {"state": self.state, "mode": self.mode, "level": self.level, "match_id": self.match_id,
                "fees": FEES, "assets": list(ASSETS), "total_ticks": TOTAL_TICKS}
        if s:
            view.update(tick=s.tick, date=clock_label(s.tick), prices=s.prices, history=s.history,
                        time_left=(TOTAL_TICKS - s.tick) * self.tick_seconds)
            if s.finished:
                view["result"] = s.result()
        return view
