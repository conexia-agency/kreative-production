#!/usr/bin/env python3
"""relecture.py : le registre des verdicts de relecture, une créa à la fois.

**Pourquoi ce module existe.** C1 demandait à un programme de reconnaissance de
caractères de répondre à une question qui n'est pas de son ressort : « le texte
est-il correctement peint ? ». Mesuré le 19/09 sur les masters du client B, tesseract
rendait une bulle noire sur violet vide, inventait « caloul » sur du manuscrit et
« SEAT » sur une liste de noms. Trois dérogations sur quatre venaient du moteur,
pas des créas. Apple Vision lisait tout, mais seulement sur un Mac.

Le fond du problème n'était pas le moteur. Les fautes réellement constatées ne
sont pas des écarts de mots : une police peinte en clair devant un nom
(« DM Sans: »), un mot de liaison peint dans une pastille (« puis »), une
étiquette de flacon réinventée avec un format 80 ml qui n'existe pas au
catalogue. Aucun comparateur de chaînes ne voit ces trois là, parce que les
reconnaître demande de savoir ce qui aurait dû se trouver là. Lire, ici, c'est
juger.

**Ce que ce module fait, et ce qu'il ne fait pas.** Il ne lit pas les images :
`loupe.py` fournit les pixels, la session fournit le jugement. Il consigne ce
jugement, créa par créa, et il REFUSE la suite tant qu'une créa rendue n'a pas
le sien. C'est le seul point mécanique de l'affaire, et il suffit : une étape
sautée devient détectable et bloquante au lieu de passer inaperçue.

**La limite, dite franchement.** Comme `banque.py lue`, un verdict est une
déclaration, pas une preuve : rien ici ne démontre que les zones ont réellement
été ouvertes. Le registre attrape l'oubli, pas le mensonge. Une chose est
vérifiée pour de bon, en revanche : l'empreinte du master au moment du jugement.
Une créa régénérée après son verdict repasse automatiquement en « à relire », ce
qui ferme le seul trou qui se referme mécaniquement.

**La grille vient du skill, pas de moi.** `zones` affiche les garde-fous de
`skill/strategie-creative.md` qui se vérifient sur un rendu, et pose la source
de chaque référence en face du master : un repaint est invisible sur le master
seul, il saute aux yeux contre l'original. Un refus doit citer la règle
enfreinte, et toute créa partie avec une référence doit trancher la fidélité de
son asset. Le reste du jugement reste libre, parce qu'il est libre.

Usage :
    python3 pipeline/relecture.py zones <ardoise>
    python3 pipeline/relecture.py zones <ardoise> --creas c03
    python3 pipeline/relecture.py verdict <ardoise> c03 --etat ok \\
        --asset conforme \\
        --constat "quatre zones lues, photo identique à la source, copy conforme"
    python3 pipeline/relecture.py verdict <ardoise> c07 --etat refus \\
        --garde-fou VIDE \\
        --constat "trois polaroïds sur quatre sont des aplats gris"
    python3 pipeline/relecture.py exiger <ardoise>

Cible Python 3.9+. Aucune dépendance.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

from etat import Commande, Crea  # noqa: E402
from loupe import ZONES  # noqa: E402

REGISTRE = "relecture.json"

# Un constat plus court que ça est une case cochée, pas une relecture. Le
# 19/09 a montré ce que vaut une liste de contrôle déclarative : cocher ne
# prouve rien, et c'est la formulation de ce qui a été vu qui oblige à regarder.
CONSTAT_MINIMUM = 30

ETATS = ("ok", "refus")

# Les garde-fous du skill qui se vérifient sur le MASTER RENDU, avec leur ligne
# dans `skill/strategie-creative.md`. Le skill les liste sous « à vérifier sur
# chaque créa », mais son format de sortie les fait cocher dans le PLAN, donc
# avant que l'image existe : on coche des créas qui ne sont pas générées. Ils
# sont repris ici pour être posés au seul endroit où ils sont vérifiables.
# Un refus doit en citer un : nommer la règle enfreinte évite le « je le sens
# pas » qui ne se transmet pas et qui ne se corrige pas.
GARDE_FOUS = {
    "ASSET": "adapter n'est pas modifier : l'asset du client est-il celui de la "
             "source, ou une variante redessinée ? (skill l.184 et 359)",
    "VIDE": "mockup ou cadre vide, faux texte, texte semi-lisible : le tell IA "
            "numéro un (skill l.117 et 199)",
    "FOCAL": "une seule idée, un seul point focal, lisible en vignette "
             "(skill l.128 à 130 et 355)",
    "LAYOUT": "zones qui respirent, CTA détaché, sous-titre non collé, aucun "
              "empilement de texte (skill l.131 et 356)",
    "MATIERE": "aucun aplat nu ni fond sombre avec lueur centrée, de la "
               "profondeur et de la matière (skill l.119 et 357)",
    "CLONE": "aucune paire clonable dans le pack, architecture qui varie "
             "(skill l.116, 132 et 354)",
    "TEXTE": "le texte peint est-il exactement celui du plan, accents compris, "
             "sans nom de police ni mot de liaison peint",
    "SCENE": "client agence, SaaS ou service : aucune scène photographique "
             "générée, ce qui existe est photographié et joint (skill l.206)",
}

# Verdict d'asset, exigé dès que la créa part avec des références. C'est le
# défaut qui a coûté le pack du client B du 18/09 : trois créas sur trois avec
# référence jointe et présente sont revenues repeintes, et le test mesuré du
# 01/09 (`tests/fidelite-nano-banana`) l'avait annoncé, logo redessiné 4 fois
# sur 4. Une case libre ne suffit pas là-dessus, la question se pose en face.
ASSETS = ("conforme", "repeint", "absent")


# ---------------------------------------------------------------------------
# Le disque
# ---------------------------------------------------------------------------

def _ardoise(commande: Commande) -> str:
    """Le slug de la commande, tel qu'il s'écrit sur la ligne de commande."""
    return commande.donnees.get("ardoise") or commande.dossier.name


def _chemin_registre(commande: Commande) -> Path:
    return commande.dossier / REGISTRE


def lire_registre(commande: Commande) -> dict:
    """Le registre tel qu'il est sur le disque, vide s'il n'existe pas encore."""
    chemin = _chemin_registre(commande)
    if not chemin.exists():
        return {}
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _ecrire_registre(commande: Commande, registre: dict) -> None:
    _chemin_registre(commande).write_text(
        json.dumps(registre, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _empreinte(chemin: Path) -> Optional[str]:
    """Taille et date de modification du master, pour repérer une régénération.

    Un verdict porte sur l'image qui était là quand la session l'a regardée. Si
    la créa repart en génération, l'ancien verdict ne vaut plus rien : il parle
    d'une image qui n'existe plus.
    """
    try:
        etat = chemin.stat()
    except OSError:
        return None
    return f"{etat.st_size}-{etat.st_mtime_ns}"


# ---------------------------------------------------------------------------
# L'état d'une créa
# ---------------------------------------------------------------------------

def _creas_a_relire(commande: Commande) -> List[Crea]:
    return [c for c in commande.creas()
            if c.etat in ("master_ok", "composee", "retenue") and c.master]


def _zones_attendues(commande: Commande, crea: Crea) -> Tuple[List[Path], List[str]]:
    """Les fichiers de zone de cette créa : ceux qui existent, ceux qui manquent."""
    dossier = commande.dossier / "session" / "loupe"
    souche = Path(crea.master).stem if crea.master else crea.identifiant
    presentes: List[Path] = []
    absentes: List[str] = []
    for zone in ZONES:
        nom = f"{souche}-{zone}.png"
        chemin = dossier / nom
        if chemin.exists():
            presentes.append(chemin)
        else:
            absentes.append(nom)
    return presentes, absentes


def _sources(commande: Commande, crea: Crea) -> List[Path]:
    """Les références de la créa qui existent sur le disque, à ouvrir en face.

    On prend `references_jointes` quand elle est renseignée, parce qu'elle dit
    ce qui a RÉELLEMENT été envoyé ; `prompt.references` ne dit que ce qui était
    demandé, et l'écart entre les deux est précisément ce qu'on cherche à voir.
    """
    declarees = list(getattr(crea, "references_jointes", None) or []) \
        or list(crea.prompt.references or [])
    return [commande.dossier / r for r in declarees
            if (commande.dossier / r).exists()]


def etat_crea(commande: Commande, crea: Crea, registre: dict) -> Dict[str, object]:
    """Où en est la relecture de cette créa : à relire, périmée, ou jugée."""
    entree = registre.get(crea.identifiant) or {}
    master = commande.dossier / crea.master if crea.master else None
    empreinte = _empreinte(master) if master else None

    if not entree.get("verdict"):
        situation = "a_relire"
    elif entree.get("empreinte") and empreinte and entree["empreinte"] != empreinte:
        situation = "perimee"
    else:
        situation = "jugee"

    return {
        "crea": crea.identifiant,
        "situation": situation,
        "verdict": entree.get("verdict"),
        "garde_fou": entree.get("garde_fou"),
        "asset": entree.get("asset"),
        "constat": entree.get("constat"),
        "date": entree.get("date"),
    }


# ---------------------------------------------------------------------------
# Les sous-commandes
# ---------------------------------------------------------------------------

def zones(commande: Commande, creas: Optional[List[str]] = None) -> int:
    """Dire quoi ouvrir, dans quel ordre, et ce qui reste à juger."""
    a_relire = _creas_a_relire(commande)
    if creas:
        a_relire = [c for c in a_relire if c.identifiant in creas]
    if not a_relire:
        print("aucune créa rendue à relire.")
        return 0

    registre = lire_registre(commande)
    manque_des_zones = False
    for crea in a_relire:
        etat = etat_crea(commande, crea, registre)
        presentes, absentes = _zones_attendues(commande, crea)
        marque = {"jugee": "jugée", "perimee": "PÉRIMÉE (master régénéré)",
                  "a_relire": "à relire"}[str(etat["situation"])]
        print(f"\n{crea.identifiant}  -  {marque}")
        if etat["situation"] == "jugee":
            print(f"  verdict {etat['verdict']} le {etat['date']}")
            print(f"  {etat['constat']}")
            continue
        if absentes:
            manque_des_zones = True
            print(f"  zones absentes : {', '.join(absentes)}")
            print(f"  produire d'abord : python3 pipeline/loupe.py {_ardoise(commande)} "
                  f"--creas {crea.identifiant}")
        for chemin in presentes:
            print(f"  ouvrir  {chemin}")

        # La source EN FACE du master. Un repaint est invisible sur le master
        # seul : on ne peut y juger que « ça a l'air bien ». Il saute aux yeux
        # contre l'original. c11 du pack du client B n'a été prouvé que comme ça.
        for source in _sources(commande, crea):
            print(f"  COMPARER à la source  {source}")

    print("\nOuvrir chaque zone une par une, avec Read. Tu ne transcris pas, tu juges.")
    print("La grille, garde-fous du skill vérifiables sur le rendu :")
    for code, texte in GARDE_FOUS.items():
        print(f"  {code:8} {texte}")
    print("\nPuis consigner, par créa :")
    print(f"  python3 pipeline/relecture.py verdict {_ardoise(commande)} <crea> "
          f"--etat ok --constat \"ce qui a été vu\" [--asset conforme|repeint|absent]")
    print(f"  python3 pipeline/relecture.py verdict {_ardoise(commande)} <crea> "
          f"--etat refus --garde-fou {'|'.join(list(GARDE_FOUS)[:3])}|... --constat \"...\"")
    return 1 if manque_des_zones else 0


def verdict(commande: Commande, crea_id: str, etat: str, constat: str,
            garde_fou: Optional[str] = None, asset: Optional[str] = None) -> int:
    """Consigner le jugement de la session sur une créa."""
    if etat not in ETATS:
        print(f"REFUS  -  état inconnu : {etat}. Attendu : {' ou '.join(ETATS)}.")
        return 1

    if etat == "refus":
        if not garde_fou:
            print("REFUS  -  un refus cite la règle enfreinte : --garde-fou parmi "
                  + ", ".join(GARDE_FOUS) + ".")
            print("          Un refus qui ne nomme pas sa règle ne se transmet pas "
                  "et ne se corrige pas.")
            return 1
        garde_fou = garde_fou.upper()
        if garde_fou not in GARDE_FOUS:
            print(f"REFUS  -  garde-fou inconnu : {garde_fou}. Connus : "
                  + ", ".join(GARDE_FOUS) + ".")
            return 1

    constat = " ".join(constat.split())
    if len(constat) < CONSTAT_MINIMUM:
        print(f"REFUS  -  constat trop court ({len(constat)} caractères, minimum "
              f"{CONSTAT_MINIMUM}). Un verdict sans constat est une case cochée : "
              f"écrire ce qui a été lu, et sur quelle zone.")
        return 1

    try:
        crea = commande.lire_crea(crea_id)
    except Exception:
        print(f"REFUS  -  créa inconnue dans cette commande : {crea_id}")
        return 1

    if not crea.master:
        print(f"REFUS  -  {crea_id} n'a pas de master rendu : rien à relire.")
        return 1

    master = commande.dossier / crea.master
    empreinte = _empreinte(master)
    if empreinte is None:
        print(f"REFUS  -  master déclaré mais absent du disque : {crea.master}")
        return 1

    _, absentes = _zones_attendues(commande, crea)
    if absentes:
        print(f"REFUS  -  zones de loupe absentes pour {crea_id} : "
              f"{', '.join(absentes)}")
        print(f"          python3 pipeline/loupe.py {_ardoise(commande)} --creas {crea_id}")
        return 1

    # Dès qu'une référence est partie avec la créa, la question de la fidélité
    # se pose en face et ne se noie pas dans un constat libre.
    sources = _sources(commande, crea)
    if sources:
        if not asset:
            print(f"REFUS  -  {crea_id} est partie avec {len(sources)} référence(s) : "
                  f"--asset conforme|repeint|absent est obligatoire.")
            for s in sources:
                print(f"          comparer au master : {s}")
            return 1
        asset = asset.lower()
        if asset not in ASSETS:
            print(f"REFUS  -  valeur d'asset inconnue : {asset}. Attendu : "
                  + ", ".join(ASSETS) + ".")
            return 1
        # Un asset du client redessiné par le modèle est une contrefaçon
        # diffusée sous son nom. Ça ne se valide pas, quel que soit le reste
        # de la créa : le test du 01/09 est formel là-dessus.
        if asset == "repeint" and etat == "ok":
            print(f"REFUS  -  contradiction : l'asset est déclaré repeint et la créa "
                  f"validée. Un asset d'identité redessiné est une contrefaçon "
                  f"diffusée sous le nom du client. Passer --etat refus "
                  f"--garde-fou ASSET.")
            return 1
    elif asset:
        print(f"REFUS  -  {crea_id} n'a aucune référence : --asset n'a pas de sens ici.")
        return 1

    registre = lire_registre(commande)
    registre[crea_id] = {
        "verdict": etat,
        "garde_fou": garde_fou,
        "asset": asset,
        "constat": constat,
        "date": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "empreinte": empreinte,
        "zones": list(ZONES),
        "sources_comparees": [str(s.relative_to(commande.dossier)) for s in sources],
    }
    _ecrire_registre(commande, registre)
    commande.tracer("relecture", crea=crea_id, verdict=etat)
    print(f"{crea_id} : verdict {etat} consigné.")
    if etat == "refus":
        print("  la créa est à reprendre : python3 pipeline/etat.py "
              f"reprise-visuel {_ardoise(commande)} {crea_id}")
    return 0


def exiger(commande: Commande) -> int:
    """0 si chaque créa rendue porte un verdict valable, 1 sinon."""
    a_relire = _creas_a_relire(commande)
    if not a_relire:
        print("OK  -  aucune créa rendue, rien à relire.")
        return 0

    registre = lire_registre(commande)
    etats = [etat_crea(commande, crea, registre) for crea in a_relire]
    manquantes = [e for e in etats if e["situation"] == "a_relire"]
    perimees = [e for e in etats if e["situation"] == "perimee"]
    refusees = [e for e in etats if e["situation"] == "jugee" and e["verdict"] == "refus"]

    if not manquantes and not perimees and not refusees:
        print(f"OK  -  {len(etats)} créa(s) relue(s) et jugée(s) conformes.")
        return 0

    print("REFUS  -  la relecture n'est pas close.")
    for e in manquantes:
        print(f"  {e['crea']} : jamais relue")
    for e in perimees:
        print(f"  {e['crea']} : verdict périmé, le master a été régénéré depuis")
    for e in refusees:
        print(f"  {e['crea']} : refusée à la relecture [{e.get('garde_fou') or '?'}]. "
              f"{e['constat']}")
    print(f"\n  python3 pipeline/relecture.py zones {_ardoise(commande)}")
    return 1


# ---------------------------------------------------------------------------

def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sous = a.add_subparsers(dest="commande", required=True)

    p = sous.add_parser("zones", help="Ce qu'il reste à ouvrir et à juger")
    p.add_argument("ardoise")
    p.add_argument("--creas", nargs="*", help="limiter à ces créas")

    p = sous.add_parser("verdict", help="Consigner le jugement sur une créa")
    p.add_argument("ardoise")
    p.add_argument("crea")
    p.add_argument("--etat", required=True, choices=list(ETATS))
    p.add_argument("--constat", required=True, help="ce qui a été vu, et sur quelle zone")
    p.add_argument("--garde-fou", dest="garde_fou",
                   help="la règle enfreinte, obligatoire sur un refus : "
                        + ", ".join(GARDE_FOUS))
    p.add_argument("--asset", choices=list(ASSETS),
                   help="fidélité de l'asset du client, obligatoire dès que la "
                        "créa est partie avec une référence")

    p = sous.add_parser("exiger", help="Gate : toute créa rendue porte un verdict")
    p.add_argument("ardoise")

    args = a.parse_args()
    commande = Commande.charger(args.ardoise)

    if args.commande == "zones":
        return zones(commande, args.creas)
    if args.commande == "verdict":
        return verdict(commande, args.crea, args.etat, args.constat,
                       args.garde_fou, args.asset)
    return exiger(commande)


if __name__ == "__main__":
    raise SystemExit(main())
