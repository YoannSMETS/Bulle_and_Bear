# Bulle & Bear — Software Specification

**Project:** Bulle & Bear — a 2-player (human vs human / human vs AI) stock market simulation game
**Version:** 0.1 (draft)
**Date:** 2026-11-02
**Status:** Specification for implementation

---

## 1. Overview

**Bulle & Bear** is a local, split-screen stock market simulation game. Two players (human vs human, or human vs AI) compete over a simulated year of trading. The goal is simple: **at the end of the game, the player with the largest total portfolio value (cash + holdings) wins.**

Each player can trade on **three assets**: a cryptocurrency (high volatility), a stock (medium volatility), and gold (low volatility). Random news events occur throughout the game and immediately impact the markets.

The whole system is built with the **IngScape / IngEscape** agent framework, using the resources and software provided at:
> https://repository.ingescape.com/upssitech/ (IngScape Whiteboard, course material, `.igslicense`)
Some documentation on :
>  https://github.com/zeromq/ingescape

## 2. Goals & Non-Goals

### Goals
- G1. A playable 1v1 game on a **single screen, single keyboard** (split view).
- G2. A playable 1vAI game with **3 selectable difficulty levels**.
- G3. A central **"Bourse" (Exchange) agent** that manages all asset prices.
- G4. Realistic-feeling price simulation with per-asset volatility profiles.
- G5. **12 random news events** (1 per simulated month) that immediately affect prices.
- G6. A clear, colourful, French-language UI with on-screen keyboard help.
- G7. Architecture designed in **IngScape Whiteboard**; agents implemented in **Python**.

### Non-Goals
- NG1. Online / network multiplayer (both players are on the same machine).
- NG2. Leverage, margin, short selling, limit orders.
- NG3. Fake/misleading news (all news is true and immediately visible).
- NG4. Account persistence across sessions (no save games in v1; optional score tracking only).

## 3. Gameplay

### 3.1 Match structure
- One match simulates **1 year (12 months) of trading** in **6 minutes of real time**.
  - ⇒ 1 simulated month = 30 seconds; 1 simulated month is split into monthly price ticks.
- The clock is displayed as **"Janvier 2026 → Décembre 2026"** and advances in real time for immersion.
- Starting capital: **10 000 €** for each player (identical).
- Assets are fully divisible: players may buy **fractional units** (e.g. 0.5 BTCX).

### 3.2 Assets
| Asset | Name (fictional) | Volatility profile | Description |
|---|---|---|---|
| Crypto | **BTCX** | Very high | Wild swings, can double or halve in a month |
| Stock  | **CORPO** | Medium  | Follows economic trends with moderate noise |
| Gold   | **OR** | Low | Safe haven; rises when markets fall (war, crisis) |

Price model: a **realistic stochastic model** (random walk with drift, mean-reversion components, per-asset volatility σ, and cross-correlations so that gold acts as a safe haven).

