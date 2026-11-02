# Bulle & Bear

Jeu de simulation boursière à 2 joueurs (humain vs humain, ou humain vs IA) — voir `specifications.md`.
Un match = 12 mois simulés (Janvier → Décembre 2026) en 6 minutes. Capital initial : 10 000 € par joueur,
3 actifs (BTCX, CORPO, OR), 12 actualités tirées parmi 22, frais par actif (1,5 % / 0,75 % / 0,25 %).

## Installation

1. Python 3.10+ (Windows x64) — `winget install Python.Python.3.12`
2. `pip install -r requirements.txt` (paquet `ingescape` + `pytest`)
3. Licence : copier `UPSSITECH_RSI_2026.igslicense` (fournie par le référentiel, utilisée telle quelle) dans
   `Documents\IngeScape\licenses\` (déjà fait sur cette machine).

## Jouer

```
python main.py                    # plein écran (F11 : basculer), réseau = 1re carte non-loopback
python main.py --windowed --speed 10 --seed 42
python main.py --device "Loopback Pseudo-Interface 1" --port 5670
```

Options : `--speed` accélère le temps (1 = 6 min), `--seed` rend marché et actualités reproductibles.
Menu : ↑ ↓ + Entrée. Entrée/Espace : pause / revanche. Échap : menu / quitter.

### Touches (AZERTY, affichées en bas de chaque panneau)

| Action | Joueur 1 | Joueur 2 |
|---|---|---|
| Actif précédent / suivant | `A` / `Z` | `Q` / `S` |
| Acheter / Vendre | `E` / `R` | `D` / `F` |
| Marché ⇄ Portefeuille | `T` | `G` |
| Saisir le montant en € (chiffres de la rangée du haut ou du pavé numérique, ⌫ pour corriger, même touche pour valider) | `Y` | `H` |
| Montant maximum (tout le cash / toute la position) | `U` | `J` |

Les ordres se passent en **euros** : la quantité (fractionnaire) est calculée à partir du prix courant.
Achat de *M* € : frais = *M*×taux, quantité = (*M*−frais)/prix. Vente de *M* € : cash reçu = *M*×(1−taux).
Les montants sont plafonnés au cash / à la position. Un seul joueur à la fois saisit des chiffres (le dernier à avoir
appuyé sur sa touche de saisie).

## Architecture (un seul processus, plusieurs agents Ingescape via `igs.Agent`)

| Agent | Entrées | Sorties |
|---|---|---|
| **Bourse** | `command`, `event`, `order_p1`, `order_p2` | `market`, `account_p1`, `account_p2`, `month_start`, `new_game` |
| **Journal** | `new_game`, `month_start` | `event` |
| **Player1 / Player2** | `key_event`, `account` | `order`, `view` |
| **AI** (même contrat que Player2) | `market`, `account`, `event` | `order` |
| **UI** | `market`, `view_p1`, `view_p2`, `news_event` | `key_p1`, `key_p2`, `command` |

Mappings : voir `agents/wiring.py` et `whiteboard/` (définitions + mappings JSON de chaque agent, générés par
`python tools/export_whiteboard.py`). Toutes les valeurs structurées sont des chaînes JSON.
Commandes UI → Bourse : `start:1v1`, `start:ai:<facile|normal|difficile>`, `toggle_pause`, `rematch`, `menu`.

```
engine/   modèle de prix, événements, grand livre (frais), IA, contrôleur clavier  (Python pur, testé)
agents/   Bourse, Journal, Player, AI + câblage
ui/       agent UI (tkinter, 1920×1080 adaptatif)
tests/    pytest : V2 (volatilité), V3 (frais), V4 (1 actu/mois), IA, match complet 1v1 et 1vIA
```

### UI dans Whiteboard
L'UI fournie est un agent Python (tkinter) jouable tel quel. Pour utiliser Whiteboard à la place : lancer
`python main.py` (les agents apparaissent sur le réseau), puis dans Whiteboard créer des widgets liés aux IOP
ci-dessus (ex. afficher `Bourse.market`, envoyer `Bourse.command`). Le clavier AZERTY dual-joueur n'est pas
capturable depuis Whiteboard, d'où l'agent UI Python.

## Tests

```
python -m pytest
```
Le test d'intégration démarre Ingescape en boucle locale (port 5681) et joue un match accéléré.
