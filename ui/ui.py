"""UI agent: renders the split-screen game (tkinter) and forwards keyboard events to the Player agents."""
import threading
import time
import tkinter as tk

from agents.common import STR, add_inputs, add_outputs, listen, make_agent, parse
from engine.player_controller import KEYMAPS

BG, PANEL, TEXT, MUTED = "#0b1220", "#141c2f", "#e5e7eb", "#8892a6"
UP, DOWN = "#22c55e", "#ef4444"
COLORS = {"BTCX": "#f7931a", "CORPO": "#3b82f6", "OR": "#facc15"}
P_COLORS = {1: "#2dd4bf", 2: "#e879f9"}
ASSET_NAMES = {"BTCX": "Crypto", "CORPO": "Action", "OR": "Or"}
MENU = [("Humain vs Humain", "start:1v1"), ("Humain vs IA — Facile", "start:ai:facile"),
        ("Humain vs IA — Normal", "start:ai:normal"), ("Humain vs IA — Difficile", "start:ai:difficile")]
GAME_KEYS = {p: set(k.values()) for p, k in KEYMAPS.items()}
HELP = {
    1: "A ◄  Z ►  choisir  |  E Acheter  R Vendre  |  T Portefeuille  |  Y Saisir montant  U Max",
    2: "Q ◄  S ►  choisir  |  D Acheter  F Vendre  |  G Portefeuille  |  H Saisir montant  J Max",
}
try:  # crisp rendering and exact pixel sizes on scaled Windows displays
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


def eur(x):
    return f"{x:,.2f} €".replace(",", " ")


