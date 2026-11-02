"""Pool of humorous news events. Levels: -3..+3 arrows per asset (BTCX, CORPO, OR)."""
import random

# (headline, BTCX, CORPO, OR)
EVENT_POOL = [
    ("Guerre mondiale : les marchés paniquent (et l'or fait la fête)", -2, -2, 2),
    ("Hack massif : BTCX piraté, les clés perdues sur ClavierAzerty", -3, -1, 1),
    ("La banque centrale baisse les taux à -1 % (pourquoi pas)", 1, 1, -1),
    ("Un milliardaire tweete « BTCX is life » à 3 h du matin", 2, -1, 0),
    ("Pandémie de grippe du serveur de la Bourse", 0, -1, 1),
    ("Nouveau président élu sur un programme pro-or", 0, 0, 2),
    ("La crypto devient monnaie officielle d'un micro-État (3 habitants)", 3, 1, 0),
    ("Scandale financier : le PDG de CORPO s'enfuit avec la caisse", 0, -2, 1),
    ("Une mine d'or découverte sous un lycée", 0, 0, -2),
    ("CORPO annonce des bénéfices records (et un nouveau babyfoot)", 0, 2, -1),
    ("Krach boursier : même les pigeons vendent", -2, -3, 2),
    ("Une IA prédit la hausse du BTCX, personne ne sait laquelle", 2, 0, 0),
    ("Les mineurs de BTCX en grève : plus de courant, plus de pioches", -1, 0, 0),
    ("Inflation galopante : la baguette coûte plus cher qu'un lingot", 1, -1, 2),
    ("CORPO lance un produit révolutionnaire : le stylo à bille bleu", 0, 2, 0),
    ("Les bijoutiers font des soldes : l'or devient tendance", 0, 0, 1),
    ("Sommet de la paix : tout le monde se serre la main, sauf l'or", 1, 2, -2),
    ("Panne géante d'Internet : BTCX introuvable, CORPO aussi", -2, -1, 1),
    ("Un chat marche sur le clavier d'un trader : vente massive de BTCX", -2, 0, 0),
    ("Boom de l'innovation : des start-ups de croquettes lèvent des millions", 1, 3, -1),
    ("Les banques centrales achètent de l'or par camions entiers", 0, -1, 3),
    ("Régulation de la crypto : un formulaire de 400 pages", -2, 0, 1),
]


def event_dict(idx, item):
    headline, b, c, o = item
    return {"id": idx, "headline": headline, "levels": {"BTCX": b, "CORPO": c, "OR": o}}


def draw_events(count=12, seed=None, pool=None):
    """Draw `count` distinct events (one per simulated month)."""
    pool = pool or EVENT_POOL
    rng = random.Random(seed)
    return [event_dict(i, pool[i]) for i in rng.sample(range(len(pool)), count)]
