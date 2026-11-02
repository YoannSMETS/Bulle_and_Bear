"""Journal agent: draws one humorous news event per simulated month."""
import threading

from engine.events import draw_events
from engine.price_model import MONTHS, TICKS_PER_MONTH
from engine.session import clock_label

from .common import INT, STR, add_inputs, add_outputs, emit, listen, make_agent, parse


class Journal:
    def __init__(self):
        self.agent = make_agent("Journal")
        add_inputs(self.agent, new_game=STR, month_start=INT)
        add_outputs(self.agent, event=STR)
        self.lock = threading.Lock()
        self.match_id = 0
        self.schedule = []
        listen(self.agent, "new_game", self.on_new_game)
        listen(self.agent, "month_start", self.on_month)

    def on_new_game(self, value):
        data = parse(value) or {}
        with self.lock:
            self.match_id = data.get("match_id", 0)
            self.schedule = draw_events(MONTHS, data.get("seed"))

    def on_month(self, month):
        with self.lock:
            if not 0 <= month < len(self.schedule):
                return
            event = {**self.schedule[month], "month": month, "match_id": self.match_id,
                     "date": clock_label(month * TICKS_PER_MONTH)}
        emit(self.agent, "event", event)
