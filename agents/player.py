"""Human player agent: turns key events into orders and exposes its view/portfolio."""
import threading

from engine.player_controller import PlayerController

from .common import STR, add_inputs, add_outputs, emit, listen, make_agent, parse


class Player:
    def __init__(self, player_id):
        self.pid = player_id
        self.agent = make_agent(f"Player{player_id}")
        add_inputs(self.agent, key_event=STR, account=STR)
        add_outputs(self.agent, order=STR, view=STR)
        self.ctrl = PlayerController(player_id)
        self.account = None
        self.match_id = None
        self.lock = threading.Lock()
        listen(self.agent, "key_event", self.on_key)
        listen(self.agent, "account", self.on_account)

    def on_key(self, key):
        with self.lock:
            self.ctrl.message = ""
            order = self.ctrl.handle(str(key))
            view = self._view()
        if order:
            emit(self.agent, "order", order)
        emit(self.agent, "view", view)

    def on_account(self, value):
        account = parse(value)
        if not account:
            return
        with self.lock:
            if account.get("match_id") != self.match_id:
                self.match_id = account.get("match_id")
                self.ctrl.reset()
            self.account = account
            view = self._view()
        emit(self.agent, "view", view)

    def _view(self):
        view = self.ctrl.view()
        view["player"] = self.pid
        view["account"] = self.account
        if self.account and self.account.get("message"):
            view["message"] = self.account["message"]
        return view
