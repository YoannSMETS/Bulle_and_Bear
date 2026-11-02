"""AI agent: same IOP contract as a human player (order out, account/market/news in)."""
import threading
import time

from engine.ai_strategy import AIBrain

from .common import STR, add_inputs, add_outputs, emit, listen, make_agent, parse


class AIPlayer:
    def __init__(self, speed=1.0, seed=None):
        self.agent = make_agent("AI")
        add_inputs(self.agent, market=STR, account=STR, event=STR)
        add_outputs(self.agent, order=STR)
        self.speed = speed
        self.seed = seed
        self.lock = threading.Lock()
        self.market = None
        self.account = None
        self.brain = None
        self.match_id = None
        self.early_news = []
        self.vclock = 0.0  # virtual seconds, only advances while the match runs
        self.stop_flag = threading.Event()
        listen(self.agent, "market", self.on_market)
        listen(self.agent, "account", self.on_account)
        listen(self.agent, "event", self.on_event)
        self.thread = threading.Thread(target=self._loop, name="ai-loop", daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_flag.set()

    def on_market(self, value):
        market = parse(value)
        if not market:
            return
        with self.lock:
            self.market = market
            if market.get("mode") == "ai" and market.get("match_id") != self.match_id:
                self.match_id = market.get("match_id")
                self.vclock = 0.0
                self.brain = AIBrain(market.get("level") or "normal", self.seed)
                self.brain.reset(self.vclock)
                for ev in self.early_news:
                    if ev.get("match_id") == self.match_id:
                        self.brain.observe_news(self.vclock, ev)
                self.early_news.clear()

    def on_account(self, value):
        account = parse(value)
        if account:
            with self.lock:
                self.account = account

    def on_event(self, value):
        event = parse(value)
        with self.lock:
            if not event:
                return
            if self.brain and event.get("match_id") == self.match_id:
                self.brain.observe_news(self.vclock, event)
            else:
                self.early_news.append(event)  # the match announcement may arrive after the first headline

    def _loop(self):
        last = time.monotonic()
        while not self.stop_flag.is_set():
            time.sleep(0.1)
            now = time.monotonic()
            dt, last = now - last, now
            order = None
            with self.lock:
                m = self.market
                if not (self.brain and m and m.get("mode") == "ai" and m.get("state") == "running" and self.account):
                    continue
                self.vclock += dt * self.speed
                view = {"prices": m["prices"], "history": m["history"], "account": self.account}
                order = self.brain.step(self.vclock, view)
            if order:
                emit(self.agent, "order", order)
