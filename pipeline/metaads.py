#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""metaads.py : la trace de la consultation de la bibliothèque publicitaire Meta.

**Pourquoi ce verrou existe.** Le skill de Kreative demande de consulter la
bibliothèque publicitaire Meta à chaque commande, avant la stratégie : le
registre verbal du client, les annonces qui tournent depuis longtemps, les
angles déjà diffusés qu'il ne faut pas redoubler. Il la dit non bloquante, et
précise que ce qui n'est pas permis, c'est de ne pas essayer. Rien ne le
vérifiait. Mesuré le 25/09 sur la page blanche du client A : les navigateurs étaient
indisponibles, la bibliothèque n'a pas été consultée, et le pack s'est écrit
sans savoir que la marque avait 88 publicités, zéro active, avec des angles
« élégance et amour » et le cadeau déjà tournés.

**Ce que ce module fait.** Il ne consulte rien lui-même : la bibliothèque
bloque les navigateurs automatisés neufs, c'est la session qui l'ouvre avec le
navigateur. Il enregistre le résultat de la tentative dans
`marque/meta-ads.json`, et `parcours.py` comme `plan.py importer` exigent ce
fichier avant la stratégie. Trois issues sont recevables :

- `releve` : des annonces statiques ont été relevées, avec au moins une
  capture et une ligne par annonce retenue ;
- `aucune` : la bibliothèque a été lue et ne montre aucune annonce statique du
  client, une capture le prouve ;
- `echec` : inaccessible après deux essais, connexion exigée, page vide. Le
  motif s'écrit en toutes lettres.

Un échec est accepté, conformément au skill. L'absence de tentative ne l'est pas.

**La limite, dite franchement.** Comme les autres registres, une consignation
est une déclaration. Les captures, elles, doivent exister sur le disque.

Usage :
    python3 pipeline/metaads.py consigner <ardoise> --statut releve \\
        --captures marque/meta-ads/01.png --annonces annonces.json \\
        --note "ce que la bibliothèque dit du registre et des angles tournés"
    python3 pipeline/metaads.py consigner <ardoise> --statut echec \\
        --motif "connexion exigée aux deux essais"
    python3 pipeline/metaads.py exiger <ardoise>

`annonces.json` : une liste de `{"texte": ..., "angle": ..., "active": true,
"depuis": "2026-06"}`, une entrée par annonce statique retenue.

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

REGISTRE = "marque/meta-ads.json"
STATUTS = ("releve", "aucune", "echec")
# Une note ou un motif plus court est une case cochée.
TEXTE_MINIMUM = 25


def _chemin(commande: Commande) -> Path:
    return commande.dossier / REGISTRE


def lire(commande: Commande) -> Optional[dict]:
    chemin = _chemin(commande)
    if not chemin.exists():
        return None
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def verifier(commande: Commande) -> List[str]:
    """Les manquements, vide si la tentative est consignée et recevable."""
    trace = lire(commande)
    if trace is None:
        return ["bibliotheque publicitaire Meta jamais tentee : l'ouvrir au "
                "navigateur, puis `metaads.py consigner` (un echec motive est "
                "accepte, l'absence de tentative non)"]
    fautes: List[str] = []
    statut = trace.get("statut")
    if statut not in STATUTS:
        fautes.append(f"statut inconnu : {statut!r}, attendu {', '.join(STATUTS)}")
        return fautes
    if statut == "echec":
        if len((trace.get("motif") or "").strip()) < TEXTE_MINIMUM:
            fautes.append("echec sans motif ecrit en toutes lettres")
        return fautes
    captures = trace.get("captures") or []
    presentes = [c for c in captures if (commande.dossier / c).is_file()]
    if not presentes:
        fautes.append(f"statut {statut} sans aucune capture presente sur le disque")
    if len((trace.get("note") or "").strip()) < TEXTE_MINIMUM:
        fautes.append(f"statut {statut} sans note : ce que la bibliotheque dit "
                      "du registre et des angles deja tournes")
    if statut == "releve" and not trace.get("annonces"):
        fautes.append("statut releve sans aucune annonce consignee")
    return fautes


def consigner(commande: Commande, statut: str, motif: str, note: str,
              captures: List[str], annonces_fichier: Optional[Path]) -> int:
    annonces = []
    if annonces_fichier:
        annonces = json.loads(annonces_fichier.read_text(encoding="utf-8"))
        if not isinstance(annonces, list):
            print("REFUS  -  le fichier d'annonces doit contenir une liste.")
            return 1
    trace = {
        "statut": statut,
        "le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "motif": motif.strip(),
        "note": note.strip(),
        "captures": captures,
        "annonces": annonces,
    }
    chemin = _chemin(commande)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    precedente = lire(commande)
    chemin.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    fautes = verifier(commande)
    if fautes:
        # On garde la tentative précédente si la nouvelle n'est pas recevable.
        if precedente is not None:
            chemin.write_text(json.dumps(precedente, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        else:
            chemin.unlink()
        print("REFUS  -  consignation non recevable :")
        for f in fautes:
            print(f"  {f}")
        return 1
    commande.tracer("meta_ads_consigne", statut=statut, annonces=len(annonces),
                    captures=len(captures))
    print(f"Bibliotheque Meta consignee : {statut}, {len(annonces)} annonce(s), "
          f"{len(captures)} capture(s).")
    return 0


def exiger(commande: Commande) -> int:
    fautes = verifier(commande)
    if not fautes:
        print(f"OK  -  bibliotheque Meta consignee ({lire(commande).get('statut')}).")
        return 0
    print("REFUS  -  " + " ; ".join(fautes))
    return 1


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = a.add_subparsers(dest="commande", required=True)

    p = sous.add_parser("consigner", help="Enregistrer le résultat de la tentative")
    p.add_argument("ardoise")
    p.add_argument("--statut", required=True, choices=STATUTS)
    p.add_argument("--motif", default="", help="obligatoire sur un echec")
    p.add_argument("--note", default="", help="ce que la bibliothèque dit, sur releve ou aucune")
    p.add_argument("--captures", nargs="*", default=[], help="chemins relatifs à la commande")
    p.add_argument("--annonces", type=Path, help="fichier JSON, liste des annonces retenues")

    p = sous.add_parser("exiger", help="Gate : la tentative est consignée")
    p.add_argument("ardoise")

    args = a.parse_args()
    commande = Commande.charger(args.ardoise)
    if args.commande == "consigner":
        return consigner(commande, args.statut, args.motif, args.note,
                         args.captures, args.annonces)
    return exiger(commande)


if __name__ == "__main__":
    raise SystemExit(main())
