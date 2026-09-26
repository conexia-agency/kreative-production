#!/usr/bin/env python3
"""audit.py : cinq contrôles mécaniques sur ce que le modèle a rendu.

Règle de conception : **aucun contrôle ne demande de jugement, et aucun ne porte
une règle de création.** Chacun se calcule, se prouve, cite sa pièce, et renvoie
soit à une règle écrite dans le skill de Kreative, soit à un fait vérifiable du
fichier produit. Juger si une créa est bonne n'appartient pas à ce fichier.

Trois contrôles ont été retirés le 18/09 : la répétition de gabarit, le
contraste de palette et le débordement de texte. Tous les trois mesuraient la
chaîne composée en HTML, avec notre répertoire d'archétypes et notre
compositeur. Le texte est désormais peint par le modèle et la création vient du
skill de Kreative : ces trois contrôles jugeaient un objet qui n'existe plus.

Les cinq qui restent :

  C1 copy peinte      Toute créa rendue porte le verdict de sa relecture. La
                      lecture elle-même appartient à la session (`loupe.py`
                      pour les pixels, `relecture.py` pour le registre) : lire
                      un texte peint, c'est juger, et ce fichier ne juge pas.
  C2 doublon visuel   Deux créas visuellement identiques comptent pour une.
                      Le skill l'écrit dans sa propre liste de contrôle :
                      « aucune paire clonable ».
  C3 chiffre sourcé   Tout nombre du copy doit venir du brief. Règle d'or 5 du
                      skill : vérifier chaque chiffre et chaque attribution.
  C4 marqueur         Une créa qui porte [A COMPLETER] ne part pas.
  C5 format du master Le skill impose le carré 1:1 par défaut. Le fichier
                      produit doit l'être.

**Le gate ne bloque pas par défaut.** Le point ouvert 9.3 du cahier des charges
de Kreative demande encore si le pipeline doit rejeter et relancer les visuels
ratés, ou si le tri se fait à l'oeil à la réception. Tant qu'Evan n'a pas
tranché, `audit.py` rapporte et rend 0. `--bloquant` rend 1 sur échec, pour le
jour où la réponse sera oui.

Usage :
    python3 audit.py --marque "Marque Exemple"
    python3 audit.py --marque "Marque Exemple" --bloquant
    python3 audit.py --marque "Marque Exemple" --json

Cible Python 3.9+. Dépendances : Pillow. Plus aucun moteur de reconnaissance de
caractères, ni tesseract ni Apple Vision : C1 lit le registre de `relecture.py`,
ce qui rend le contrôle identique sur un Mac et sur le poste d'un client.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

from etat import Commande, Crea  # noqa: E402
from relecture import (  # noqa: E402
    etat_crea as etat_relecture,
    lire_registre as lire_relecture,
)

SEUIL_SIMILARITE = 0.92    # au delà, deux créas sont le même visuel

# Le format que le skill de Kreative impose : « Le 1:1 (carré) est le format par
# défaut, toujours, tu ne changes de ratio que si le brief l'exige
# explicitement. » On tolère un écart d'un pour cent, une image 2048x2047 reste
# un carré.
TOLERANCE_RATIO = 0.01


@dataclass
class Constat:
    controle: str
    crea: str
    verdict: str        # "ok" | "alerte" | "echec"
    message: str
    preuve: str = ""

    @property
    def bloquant(self) -> bool:
        return self.verdict == "echec"


# ---------------------------------------------------------------------------
# C1 : la copy est-elle réellement peinte dans le master
# ---------------------------------------------------------------------------


def c1_copy_peinte(commande: Commande, crea: Crea) -> Optional[Constat]:
    """Chaque créa rendue porte-t-elle le verdict de sa relecture ?

    **Ce contrôle a changé de nature le 21/09, et c'est une correction, pas un
    renoncement.** Il demandait auparavant à un programme de reconnaissance de
    caractères si la copy était bien peinte, en comparant des listes de mots.
    Deux raisons de l'abandonner, mesurées.

    D'abord le moteur : tesseract rendait vide une bulle noire sur violet clair,
    inventait « caloul » sur du manuscrit et « SEAT » sur une liste de noms
    (19/09, masters du client B). Trois dérogations sur quatre venaient de lui, pas
    des créas. Apple Vision lisait tout, mais seulement là où il y a un Mac.

    Ensuite, et surtout, la question : les fautes réellement constatées ne sont
    pas des écarts de mots. Une police peinte en clair devant un nom
    (« DM Sans: »), un mot de liaison peint dans une pastille (« puis »), une
    étiquette de flacon réinventée avec un format 80 ml absent du catalogue.
    Aucun comparateur de chaînes ne voit ces trois là : les reconnaître demande
    de savoir ce qui aurait dû se trouver là. Lire, ici, c'est juger, et ce
    fichier dit lui-même en tête qu'aucun de ses contrôles ne juge.

    Donc la lecture sort d'ici et revient à la session, avec `loupe.py` pour les
    pixels et `relecture.py` pour le registre. Ce qui reste mécanique, et qui le
    reste entièrement : une créa rendue sans verdict, ou dont le master a été
    régénéré depuis son verdict, ne passe pas.
    """
    if not crea.master:
        return None

    etat = etat_relecture(commande, crea, lire_relecture(commande))
    situation = etat["situation"]

    if situation == "a_relire":
        return Constat(
            "C1 copy peinte", crea.identifiant, "echec",
            "master rendu mais jamais relu. Ouvrir ses zones de loupe une par "
            "une, lire chaque texte peint, puis consigner le verdict.",
            preuve=f"python3 pipeline/relecture.py zones "
                   f"{commande.donnees.get('ardoise') or commande.dossier.name} "
                   f"--creas {crea.identifiant}")

    if situation == "perimee":
        return Constat(
            "C1 copy peinte", crea.identifiant, "echec",
            f"verdict périmé : le master a été régénéré depuis la relecture du "
            f"{etat.get('date')}. L'ancien verdict parle d'une image qui "
            f"n'existe plus, la créa est à relire.",
            preuve=str(etat.get("constat") or "")[:120])

    if etat.get("verdict") == "refus":
        return Constat(
            "C1 copy peinte", crea.identifiant, "echec",
            f"refusée à la relecture du {etat.get('date')} : {etat.get('constat')}",
            preuve=str(crea.master))

    return Constat(
        "C1 copy peinte", crea.identifiant, "ok",
        f"relue et jugée conforme le {etat.get('date')} : {etat.get('constat')}")


# ---------------------------------------------------------------------------
# C2 : doublon visuel
# ---------------------------------------------------------------------------

def _empreinte(chemin: Path) -> Optional[int]:
    """Empreinte perceptuelle 8x8, robuste au recadrage et au changement de teinte."""
    try:
        from PIL import Image
        with Image.open(chemin) as im:
            gris = im.convert("L").resize((9, 8), Image.LANCZOS)
        pixels = list(gris.getdata())
        bits = 0
        for ligne in range(8):
            for col in range(8):
                gauche = pixels[ligne * 9 + col]
                droite = pixels[ligne * 9 + col + 1]
                bits = (bits << 1) | (1 if gauche > droite else 0)
        return bits
    except Exception:
        return None


def c2_doublons(commande: Commande, creas: List[Crea]) -> List[Constat]:
    """Deux masters visuellement identiques comptent pour une créa.

    Le skill de Kreative le pose dans sa propre liste de contrôle : les créas
    d'un pack sont franchement différentes, aucune paire clonable. Ici on ne
    juge pas la différence de concept, seulement la ressemblance des pixels.
    """
    empreintes: Dict[str, int] = {}
    for crea in creas:
        if not crea.master:
            continue
        valeur = _empreinte(commande.dossier / crea.master)
        if valeur is not None:
            empreintes[crea.identifiant] = valeur

    constats: List[Constat] = []
    identifiants = sorted(empreintes)
    for i, a in enumerate(identifiants):
        for b in identifiants[i + 1:]:
            distance = bin(empreintes[a] ^ empreintes[b]).count("1")
            similarite = 1 - distance / 64
            if similarite < SEUIL_SIMILARITE:
                continue
            constats.append(Constat(
                "C2 doublon visuel", a, "echec",
                f"{a} et {b} sont visuellement identiques à {similarite:.0%}. "
                f"Dans un pack, cela compte pour une seule créa.",
                preuve=f"distance de Hamming {distance}/64"))
    return constats or [Constat("C2 doublon visuel", "pack", "ok",
                                f"{len(empreintes)} créas comparées, aucune paire identique")]


# ---------------------------------------------------------------------------
# C3 : chiffre non sourcé
# ---------------------------------------------------------------------------

def c3_chiffres(commande: Commande, crea: Crea) -> Optional[Constat]:
    """Tout nombre du copy doit se retrouver dans le brief.

    Règle d'or 5 du skill de Kreative : vérifier chaque chiffre et chaque
    attribution, pas de promesse chiffrée non vérifiable. Les nombres écrits en
    toutes lettres et les nombres d'un seul chiffre ne sont pas contrôlés : ils
    sont presque toujours grammaticaux, pas factuels.
    """
    brief = commande.donnees.get("brief") or {}
    source = json.dumps(brief, ensure_ascii=False)
    autorises = set(re.findall(r"\d[\d\s.,]*", source))
    autorises = {a.replace(" ", "").replace(",", ".").rstrip(".") for a in autorises}

    copy = " ".join([crea.copy.accroche, crea.copy.sous_accroche, crea.copy.badge])
    trouves = re.findall(r"\d[\d\s.,]*", copy)
    orphelins = []
    for brut in trouves:
        valeur = brut.replace(" ", "").replace(",", ".").rstrip(".")
        if len(valeur) < 2:
            continue
        if not any(valeur in a or a in valeur for a in autorises):
            orphelins.append(brut.strip())
    if not orphelins:
        return Constat("C3 chiffre sourcé", crea.identifiant, "ok",
                       "tous les chiffres du copy viennent du brief")
    return Constat("C3 chiffre sourcé", crea.identifiant, "echec",
                   f"chiffre absent du brief : {', '.join(orphelins)}. "
                   f"Un chiffre inventé est une faute, pas une approximation.",
                   preuve=copy[:140])


# ---------------------------------------------------------------------------
# C4 : marqueur à compléter
# ---------------------------------------------------------------------------

def c4_marqueurs(crea: Crea) -> Constat:
    champs = crea.copy.accroche + crea.copy.sous_accroche + crea.copy.badge
    manquants = re.findall(r"\[A COMPLETER: ([\w.]+)\]", champs)
    if not manquants:
        return Constat("C4 marqueur", crea.identifiant, "ok", "aucun champ à compléter")
    return Constat("C4 marqueur", crea.identifiant, "echec",
                   f"brief incomplet : {', '.join(sorted(set(manquants)))}",
                   preuve=champs[:140])


# ---------------------------------------------------------------------------
# C5 : le master est bien au format demandé
# ---------------------------------------------------------------------------

def c5_format(commande: Commande, crea: Crea) -> Optional[Constat]:
    """Le master respecte le ratio que le skill impose.

    Le contrôle porte sur le fichier, pas sur l'intention : un modèle rend
    parfois un 1:1 demandé en 4:5 réel, et personne ne s'en aperçoit avant que
    la créa soit coupée dans le feed.
    """
    if not crea.master:
        return None
    chemin = commande.dossier / crea.master
    if not chemin.exists():
        return Constat("C5 format du master", crea.identifiant, "echec",
                       f"master déclaré mais absent du disque : {crea.master}")
    try:
        from PIL import Image
        with Image.open(chemin) as im:
            largeur, hauteur = im.size
    except Exception as erreur:
        return Constat("C5 format du master", crea.identifiant, "alerte",
                       f"image illisible : {erreur}")

    ratio = largeur / hauteur if hauteur else 0
    if abs(ratio - 1.0) <= TOLERANCE_RATIO:
        return Constat("C5 format du master", crea.identifiant, "ok",
                       f"carré, {largeur}x{hauteur}")
    return Constat("C5 format du master", crea.identifiant, "echec",
                   f"le master n'est pas carré : {largeur}x{hauteur}, ratio "
                   f"{ratio:.2f}. Le skill impose le 1:1 par défaut.",
                   preuve=str(chemin.name))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _derogations(commande: Commande) -> dict:
    """Les échecs couverts par une vérification humaine consignée.

    Un contrôle mécanique peut se tromper : tesseract ne lit pas un texte
    incliné (mesuré le 18/09 sur c09, texte exact à l'oeil en pleine
    résolution, rappel OCR à 45%). Baisser le seuil couvrirait aussi les vrais
    défauts ; la sortie honnête est la dérogation NOMINATIVE : un humain a
    regardé le master, l'écrit dans `audit-derogations.json`, et l'audit
    convertit ce seul échec en alerte en citant le motif. Le fichier vit dans
    le dossier de la commande, versionné avec elle.

    Format : {"c09": {"C1 copy peinte": {"date": "...", "verifie_par": "...",
    "motif": "..."}}}. Une dérogation sans motif est ignorée.
    """
    chemin = commande.dossier / "audit-derogations.json"
    if not chemin.exists():
        return {}
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def auditer(commande: Commande) -> List[Constat]:
    creas = [c for c in commande.creas() if c.etat in ("master_ok", "composee", "retenue")]
    constats: List[Constat] = []
    for crea in creas:
        for constat in (c1_copy_peinte(commande, crea), c3_chiffres(commande, crea),
                        c4_marqueurs(crea), c5_format(commande, crea)):
            if constat:
                constats.append(constat)
    constats += c2_doublons(commande, creas)

    derogations = _derogations(commande)
    for constat in constats:
        derog = (derogations.get(constat.crea) or {}).get(constat.controle) or {}
        if constat.verdict == "echec" and derog.get("motif"):
            constat.verdict = "alerte"
            constat.message = (
                f"échec couvert par dérogation consignée du {derog.get('date', '?')} "
                f"({derog.get('verifie_par', 'vérificateur non nommé')}) : "
                f"{derog['motif']} Message du contrôle : {constat.message}")
    return constats


def rapport(constats: List[Constat], bloquant: bool = False) -> str:
    echecs = [c for c in constats if c.verdict == "echec"]
    alertes = [c for c in constats if c.verdict == "alerte"]
    lignes = []
    for constat in echecs + alertes:
        marque = "ECHEC " if constat.bloquant else "ALERTE"
        lignes.append(f"  [{marque}] {constat.controle} / {constat.crea}")
        lignes.append(f"           {constat.message}")
        if constat.preuve:
            lignes.append(f"           preuve : {constat.preuve}")
    entete = (f"{len(constats)} contrôles, {len(echecs)} échec(s), "
              f"{len(alertes)} alerte(s).")
    if not echecs:
        verdict = "Aucun échec."
    elif bloquant:
        verdict = "GATE BLOQUE : la commande ne part pas."
    else:
        verdict = ("Le gate ne bloque pas : point ouvert 9.3 du cahier des charges, "
                   "en attente de la réponse de Kreative. Relancer avec --bloquant "
                   "pour qu'un échec arrête la commande.")
    return "\n".join([entete, ""] + lignes + ["", verdict])


def main() -> int:
    parseur = argparse.ArgumentParser(description="Contrôles mécaniques d'une commande")
    parseur.add_argument("--marque", required=True)
    parseur.add_argument("--json", action="store_true")
    parseur.add_argument("--bloquant", action="store_true",
                         help="rendre 1 en cas d'échec, pour enchaîner dans un script")
    arguments = parseur.parse_args()

    commande = Commande.charger(arguments.marque)
    constats = auditer(commande)
    if arguments.json:
        print(json.dumps([asdict(c) for c in constats], ensure_ascii=False, indent=1))
    else:
        print(rapport(constats, bloquant=arguments.bloquant))
    commande.tracer("audit", echecs=sum(1 for c in constats if c.bloquant),
                    controles=len(constats), bloquant=arguments.bloquant)
    return 1 if arguments.bloquant and any(c.bloquant for c in constats) else 0


if __name__ == "__main__":
    raise SystemExit(main())