### 3.3 Trading rules
- Order type: **market orders only** (buy / sell at current price).
- No leverage, no short selling, no limit orders.
- **Transaction fees** (applied per trade, deducted from the player's cash):
  | Asset | Fee |
  |---|---|
  | BTCX (crypto) | High (e.g. 1.5 %) |
  | CORPO (stock) | Medium (e.g. 0.75 %) |
  | OR (gold) | Low (e.g. 0.25 %) |
- **Shared market, independent impact:** both players see the **same market** and the same prices, but their individual buy/sell orders do **not** move the price (pure market simulation, no supply/pressure model). This guarantees fairness.
- Trades are executed instantly at the current tick price, fees included in the computed cost.

### 3.4 Victory condition
- At the end of the 6 minutes (12 simulated months), each player's total wealth is computed:
  `wealth = cash + Σ (quantity_held × final_price) − pending nothing`.
- **The player with the largest wealth wins.** Ties are possible → the game displays "Égalité".
- A rematch button is available; optionally a session scoreboard tracks wins across rematches.

## 4. Random Events (News)

- Exactly **12 events per match**, one per simulated month (one every ~30 s), drawn from a pool of ~20 predefined events.
- Events are announced through an on-screen **news feed (fil d'actualités)** and take effect **immediately** on prices. No fake news: every headline truthfully reflects its market effect.
- Events may affect **one, two, or all three assets**, with multipliers on drift/volatility for the following months. Example table:

| Event (FR, with humour) | BTCX | CORPO | OR |
|---|---|---|---|
| « Guerre mondiale : les marchés paniquent » | ↓↓ | ↓↓ | ↑↑ |
| « Hack massif : BTCX piraté, les clés perdues sur ClavierAzerty » | ↓↓↓ | ↓ | ↑ |
| « La banque centrale baisse les taux à -1 % (pourquoi pas) » | ↑ | ↑ | ↓ |
| « Un milliardaire tweete auDDD sobre BTCX » | ↑↑ | ↓ | = |
| « Pandémie de grippe du serveur de la Bourse » | = | ↓ | ↑ |
| « Nouveau président élu sur un programme pro-or » | = | = | ↑↑ |
| « La crypto devient une monnaie officielle d'un micro-État » | ↑↑↑ | ↑ | = |
| « Scandale financier : le PDG de CORPO fuites avec la caisse » | = | ↓↓ | ↑ |
| « Une mine d'or découverte sous un lycée » | = | = | ↓↓ |
| « etc. » | … | … | … |

- Events are emitted by a dedicated **"Journal" agent**.

## 5. Modes of Play

### 5.1 Human vs Human (1v1)
- Both human players on one machine, one keyboard, **split view**.
- Left panel = Player 1, right panel = Player 2. Each player sees their own portfolio; both see the same market charts and the same news feed.

### 5.2 Human vs AI (1vAI)
- The AI is an **agent with the same interface and the same information as a human player**, but trades are decided by its strategy agent.
- The AI behaves **like a human**: it makes decisions at regular human-like intervals (not every tick), with delays and occasional suboptimal trades.
- **3 difficulty levels (selectable in the menu):**
  | Level | Behaviour |
  |---|---|
  | Facile | Near-random trades, poor timing, reacts slowly to news |
  | Normal | Follows trends (momentum), reacts to major news with delay |
  | Difficile | Reacts quickly to news, exploits volatility, occasionally diversifies optimally |

## 6. User Interface

### 6.1 Layout & display
- Target resolution: **1920×1080 (16:9)**, full screen.
- Split view: **Player 1 panel on the left, Player 2 panel on the right**, with the shared market charts and the news feed visible to both.
- Interface language: **French**.
- Keyboard mapping is **AZERTY-based** and **always displayed on screen** (persistent help strip at the bottom of each player's panel).

### 6.2 Keyboard controls (AZERTY)
| Action | Joueur 1 (left) | Joueur 2 (right) |
|---|---|---|
| Navigate (select asset / section) | `Q` / `D` | `←` / `→` |
| Buy  | `Z` | `↑` |
| Sell | `S` | `↓` |
| Focus portfolio / toggle asset vs portfolio | `E` | `Maj (Shift)` |
| Change quantity of next order | `A` / `E` cycle presets? *(to finalise: presets 25/50/75/100 % or typed amount — TBD)* |
| Start / pause / rematch | `Espace` / `Entrée` (either player) |

> ⚠ Note: final key mapping must avoid AZERTY conflicts between the two players (e.g. `S` is used by P1 for sell and by P2's arrows for sell — they are distinct physical keys, so no conflict). This must be validated during playtesting.

### 6.3 Panels & widgets
Each player panel displays:
1. **Live price chart** (candlestick or line) per selected asset, updating in real time.
2. **Portfolio** — quantities held per asset and their current value.
3. **Cash** — available balance.
4. **Transaction history** — timestamps, asset, side (buy/sell), quantity, price, fees.
5. **News feed** — chronological list of headlines (shared view).

## 7. Architecture (IngScape / IngEscape)

### 7.1 Framework
- The system architecture is designed in **IngScape Whiteboard** (from the provided repository), using the UPSSITECH 2026 course as reference. *(Licence fournie par le référentiel — the `.igslicense` file from the repository is used as-is.)*
- Agents are implemented in **Python** via the IngEscape Python bindings; behaviour is triggered through IngScape IOP (inputs/outputs), parameters and services.
- One **single process runs multiple internal agents** — no distributed instances.

### 7.2 Agents
| Agent | Type | Responsibilities |
|---|---|---|
| **Bourse** (Exchange) | Central server agent | Owns all price state; ticks the market every month (~30 s); computes prices with the stochastic model; applies event multipliers; handles buy/sell requests from Player1, Player2 and AI; computes fees. |
| **Journal** (News) | Event agent | Draws 1 event per simulated month from the event pool; publishes the headline and its market effects; sends them to Bourse and to the UI. |
| **Player1** | Human agent | Reads keyboard inputs for P1; sends buy/sell requests to Bourse; exposes own portfolio & cash. |
| **Player2** | Human agent | Same as Player1 but for the right-hand player (or replaced by AI below). |
| **AI** | Automated agent | Same IOP contract as a Player agent; decides trades based on difficulty level; reacts to news with a human-like delay. |
| **UI** | Interface agent | Renders the 1920×1080 split view, charts, news feed, portfolio panels, keyboard help; collects keyboard events and feeds the Player agents. |

### 7.3 Agent interactions (IOP wiring, indicative)
```
Journal ──(event, impact)──▶ Bourse
Bourse ──(tick, prices[], fees)──▶ Player1 / Player2 / AI / UI
Player1 ──(buy/sell, asset, qty)──▶ Bourse
Bourse ──(trade_result, cash, portfolio)──▶ Player1
AI      ──(buy/sell, asset, qty)──▶ Bourse   (same contract as a human player)
UI      ──(key_event)──▶ Player1 / Player2
```
- All connections (mappings) are defined in the IngScape Whiteboard project file.

## 8. Requirements

### 8.1 Functional requirements
| ID | Requirement |
|---|---|
| FR-1 | The game runs one match of 12 simulated months in 6 real-time minutes. |
| FR-2 | Three tradable fictional assets exist: BTCX (crypto, very volatile), CORPO (stock, medium), OR (gold, low). |
| FR-3 | Each player starts with 10 000 € and can trade fractional quantities. |
| FR-4 | Market orders only; no leverage, no short selling. |
| FR-5 | Per-asset transaction fees are applied (crypto > stock > gold). |
| FR-6 | Both players see the same market; trades do not influence prices. |
| FR-7 | 12 news events are drawn (one per month) from a predefined humorous pool; effects apply immediately. |
| FR-8 | Events can affect one, two or all three assets. |
| FR-9 | Supports 1v1 (two humans, one keyboard) and 1vAI (3 difficulty levels). |
| FR-10 | The AI behaves with human-like timing and sees the same information as humans. |
| FR-11 | The winner is the player with the greatest final wealth (cash + holdings). |
| FR-12 | A rematch is offered at the end of the match. |
| FR-13 | Interface is French, 1920×1080, split view (P1 left, P2 right). |
| FR-14 | AZERTY keyboard controls are shown on screen at all times. |
| FR-15 | The UI displays live charts, portfolio, cash, transaction history and a news feed. |

### 8.2 Non-functional requirements
| ID | Requirement |
|---|---|
| NFR-1 | Architecture is modelled in IngScape Whiteboard (single process, multiple agents). |
| NFR-2 | Agents are implemented in Python (IngEscape bindings). |
| NFR-3 | The game runs on Windows x64 (Whiteboard win64 build provided). |
| NFR-4 | UI stays responsive (>30 fps) while market ticks and news are processed. |
| NFR-5 | The codebase is hosted on a clean GitHub repository with a README explaining how to install, activate the licence and play. |
| NFR-6 | The `.igslicense` from the referential is used as provided (licence fournie par le référentiel). |

## 9. Project Structure (suggested)

```
bulle-and-bear/
├── README.md               # how to play, install, licence
├── specifications.md       # this document
├── whiteboard/
│   └── bulle_and_bear.igs  # IngScape Whiteboard architecture
├── agents/                 # Python agents (ingescape)
│   ├── bourse.py
│   ├── journal.py
│   ├── player.py
│   └── ai.py
├── ui/                     # UI agent / rendering
│   └── ui.py
├── engine/                 # price model, fees, event pool
│   ├── price_model.py
│   └── events.py
└── tests/                  # unit tests (price model, fees, win condition)
```
*(Repository layout to be finalised with the team.)*

## 10. Validation & Verification (V&V)

Following the spirit of the course material (`Ingescape_VandV.pdf`), the following checks must pass before release:
- **V1** — A 6-minute match finishes in real time with a declared winner (or tie).
- **V2** — Prices respect the intended volatility ranking: BTCX > CORPO > OR (statistical check over several runs).
- **V3** — Fees are correctly computed and deducted for each asset type.
- **V4** — Each month produces exactly one news event, and its effect is visible on the next price tick.
- **V5** — The AI at each difficulty produces the expected trade behaviour (manual observation).
- **V6** — Keyboard controls work in AZERTY for both players without conflict; help strip is always visible.

## 11. Open Points / To Be Finalised

- Exact quantity-selection mechanism for orders (presets 25/50/75/100 % vs free amount input).
- Final AZERTY key mapping (playtest to confirm no conflicts).
- Final fee percentages (1.5 % / 0.75 % / 0.25 % are proposed values).
- Complete list of the ~20 humorous news events and their impact multipliers.
- Python version and packaging (requirements.txt / venv instructions in README).

## 12. References

- IngScape / IngEscape resources for UPSSITECH 2026: https://repository.ingescape.com/upssitech/
  - `Ingescape_course_UPSSITECH_2026.pdf` — course material
  - `UPSSITECH_RSI_2026.igslicense` — licence
  - `Whiteboard/` — IngScape Whiteboard software (win64/linux/macos)
  - `Ingescape_VandV.pdf` — validation & verification guidance
