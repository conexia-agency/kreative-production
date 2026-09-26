#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill.py : la règle zéro, rendue mécanique.

**Pourquoi ce verrou existe.** Le CLAUDE.md du dépôt ouvre par une règle qu'il
appelle lui-même « la règle qui rend toutes les autres superflues » : lire
`skill/strategie-creative.md` EN ENTIER, à chaque commande, avant d'écrire la
moindre ligne de stratégie ou de prompt. Elle n'était tenue par rien d'autre
que la bonne volonté de la session.

Mesuré le 22/09/2026 sur le client A, et c'est ce qui a motivé ce module :
le skill a été lu une fois, au quatrième lot de la journée, puis cinq lots de
plus ont été produits sans y retourner. Coût constaté :

- le **format visuel** n'était nommé dans aucun prompt des trois premiers lots,
  alors que le skill l'impose, ce qui a donné des décalques de références ;
- la **synthèse stratégique** de l'étape 3, celle qui pose les curseurs du
  registre, n'a jamais été écrite avant le quatrième lot : la copy du lot 1
  était descriptive, celle du lot 2 transactionnelle, deux registres hors brief ;
- un **scrim dégradé** a été réinventé de zéro alors qu'il est dans le skill
  depuis toujours, à la section « Marier photo + lisibilité ».

Aucune de ces fautes n'appelait un arbitrage. Toutes étaient écrites dans le
fichier.

**Ce que ce module fait.** Il enregistre que le skill a été lu, avec son
empreinte, et `plan.py importer` refuse le plan tant que la lecture n'est pas
déclarée pour cette commande. Si le fichier du skill change, la lecture est à
refaire : une déclaration porte sur un contenu, pas sur un nom de fichier.

Il exige aussi que la **synthèse stratégique** existe sur le disque avant tout
plan, parce que l'étape 3 du process décide du registre de toute la copy.

**La limite, dite franchement**, la même que pour `banque.py lue` et
`dossier.py vu` : une déclaration n'est pas une preuve de lecture. Elle
transforme un oubli silencieux en acte explicite, et elle date cet acte. Le
minimum de caractères sur la note sert à ça : on ne consigne pas sans avoir à
formuler ce qu'on a retenu.

Usage :
    python3 pipeline/skill.py lu <ardoise> --note "les sections qui changent
        quelque chose pour CETTE commande"
    python3 pipeline/skill.py exiger <ardoise>
    python3 pipeline/skill.py etat <ardoise>

Cible Python 3.9+. Aucune dépendance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

from etat import Commande  # noqa: E402

REGISTRE = "session/skill.json"

# Une note plus courte qu'une phrase est une case cochée. Le 19/09 a montré ce
# que vaut une liste de contrôle déclarative : c'est la formulation de ce qu'on
# a retenu qui oblige à lire.
NOTE_MINIMUM = 60

# Le fichier fait 379 lignes à l'origine. En dessous de ce seuil, ce n'est pas
# le skill mais un extrait, un résumé ou un fichier tronqué par l'empaquetage.
TAILLE_MINIMUM = 20_000


def chemin_skill() -> Optional[Path]:
    """Le skill, par le même résolveur que le reste de la chaîne."""
    # Dépôt : skill/ à côté du code. Paquet installé : le code est dans
    # scripts/ et le skill dans references/, un niveau au-dessus.
    for candidat in (
        ICI.parent / "skill" / "strategie-creative.md",
        ICI.parent / "references" / "strategie-creative.md",
        ICI.parent.parent / "references" / "strategie-creative.md",
        ICI.parent / "resources" / "strategie-creative.md",
        ICI.parent.parent / "resources" / "strategie-creative.md",
    ):
        if candidat.exists():
            return candidat
    return None


def empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()[:16]


def _registre(commande: Commande) -> dict:
    p = commande.dossier / REGISTRE
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _ecrire(commande: Commande, donnees: dict) -> None:
    p = commande.dossier / REGISTRE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8")


def chemin_strategie(commande: Commande) -> Path:
    return commande.dossier / "strategie-creative.md"