class UI:
    def __init__(self, fullscreen=True):
        self.agent = make_agent("UI")
        add_inputs(self.agent, market=STR, view_p1=STR, view_p2=STR, news_event=STR)
        add_outputs(self.agent, key_p1=STR, key_p2=STR, command=STR)
        self.lock = threading.Lock()
        self.market, self.views, self.news = None, {1: None, 2: None}, {}
        listen(self.agent, "market", lambda v: self._store("market", v))
        listen(self.agent, "view_p1", lambda v: self._store("v1", v))
        listen(self.agent, "view_p2", lambda v: self._store("v2", v))
        listen(self.agent, "news_event", self._on_news)
        self.menu_idx = 0
        self.closed = False
        self.down, self.edit_ts = set(), {1: 0.0, 2: 0.0}
        self.root = tk.Tk()
        self.root.title("Bulle & Bear")
        self.root.configure(bg=BG)
        if fullscreen:
            self.root.attributes("-fullscreen", True)
        else:
            self.root.geometry("1280x720")
        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.root.bind("<KeyPress>", self._on_key)
        self.root.bind("<KeyRelease>", lambda e: self.down.discard(e.keycode))
        self.root.bind("<FocusOut>", lambda e: self.down.clear())
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<F11>", lambda e: self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen")))

    # --- incoming data (ingescape threads) ---------------------------------------
    def _store(self, kind, value):
        data = parse(value)
        if data is None:
            return
        with self.lock:
            if kind == "market":
                self.market = data
            else:
                self.views[1 if kind == "v1" else 2] = data

    def _on_news(self, value):
        event = parse(value)
        if event:
            with self.lock:
                self.news.setdefault(event["match_id"], []).append(event)

    # --- keyboard ----------------------------------------------------------------
    def _on_key(self, e):
        keysym = e.keysym
        now = time.monotonic()
        if e.keycode in self.down:  # ignore OS auto-repeat while a key is held
            return
        self.down.add(e.keycode)
        with self.lock:
            market = self.market
        state = market["state"] if market else "menu"
        if keysym == "Escape":
            if state == "menu":
                self.close()
            else:
                self.agent.output_set_string("command", "menu")
            return
        if state == "menu":
            if keysym == "Up":
                self.menu_idx = (self.menu_idx - 1) % len(MENU)
            elif keysym == "Down":
                self.menu_idx = (self.menu_idx + 1) % len(MENU)
            elif keysym in ("Return", "space"):
                self.agent.output_set_string("command", MENU[self.menu_idx][1])
            return
        if keysym in ("Return", "space"):
            cmd = "rematch" if state == "finished" else "toggle_pause"
            self.agent.output_set_string("command", cmd)
            return
        if state != "running":
            return
        key = self._normalise(e)
        if not key:
            return
        if key.startswith("digit:") or key == "backspace":
            self._route_edit_key(key)
            return
        for p in (1, 2):
            if key in GAME_KEYS[p] and not (p == 2 and market.get("mode") == "ai"):
                if key == KEYMAPS[p]["edit"]:
                    self.edit_ts[p] = now
                self.agent.output_set_string(f"key_p{p}", key)

    @staticmethod
    def _normalise(e):
        if e.keysym == "BackSpace":
            return "backspace"
        code = e.keycode
        if 48 <= code <= 57:  # top-row digits (VK codes, independent of AZERTY shift state)
            return f"digit:{code - 48}"
        if 96 <= code <= 105:
            return f"digit:{code - 96}"
        return e.keysym.lower() if len(e.keysym) == 1 else None

    def _route_edit_key(self, key):
        with self.lock:
            editing = [p for p in (1, 2) if self.views[p] and self.views[p].get("editing")]
        if editing:
            target = max(editing, key=lambda p: self.edit_ts[p])
            self.agent.output_set_string(f"key_p{target}", key)

    # --- rendering -----------------------------------------------------------------
    def run(self):
        self._frame()
        self.root.mainloop()

    def _frame(self):
        if self.closed:
            return
        c = self.canvas
        c.delete("all")
        W, H = max(c.winfo_width(), 640), max(c.winfo_height(), 360)
        with self.lock:
            market, views = self.market, dict(self.views)
            news = list(self.news.get(market["match_id"], [])) if market else []
        if not market or market["state"] == "menu":
            self._draw_menu(W, H, market is not None)
        else:
            self._draw_game(W, H, market, views, news)
        self.root.after(33, self._frame)

    def close(self):
        self.closed = True
        self.root.destroy()

    def _t(self, x, y, text, size=14, color=TEXT, anchor="nw", bold=False, **kw):
        font = ("Segoe UI", -max(10, int(size * 1.2)), "bold" if bold else "normal")  # negative = pixels
        return self.canvas.create_text(x, y, text=text, fill=color, anchor=anchor, font=font, **kw)

    def _draw_menu(self, W, H, connected):
        s = H / 1080
        self._t(W / 2, H * 0.14, "Bulle & Bear", 72 * s, "#f7931a", "n", True)
        self._t(W / 2, H * 0.27, "Simulation boursière à deux joueurs — 6 minutes, 12 mois", 22 * s, MUTED, "n")
        if not connected:
            self._t(W / 2, H * 0.5, "Connexion aux agents…", 28 * s, MUTED, "n")
            return
        for i, (label, _) in enumerate(MENU):
            y = H * 0.4 + i * H * 0.09
            sel = i == self.menu_idx
            self.canvas.create_rectangle(W * 0.33, y, W * 0.67, y + H * 0.07, fill="#1e293b" if sel else PANEL,
                                         outline="#f7931a" if sel else "#1f2937", width=3 if sel else 1)
            self._t(W / 2, y + H * 0.035, label, 26 * s, TEXT if sel else MUTED, "center", sel)
        self._t(W / 2, H * 0.84, "↑ ↓ choisir   |   Entrée / Espace : jouer   |   Échap : quitter", 18 * s, MUTED, "n")
        self._t(W / 2, H * 0.89, "Joueur 1 : A Z E R T Y U   —   Joueur 2 : Q S D F G H J", 18 * s, MUTED, "n")

    def _draw_game(self, W, H, m, views, news):
        s = H / 1080
        c = self.canvas
        total = m["total_ticks"]
        c.create_rectangle(0, 0, W, H * 0.07, fill=PANEL, outline="")
        self._t(W * 0.015, H * 0.035, "Bulle & Bear", 26 * s, "#f7931a", "w", True)
        self._t(W / 2, H * 0.035, m.get("date", ""), 30 * s, TEXT, "center", True)
        left = m.get("time_left", 0)
        self._t(W * 0.985, H * 0.035, f"{int(left // 60)}:{int(left % 60):02d}", 26 * s, TEXT, "e", True)
        c.create_rectangle(0, H * 0.07, W * m.get("tick", 0) / total, H * 0.075, fill="#f7931a", outline="")
        pw = W * 0.36
        self._draw_player(1, 0, pw, W, H, m, views[1])
        self._draw_player(2, W - pw, pw, W, H, m, views[2])
        self._draw_center(pw, W - pw, H, m, news)
        if m["state"] == "paused":
            self._overlay(W, H, "PAUSE", "Entrée / Espace : reprendre   |   Échap : menu")
        elif m["state"] == "finished":
            self._draw_result(W, H, m, views)

    def _chart(self, x0, y0, x1, y1, data, color):
        c = self.canvas
        c.create_rectangle(x0, y0, x1, y1, fill="#0f172a", outline="#1f2937")
        if len(data) < 2:
            return
        lo, hi = min(data), max(data)
        span = (hi - lo) or 1.0
        pad = (y1 - y0) * 0.08
        pts = []
        for i, v in enumerate(data):
            pts += [x0 + (x1 - x0) * i / 120, y1 - pad - (y1 - y0 - 2 * pad) * (v - lo) / span]
        c.create_line(*pts, fill=color, width=2, smooth=False)
        c.create_text(x0 + 6, y0 + 4, text=f"{hi:.2f}", fill=MUTED, anchor="nw", font=("Segoe UI", -12))
        c.create_text(x0 + 6, y1 - 4, text=f"{lo:.2f}", fill=MUTED, anchor="sw", font=("Segoe UI", -12))

    def _draw_player(self, p, x, w, W, H, m, view):
        s = H / 1080
        c = self.canvas
        col = P_COLORS[p]
        top = H * 0.09
        c.create_rectangle(x + 8, top, x + w - 8, H * 0.985, fill=PANEL, outline=col, width=2)
        ai = p == 2 and m.get("mode") == "ai"
        title = f"IA — {m.get('level', '').capitalize()}" if ai else f"Joueur {p}"
        self._t(x + 24, top + 10 * s, title, 28 * s, col, "nw", True)
        if not view or not view.get("account"):
            return
        acc, prices = view["account"], m["prices"]
        sel = view["selected"]
        self._t(x + w - 24, top + 14 * s, f"Patrimoine {eur(acc['wealth'])}", 22 * s, TEXT, "ne", True)
        # asset tabs
        tab_w = (w - 48) / 3
        for i, a in enumerate(m["assets"]):
            tx = x + 24 + i * tab_w
            on = a == sel
            c.create_rectangle(tx, top + 60 * s, tx + tab_w - 8, top + 130 * s, fill="#1e293b" if on else "#0f172a",
                               outline=COLORS[a] if on else "#1f2937", width=3 if on else 1)
            self._t(tx + 10, top + 66 * s, f"{a}  ({ASSET_NAMES[a]})", 15 * s, COLORS[a], "nw", True)
            self._t(tx + 10, top + 92 * s, f"{prices[a]:.2f} €", 20 * s, TEXT, "nw", True)
        self._chart(x + 24, top + 145 * s, x + w - 24, top + 470 * s, m["history"][sel], COLORS[sel])
        fee = m["fees"][sel] * 100
        self._t(x + 28, top + 476 * s, f"Frais {sel} : {fee:.2f} %   |   Prix : {prices[sel]:.2f} €", 14 * s, MUTED)
        # order entry
        ey = top + 505 * s
        edit = view["editing"]
        c.create_rectangle(x + 24, ey, x + w - 24, ey + 52 * s, fill="#0f172a", outline=col if edit else "#1f2937",
                           width=3 if edit else 1)
        amount = view["amount"]
        self._t(x + 36, ey + 12 * s, f"Montant : {amount if amount == 'MAX' else amount + ' €'}" + (" ▌" if edit else ""), 20 * s,
                TEXT, "nw", True)
        msg = view.get("message") or ""
        self._t(x + 24, ey + 62 * s, msg, 13 * s, "#fbbf24", "nw", width=w - 48)
        # portfolio / history
        py = ey + 100 * s
        focus = view["focus"] == "portefeuille"
        self._t(x + 24, py, "PORTEFEUILLE" + ("  (actif)" if focus else ""), 16 * s, col if focus else MUTED, "nw", True)
        self._t(x + 24, py + 28 * s, f"Liquidités : {eur(acc['cash'])}", 17 * s, TEXT)
        for i, a in enumerate(m["assets"]):
            q = acc["holdings"][a]
            self._t(x + 24, py + (58 + 26 * i) * s, f"{a:<6} {q:>10.4f}  =  {eur(q * prices[a])}", 16 * s, COLORS[a])
        hy = py + 150 * s
        self._t(x + 24, hy, "Historique", 15 * s, MUTED, "nw", True)
        for i, h in enumerate(reversed(acc["history"][-5:])):
            side = "ACH" if h["side"] == "buy" else "VTE"
            self._t(x + 24, hy + (24 + 21 * i) * s,
                    f"{h['t'][:4]}. {side} {h['asset']} {h['qty']:.3f} @ {h['price']:.2f}  frais {h['fee']:.2f}", 13 * s,
                    UP if h["side"] == "buy" else DOWN)
        c.create_rectangle(x + 8, H * 0.935, x + w - 8, H * 0.985, fill="#0f172a", outline=col)
        self._t(x + w / 2, H * 0.96, "Contrôlé par l'IA" if ai else HELP[p], 13 * s, TEXT, "center")

    def _draw_center(self, x0, x1, H, m, news):
        s = H / 1080
        w = x1 - x0
        top = H * 0.09
        self._t((x0 + x1) / 2, top + 6 * s, "MARCHÉ", 18 * s, MUTED, "n", True)
        ch = 150 * s
        for i, a in enumerate(m["assets"]):
            y = top + 40 * s + i * (ch + 40 * s)
            hist = m["history"][a]
            chg = (hist[-1] / hist[0] - 1) * 100
            self._t(x0 + 14, y, a, 18 * s, COLORS[a], "nw", True)
            self._t(x1 - 14, y, f"{hist[-1]:.2f} €  ({chg:+.1f} %)", 16 * s, UP if chg >= 0 else DOWN, "ne", True)
            self._chart(x0 + 14, y + 28 * s, x1 - 14, y + 28 * s + ch, hist, COLORS[a])
        ny = top + 40 * s + 3 * (ch + 40 * s) + 4 * s
        self.canvas.create_rectangle(x0 + 14, ny, x1 - 14, H * 0.985, fill=PANEL, outline="#1f2937")
        self._t((x0 + x1) / 2, ny + 6 * s, "FIL D'ACTUALITÉS", 15 * s, MUTED, "n", True)
        arrows = lambda lv: ("↑" * lv if lv > 0 else "↓" * -lv) if lv else "="
        y = ny + 32 * s
        for ev in reversed(news[-4:]):
            self._t(x0 + 24, y, f"{ev.get('date', '')}", 11 * s, MUTED)
            self._t(x0 + 24, y + 16 * s, ev["headline"], 13 * s, TEXT, "nw", True, width=w - 48)
            lv = ev["levels"]
            self._t(x0 + 24, y + 54 * s, "   ".join(f"{a} {arrows(lv[a])}" for a in m["assets"]), 12 * s, MUTED)
            y += 82 * s

    def _overlay(self, W, H, title, sub):
        self.canvas.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", outline="")
        self._t(W / 2, H * 0.38, title, 72 * H / 1080, "#f7931a", "center", True)
        self._t(W / 2, H * 0.50, sub, 24 * H / 1080, TEXT, "center")

    def _draw_result(self, W, H, m, views):
        r = m["result"]
        w = r["winner"]
        ai = m.get("mode") == "ai"
        names = {1: "Joueur 1", 2: f"IA ({m.get('level')})" if ai else "Joueur 2"}
        title = "Égalité !" if w == 0 else f"Victoire : {names[w]} !"
        self.canvas.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", outline="")
        s = H / 1080
        self._t(W / 2, H * 0.3, title, 64 * s, P_COLORS.get(w, "#f7931a"), "center", True)
        self._t(W / 2, H * 0.43, f"{names[1]} : {eur(r['wealth1'])}", 30 * s, P_COLORS[1], "center", True)
        self._t(W / 2, H * 0.49, f"{names[2]} : {eur(r['wealth2'])}", 30 * s, P_COLORS[2], "center", True)
        self._t(W / 2, H * 0.60, "Entrée / Espace : revanche   |   Échap : menu", 22 * s, TEXT, "center")
