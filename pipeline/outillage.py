#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""outillage.py : l'étape 0 du skill, le navigateur vérifié avant tout.

**Pourquoi ce verrou existe.** Le skill de Kreative ouvre son process ainsi :
« `navigate_page` vers le site du client, puis `take_screenshot`. Si ça
répond, tu continues sans en parler. Si ça ne répond pas, tu t'arrêtes là et
tu écris : Navigateur indisponible, analyse visuelle impossible, run
interrompu. » Et plus haut : « Sans navigateur, tu ne produis pas. »

La chaîne disait l'inverse : son CLAUDE.md autorisait à continuer sur les
captures du scraper en le signalant. Mesuré le 25/09 sur la page blanche
le client A : les deux navigateurs étaient verrouillés, le run a continué sur les
captures, contre la lettre du skill. Aligné sur lui le 26/09, décision de l'équipe.

**Ce que ce module fait.** Il enregistre le résultat de l'étape 0 dans
`marque/outillage.json`. `parcours.py` l'exige avant la banque, et s'arrête
sur l'étape `interrompu` tant que le navigateur est déclaré indisponible.
`plan.py importer` refuse le premier plan sans un navigateur vérifié.

Usage :
    python3 pipeline/outillage.py consigner <ardoise> --navigateur ok \\
        --capture marque/navigateur/accueil.png
    python3 pipeline/outillage.py consigner <ardoise> --navigateur indisponible \\
        --motif "les deux serveurs MCP verrouillés par une instance déjà lancée"
    python3 pipeline/outillage.py exiger <ardoise>

Cible Python 3.9+. Aucune dépendance.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

from etat import Commande  # noqa: E402

REGISTRE = "marque/outillage.json"
MESSAGE_ARRET = "Navigateur indisponible, analyse visuelle impossible, run interrompu."
MOTIF_MINIMUM = 20


def lire(commande: Commande) -> Optional[dict]:
    chemin = commande.dossier / REGISTRE
    if not chemin.exists():
        return None
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def etat(commande: Commande) -> str:
    """« absent », « ok » ou « indisponible »."""
    trace = lire(commande)
    if trace is None:
        return "absent"
    if trace.get("navigateur") == "ok" and (commande.dossier / (trace.get("capture") or "")).is_file():
        return "ok"
    if trace.get("navigateur") == "indisponible":
        return "indisponible"
    return "absent"


def verifier(commande: Commande) -> List[str]:
    situation = etat(commande)
    if situation == "ok":
        return []
    if situation == "indisponible":
        return [f"{MESSAGE_ARRET} Motif : {(lire(commande) or {}).get('motif', '')}"]
    return ["navigateur jamais vérifié (étape 0 du skill) : navigate_page vers le "
            "site, take_screenshot, puis `outillage.py consigner`"]


def consigner(commande: Commande, navigateur: str, capture: str, motif: str) -> int:
    if navigateur == "ok" and not (commande.dossier / capture).is_file():
        print(f"REFUS  -  capture introuvable : {capture}. Enregistrer la capture "
              f"take_screenshot dans la commande, puis consigner.")
        return 1
    if navigateur == "indisponible" and len(motif.strip()) < MOTIF_MINIMUM:
        print("REFUS  -  motif trop court : dire pourquoi le navigateur ne répond pas.")
        return 1
    chemin = commande.dossier / REGISTRE
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps({
        "navigateur": navigateur,
        "capture": capture,
        "motif": motif.strip(),
        "le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    commande.tracer("outillage_consigne", navigateur=navigateur)
    if navigateur == "indisponible":
        print(MESSAGE_ARRET)
        return 0
    print("Navigateur vérifié : la chaîne peut continuer.")
    return 0


def exiger(commande: Commande) -> int:
    fautes = verifier(commande)
    if not fautes:
        print("OK  -  navigateur vérifié.")
        return 0
    print("REFUS  -  " + " ; ".join(fautes))
    return 1


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = a.add_subparsers(dest="commande", required=True)
    p = sous.add_parser("consigner", help="Enregistrer le résultat de l'étape 0")
    p.add_argument("ardoise")
    p.add_argument("--navigateur", required=True, choices=("ok", "indisponible"))
    p.add_argument("--capture", default="", help="chemin relatif de la capture, sur ok")
    p.add_argument("--motif", default="", help="obligatoire sur indisponible")
    p = sous.add_parser("exiger", help="Gate : navigateur vérifié")
    p.add_argument("ardoise")
    args = a.parse_args()
    commande = Commande.charger(args.ardoise)
    if args.commande == "consigner":
        return consigner(commande, args.navigateur, args.capture, args.motif)
    return exiger(commande)


if __name__ == "__main__":
    raise SystemExit(main())