def verifier(commande: Commande) -> List[str]:
    """Les manquements, pour `plan.py importer`. Vide si tout est en règle."""
    fautes: List[str] = []

    source = chemin_skill()
    if source is None:
        fautes.append("le skill est introuvable sur le disque : la chaîne ne "
                      "doit pas produire sans lui.")
        return fautes
    if source.stat().st_size < TAILLE_MINIMUM:
        fautes.append(f"le skill fait {source.stat().st_size} octets, moins que "
                      f"les {TAILLE_MINIMUM} attendus : fichier tronqué.")
        return fautes

    registre = _registre(commande)
    attendue = empreinte(source)
    lue = registre.get("empreinte")
    if not lue:
        fautes.append(
            "le skill n'a jamais été déclaré lu pour cette commande. C'est la "
            "règle zéro du dépôt : 379 lignes, en entier, avant d'écrire une "
            "ligne de stratégie ou de prompt. Le lire avec Read, puis : "
            f"python3 pipeline/skill.py lu {commande.donnees['ardoise']} "
            "--note \"...\"")
    elif lue != attendue:
        fautes.append(
            f"le skill a changé depuis sa lecture (empreinte {lue} contre "
            f"{attendue}). Une déclaration porte sur un contenu : relire et "
            f"reconsigner.")

    strategie = chemin_strategie(commande)
    if not strategie.exists():
        fautes.append(
            "aucune synthèse stratégique sur le disque. C'est l'étape 3 du "
            "process du skill, et elle pose les curseurs qui décident du "
            "registre de toute la copy. La sauter, c'est écrire à l'aveugle. "
            f"Attendue ici : {strategie.relative_to(commande.dossier)}")
    elif strategie.stat().st_size < 800:
        fautes.append(
            f"la synthèse stratégique fait {strategie.stat().st_size} octets : "
            f"trop courte pour porter l'avatar, la problématique, l'objection "
            f"et les curseurs.")
    else:
        fautes += _contenu_strategie(commande, strategie.read_text(encoding="utf-8"))

    return fautes


# Les rubriques de la synthèse, dans les mots de l'étape 3 et du « Format de
# sortie » du skill. Mesuré le 26/09 : seule la taille du fichier était
# contrôlée, une synthèse pouvait omettre la température ou les curseurs.
RUBRIQUES_SYNTHESE = ("niche", "avatar", "problematique centrale", "objection cle",
                      "temperature", "positionnement", "ton", "curseurs")


def _plier(texte: str) -> str:
    import unicodedata
    n = unicodedata.normalize("NFD", texte or "")
    return "".join(c for c in n if unicodedata.category(c) != "Mn").lower()


def _section(texte: str, titre_plie: str) -> str:
    """Le corps de la section markdown dont le titre contient `titre_plie`."""
    lignes = texte.splitlines()
    for rang, ligne in enumerate(lignes):
        if ligne.lstrip().startswith("#") and titre_plie in _plier(ligne):
            niveau = len(ligne.lstrip()) - len(ligne.lstrip().lstrip("#"))
            corps = []
            for suite in lignes[rang + 1:]:
                s = suite.lstrip()
                if s.startswith("#") and len(s) - len(s.lstrip("#")) <= niveau:
                    break
                corps.append(suite)
            return "\n".join(corps)
    return ""


