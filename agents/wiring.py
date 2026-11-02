"""Builds the in-process platform of agents and wires their IOP mappings."""
import ingescape as igs

from .ai import AIPlayer
from .bourse import Bourse
from .common import map_io
from .journal import Journal
from .player import Player


class Platform:
    def __init__(self, ui_agent=None, speed=1.0, seed=None):
        self.bourse = Bourse(speed=speed, seed=seed)
        self.journal = Journal()
        self.p1 = Player(1)
        self.p2 = Player(2)
        self.ai = AIPlayer(speed=speed, seed=seed)
        self.ui = ui_agent
        self._wire()

    def _wire(self):
        b, j, p1, p2, ai = (x.agent for x in (self.bourse, self.journal, self.p1, self.p2, self.ai))
        map_io(j, "new_game", b, "new_game")
        map_io(j, "month_start", b, "month_start")
        map_io(b, "event", j, "event")
        map_io(b, "order_p1", p1, "order")
        map_io(b, "order_p2", p2, "order")
        map_io(b, "order_p2", ai, "order")
        map_io(p1, "account", b, "account_p1")
        map_io(p2, "account", b, "account_p2")
        map_io(ai, "account", b, "account_p2")
        map_io(ai, "market", b, "market")
        map_io(ai, "event", j, "event")
        if self.ui:
            u = self.ui.agent
            map_io(b, "command", u, "command")
            map_io(p1, "key_event", u, "key_p1")
            map_io(p2, "key_event", u, "key_p2")
            map_io(u, "market", b, "market")
            map_io(u, "view_p1", p1, "view")
            map_io(u, "view_p2", p2, "view")
            map_io(u, "news_event", j, "event")

    def start(self, device=None, port=5670):
        device = device or default_device()
        igs.start_with_device(device, port)
        self.bourse.start()
        self.ai.start()

    def stop(self):
        self.bourse.stop()
        self.ai.stop()
        igs.stop()


def default_device():
    devices = igs.net_devices_list()
    return next((d for d in devices if "loopback" not in d.lower()), devices[0])
