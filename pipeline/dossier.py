#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dossier.py : le registre des fichiers que le client a lui-même fournis.

**Pourquoi ce verrou existe.** La banque de références a son registre depuis le
19/09, et il a servi. Le dossier du client, lui, n'en avait aucun : ses pièces
jointes et sa production précédente étaient sur le disque et rien n'obligeait
à les ouvrir. Mesuré le 21/09 sur le client A, trois fichiers jamais ouverts
alors qu'ils étaient rangés dans la commande :

- `refs_aimees/01-IMG_7238.jpg` n'était pas une créa aimée mais **la charte
  officielle**, avec une troisième couleur, l'argent brossé #C0C0C0, que la
  session a donc ignorée. La production de septembre, elle, l'utilisait.
- `lifestyle/01-IMG_7376.jpg` montrait le registre RÉEL de la marque, une
  photo de mode avec un mannequin, quand la session partait sur du minéral
  feutré tiré du seul champ `decors` du brief.
- `masters-v3-echantillon/c01.png` portait déjà l'accroche « 30 % de
  concentration. Là où le marché tourne souvent autour de 15 % ». La session a
  réécrit la même phrase en croyant inventer.

Coût constaté : 14 crédits dépensés sur une direction déjà faite en mieux, et
une décision d'architecture prise sur une prémisse fausse.

**Ce que ce module fait.** Il ne juge rien. Il liste ce que le client a fourni,
il enregistre ce qui a été réellement ouvert, et `plan.py importer` refuse le
plan ENTIER tant qu'il reste un fichier non vu. Le refus porte sur le plan et
non sur une créa, comme pour la banque : une direction artistique se décide sur
tout le matériel ou sur rien.

**La limite, dite franchement.** Comme `banque.py lue` et comme les verdicts de
`relecture.py`, une consignation est une déclaration et non une preuve. Elle
transforme un oubli silencieux en acte explicite. L'empreinte du fichier est
vérifiée, en revanche : un asset remplacé repasse en non vu.

Usage :
    python3 pipeline/dossier.py inventaire <ardoise>
    python3 pipeline/dossier.py vu <ardoise> --fichier <chemin relatif> \\
        --note "ce que j'y ai vu et ce que ça change"
    python3 pipeline/dossier.py exiger <ardoise>

Cible Python 3.9+. Aucune dépendance.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

from etat import Commande  # noqa: E402

REGISTRE = "session/dossier.json"
EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".avif")

# Une note plus courte que ça est une case cochée. Le 19/09 a montré ce que
# vaut une liste de contrôle déclarative : c'est la formulation de ce qu'on a
# vu qui oblige à regarder.
NOTE_MINIMUM = 25


def _chemin_registre(commande: Commande) -> Path:
    return commande.dossier / REGISTRE


