"""Exports each agent's definition and mapping (Ingescape JSON) to whiteboard/ for use in IngeScape Whiteboard."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json  # noqa: E402

from agents.wiring import Platform  # noqa: E402
from ui.ui import UI  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "whiteboard")


def main():
    ui = UI(fullscreen=False)
    ui.root.withdraw()
    platform = Platform(ui_agent=ui)
    agents = [platform.bourse.agent, platform.journal.agent, platform.p1.agent, platform.p2.agent,
              platform.ai.agent, ui.agent]
    os.makedirs(OUT, exist_ok=True)
    for a in agents:
        with open(os.path.join(OUT, f"{a.name()}.definition.json"), "w", encoding="utf-8") as f:
            f.write(a.definition_json())
        with open(os.path.join(OUT, f"{a.name()}.mapping.json"), "w", encoding="utf-8") as f:
            f.write(a.mapping_json())
    with open(os.path.join(OUT, "bulle_and_bear.platform.json"), "w", encoding="utf-8") as f:
        json.dump({"agents": [{"name": a.name(), "definition": json.loads(a.definition_json()),
                               "mapping": json.loads(a.mapping_json())} for a in agents]}, f, indent=2, ensure_ascii=False)
    ui.root.destroy()
    print(f"exported {len(agents)} agents to {os.path.abspath(OUT)}")


if __name__ == "__main__":
    main()