def _contenu_strategie(commande: Commande, texte: str) -> List[str]:
    fautes: List[str] = []
    plie = _plier(texte)
    import re
    absentes = [r for r in RUBRIQUES_SYNTHESE
                if not re.search(rf"(?<![a-z]){re.escape(r)}(?![a-z])", plie)]
    if absentes:
        fautes.append(
            "la synthèse stratégique n'a pas toutes les rubriques de l'étape 3 "
            f"du skill : manquent {', '.join(absentes)}.")

    # Skill, règle d'or 2 : « Tu traites CHAQUE champ du brief » et « à la fin,
    # tu confirmes la couverture du brief ». Chaque champ rempli du formulaire
    # doit être cité par son nom dans une section « Couverture du brief »,
    # avec ce qu'il est devenu : exploité, contrainte, ou à clarifier.
    reponses = ((commande.donnees.get("brief") or {}).get("reponses") or {})
    remplis = [k for k, v in reponses.items() if str(v or "").strip()]
    if remplis:
        couverture = _plier(_section(texte, "couverture du brief"))
        if not couverture.strip():
            fautes.append(
                "aucune section « Couverture du brief » dans la synthèse : le "
                "skill fait confirmer que chaque champ du formulaire est traité. "
                f"Champs à couvrir : {', '.join(remplis)}.")
        else:
            oublies = [k for k in remplis if _plier(k) not in couverture]
            if oublies:
                fautes.append(
                    "la section « Couverture du brief » ne cite pas ces champs du "
                    f"formulaire : {', '.join(oublies)}. Chacun doit dire ce qu'il "
                    "est devenu : exploité, contrainte, ou à clarifier.")
    return fautes


def lu(commande: Commande, note: str) -> int:
    source = chemin_skill()
    if source is None:
        print("REFUS  -  skill introuvable.")
        return 1
    note = " ".join(note.split())
    if len(note) < NOTE_MINIMUM:
        print(f"REFUS  -  note trop courte ({len(note)} caractères, minimum "
              f"{NOTE_MINIMUM}). Écrire ce que les sections lues changent pour "
              f"CETTE commande, sinon la consignation ne vaut rien.")
        return 1

    _ecrire(commande, {
        "empreinte": empreinte(source),
        "octets": source.stat().st_size,
        "note": note,
        "date": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    })
    commande.tracer("skill_lu", empreinte=empreinte(source),
                    octets=source.stat().st_size)
    print(f"skill consigné comme lu ({source.stat().st_size} octets, "
          f"empreinte {empreinte(source)}).")
    return 0


def etat(commande: Commande) -> int:
    source = chemin_skill()
    registre = _registre(commande)
    print(f"skill       : {source if source else 'INTROUVABLE'}")
    if source:
        print(f"              {source.stat().st_size} octets, "
              f"empreinte {empreinte(source)}")
    if registre:
        print(f"lu le       : {registre.get('date')}")
        print(f"empreinte   : {registre.get('empreinte')}")
        print(f"note        : {registre.get('note', '')[:160]}")
    else:
        print("lu          : JAMAIS pour cette commande")
    strategie = chemin_strategie(commande)
    if not strategie.exists():
        print("stratégie   : ABSENTE")
        return 0
    manques = _contenu_strategie(commande, strategie.read_text(encoding="utf-8"))
    if manques:
        print(f"stratégie   : {strategie.stat().st_size} octets, INCOMPLÈTE")
        for m in manques:
            print(f"              {m}")
    else:
        print(f"stratégie   : ok, {strategie.stat().st_size} octets, rubriques et couverture du brief en place")
    return 0


def exiger(commande: Commande) -> int:
    fautes = verifier(commande)
    if not fautes:
        print("OK  -  skill lu pour cette commande, synthèse stratégique en place.")
        return 0
    print("REFUS  -  la règle zéro n'est pas tenue.")
    for f in fautes:
        print(f"  {f}")
    return 1


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sous = a.add_subparsers(dest="commande", required=True)

    p = sous.add_parser("lu", help="Consigner la lecture intégrale du skill")
    p.add_argument("ardoise")
    p.add_argument("--note", required=True,
                   help="ce que les sections lues changent pour cette commande")

    p = sous.add_parser("exiger", help="Gate : skill lu et synthèse écrite")
    p.add_argument("ardoise")

    p = sous.add_parser("etat", help="Où en est la lecture du skill")
    p.add_argument("ardoise")

    args = a.parse_args()
    commande = Commande.charger(args.ardoise)
    if args.commande == "lu":
        return lu(commande, args.note)
    if args.commande == "etat":
        return etat(commande)
    return exiger(commande)


if __name__ == "__main__":
    raise SystemExit(main())