def lire_registre(commande: Commande) -> dict:
    chemin = _chemin_registre(commande)
    if not chemin.exists():
        return {}
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _ecrire_registre(commande: Commande, registre: dict) -> None:
    chemin = _chemin_registre(commande)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(registre, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")


def _empreinte(chemin: Path) -> str:
    etat = chemin.stat()
    return f"{etat.st_size}-{etat.st_mtime_ns}"


def a_ouvrir(commande: Commande) -> Dict[str, List[str]]:
    """Ce que le client a fourni, par famille, en chemins relatifs.

    Trois familles. Les deux premières portent l'identité du client et sa
    production antérieure. La troisième, les captures de son site, a été
    ajoutée le 21/09 à la demande de l'équipe : le skill en fait la PREMIÈRE source
    sur tout ce qui est visuel et sur le registre verbal, et c'est la faute la
    plus ancienne du dépôt. Le 19/09 sur le client A, vingt-cinq captures produites
    et une seule ouverte ; le 21/09, quinze produites et aucune, pendant que
    la copy s'écrivait sur les seuls champs du formulaire.

    Les assets bruts aspirés (`marque/assets-site/`) restent dehors : ce sont
    des matériaux, pas de la doctrine, et ils se comptent par centaines.
    """
    familles: Dict[str, List[str]] = {
        "pieces jointes du brief": [], "production precedente": [], "captures du site": []}

    joints = commande.dossier / "brief" / "pieces-jointes"
    if joints.is_dir():
        familles["pieces jointes du brief"] = sorted(
            str(f.relative_to(commande.dossier))
            for f in joints.rglob("*") if f.suffix.lower() in EXTENSIONS)

    anciens: List[str] = []
    for repertoire in sorted(commande.dossier.glob("masters*")):
        if repertoire.is_dir():
            anciens += [str(f.relative_to(commande.dossier))
                        for f in sorted(repertoire.glob("*"))
                        if f.suffix.lower() in EXTENSIONS]
    familles["production precedente"] = anciens

    captures = commande.dossier / "marque" / "captures"
    if captures.is_dir():
        familles["captures du site"] = sorted(
            str(f.relative_to(commande.dossier))
            for f in captures.iterdir() if f.suffix.lower() in EXTENSIONS)

    return familles


def _vu_par_la_relecture(commande: Commande, relatif: str) -> bool:
    """Un master déjà jugé par `relecture.py` compte comme ouvert.

    La relecture est une preuve PLUS forte qu'une note de lecture : elle porte
    un verdict, une règle citée et l'empreinte du master au moment du jugement.
    Exiger une seconde consignation pour le même fichier ferait de ce verrou une
    paperasse, et un verrou qui fait perdre du temps pour rien finit contourné.
    L'empreinte est revérifiée ici : un master régénéré depuis son verdict
    redevient à ouvrir.
    """
    if not relatif.startswith("masters/"):
        return False
    chemin = commande.dossier / relatif
    if not chemin.exists():
        return False
    try:
        import relecture as module_relecture
        entree = (module_relecture.lire_registre(commande) or {}).get(Path(relatif).stem) or {}
    except Exception:
        return False
    return bool(entree.get("verdict")) and entree.get("empreinte") == _empreinte(chemin)


def _situation(commande: Commande, relatif: str, registre: dict) -> str:
    if _vu_par_la_relecture(commande, relatif):
        return "vu"
    entree = registre.get(relatif) or {}
    if not entree.get("note"):
        return "a_ouvrir"
    chemin = commande.dossier / relatif
    if not chemin.exists():
        return "disparu"
    if entree.get("empreinte") and entree["empreinte"] != _empreinte(chemin):
        return "remplace"
    return "vu"


def inventaire(commande: Commande) -> int:
    familles = a_ouvrir(commande)
    registre = lire_registre(commande)
    restants = 0

    for famille, fichiers in familles.items():
        if not fichiers:
            continue
        print(f"\n{famille.upper()}  ({len(fichiers)})")
        for relatif in fichiers:
            situation = _situation(commande, relatif, registre)
            marque = {"vu": "vu     ", "a_ouvrir": "À OUVRIR",
                      "remplace": "REMPLACÉ", "disparu": "disparu"}[situation]
            print(f"  [{marque}] {relatif}")
            if situation == "vu":
                print(f"             {registre[relatif]['note']}")
            elif situation != "disparu":
                restants += 1

    if restants:
        print(f"\n{restants} fichier(s) à ouvrir avec Read, puis à consigner :")
        print("  python3 pipeline/dossier.py vu <ardoise> --fichier <chemin> "
              "--note \"ce que j'y ai vu et ce que ça change\"")
    else:
        print("\nTout le matériel du client a été ouvert et consigné.")
    return 1 if restants else 0


def vu(commande: Commande, relatif: str, note: str) -> int:
    note = " ".join(note.split())
    if len(note) < NOTE_MINIMUM:
        print(f"REFUS  -  note trop courte ({len(note)} caractères, minimum "
              f"{NOTE_MINIMUM}). Écrire ce que le fichier contient et ce que ça "
              f"change pour la création, sinon la consignation ne vaut rien.")
        return 1

    chemin = commande.dossier / relatif
    if not chemin.exists():
        print(f"REFUS  -  fichier introuvable dans la commande : {relatif}")
        return 1

    attendus = {f for fichiers in a_ouvrir(commande).values() for f in fichiers}
    if relatif not in attendus:
        print(f"REFUS  -  {relatif} n'est pas un fichier fourni par le client. "
              f"Ce registre ne couvre que les pièces jointes du brief et la "
              f"production précédente.")
        return 1

    registre = lire_registre(commande)
    registre[relatif] = {
        "note": note,
        "date": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "empreinte": _empreinte(chemin),
    }
    _ecrire_registre(commande, registre)
    commande.tracer("dossier_vu", fichier=relatif)
    print(f"{relatif} : consigné.")
    return 0


def verifier(commande: Commande) -> List[str]:
    """Les manquements, pour `plan.py importer`. Vide si tout est ouvert."""
    registre = lire_registre(commande)
    fautes = []
    for famille, fichiers in a_ouvrir(commande).items():
        manquants = [f for f in fichiers
                     if _situation(commande, f, registre) in ("a_ouvrir", "remplace")]
        if manquants:
            fautes.append(
                f"{len(manquants)} fichier(s) du client jamais ouverts "
                f"({famille}) : {', '.join(manquants[:6])}"
                + (" ..." if len(manquants) > 6 else "")
                + ". Les ouvrir avec Read, puis dossier.py vu.")
    return fautes


def exiger(commande: Commande) -> int:
    fautes = verifier(commande)
    if not fautes:
        print("OK  -  tout le matériel fourni par le client a été ouvert.")
        return 0
    print("REFUS  -  du matériel du client n'a jamais été regardé.")
    for faute in fautes:
        print(f"  {faute}")
    return 1


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sous = a.add_subparsers(dest="commande", required=True)

    p = sous.add_parser("inventaire", help="Ce que le client a fourni, et ce qui reste à ouvrir")
    p.add_argument("ardoise")

    p = sous.add_parser("vu", help="Consigner un fichier réellement ouvert")
    p.add_argument("ardoise")
    p.add_argument("--fichier", required=True, help="chemin relatif à la commande")
    p.add_argument("--note", required=True, help="ce qui a été vu, et ce que ça change")

    p = sous.add_parser("exiger", help="Gate : tout le matériel du client est ouvert")
    p.add_argument("ardoise")

    args = a.parse_args()
    commande = Commande.charger(args.ardoise)

    if args.commande == "inventaire":
        return inventaire(commande)
    if args.commande == "vu":
        return vu(commande, args.fichier, args.note)
    return exiger(commande)


if __name__ == "__main__":
    raise SystemExit(main())
