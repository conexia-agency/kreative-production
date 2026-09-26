#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sortie.py : le document que le skill de Kreative appelle son « Format de sortie ».

**Pourquoi ce module existe.** Le skill décrit sa sortie, « à respecter
exactement » : 1. Synthèse stratégique, 2. Angles retenus, 3. Les créatives
(titre, sous-titre, texte additionnel, CTA, assets à joindre, prompt de
génération), 4. Garde-fous. Mesuré le 26/09 : la chaîne livrait les images et
un lisez-moi, jamais ce document. Kreative ne recevait ni la stratégie, ni les
prompts, ni la checklist cochée. Décision de l'équipe le 26/09 : il part avec le pack.

**D'où vient chaque section.** Rien n'est réécrit ici.
- 1, 2 et 4 : les sections de `strategie-creative.md`, écrites par la session,
  reprises telles quelles. Leur titre doit contenir « synthèse stratégique »,
  « angles » et « garde-fous ».
- 3 : les fiches `creas/cNN.json`, groupées par angle, prompt compris à
  l'octet près : c'est ce qui est parti au modèle.
- En fin : « Ce qui a manqué » et « Couverture du brief », comme le skill les
  demande.

Le tiret cadratin que le format du skill emploie pour un champ vide s'écrit
ici « aucun » : la règle d'écriture de Conexia s'applique à ce que la chaîne
produit.

Usage :
    python3 pipeline/sortie.py assembler <ardoise>

Écrit `sortie-strategie.md` dans la commande ; `livrer.py` le joint au pack.

Cible Python 3.9+. Aucune dépendance.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

from etat import Commande  # noqa: E402
import skill as module_skill  # noqa: E402

FICHIER = "sortie-strategie.md"
SECTIONS = (("synthese strategique", "## 1. Synthèse stratégique"),
            ("angles", "## 2. Angles retenus"),
            ("garde-fous", "## 4. Garde-fous"))


def _vide(valeur: str) -> str:
    return valeur.strip() if (valeur or "").strip() else "aucun"


def assembler(commande: Commande) -> Tuple[Path, List[str]]:
    """(chemin écrit, manquements). Rien n'est écrit s'il manque une section."""
    strategie = module_skill.chemin_strategie(commande)
    if not strategie.exists():
        return strategie, ["strategie-creative.md absent de la commande"]
    texte = strategie.read_text(encoding="utf-8")

    corps: Dict[str, str] = {}
    manques: List[str] = []
    for cle, titre in SECTIONS:
        section = module_skill._section(texte, cle).strip()
        if not section:
            manques.append(f"strategie-creative.md n'a pas de section dont le titre "
                           f"contient « {cle} » (attendue : {titre[3:]})")
        corps[cle] = section
    creas = [c for c in commande.creas() if (c.prompt.scene or "").strip()]
    if not creas:
        manques.append("aucune créa planifiée")
    if manques:
        return commande.dossier / FICHIER, manques

    par_angle: Dict[str, list] = {}
    for c in creas:
        par_angle.setdefault(c.angle or "sans angle", []).append(c)

    marque = commande.donnees.get("marque") or commande.donnees.get("ardoise")
    lignes = [f"# {marque} : sortie du skill de stratégie créative", "",
              f"Pack {commande.donnees.get('pack')}, {len(creas)} créas, "
              f"{len(par_angle)} angles.", ""]
    lignes += [SECTIONS[0][1], "", corps["synthese strategique"], ""]
    lignes += [SECTIONS[1][1], "", corps["angles"], ""]
    lignes += ["## 3. Les créatives", ""]
    for rang, (angle, groupe) in enumerate(par_angle.items(), start=1):
        lignes += [f"### Angle {rang} : {angle}", ""]
        for c in groupe:
            lignes += [
                f"**Créa {c.identifiant}**",
                f"- Titre (headline) : {_vide(c.copy.accroche)}",
                f"- Sous-titre : {_vide(c.copy.sous_accroche)}",
                f"- Texte additionnel : {_vide(c.copy.badge)}",
                f"- CTA : {c.copy.cta.strip() if c.copy.cta.strip() else 'aucun (délibéré)'}",
                f"- Structure reprise de : {_vide(getattr(c, 'structure', ''))}",
                f"- Assets à joindre : {', '.join(c.prompt.references) or 'aucun'}",
                f"- Prompt de génération : « {c.prompt.scene.strip()} »",
                "",
            ]
    lignes += [SECTIONS[2][1], "", corps["garde-fous"], ""]

    manque = commande.donnees.get("ce_qui_a_manque") or []
    lignes += ["## Ce qui a manqué", ""]
    lignes += [f"- {m}" for m in manque] if manque else ["- rien"]
    lignes.append("")
    couverture = module_skill._section(texte, "couverture du brief").strip()
    if couverture:
        lignes += ["## Couverture du brief", "", couverture, ""]

    sortie = "\n".join(lignes).replace(chr(0x2014), ",")
    chemin = commande.dossier / FICHIER
    chemin.write_text(sortie, encoding="utf-8")
    commande.tracer("sortie_assemblee", creas=len(creas), angles=len(par_angle))
    return chemin, []


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = a.add_subparsers(dest="commande", required=True)
    p = sous.add_parser("assembler", help="Écrire sortie-strategie.md")
    p.add_argument("ardoise")
    args = a.parse_args()
    commande = Commande.charger(args.ardoise)
    chemin, manques = assembler(commande)
    if manques:
        print("REFUS  -  sortie non assemblée :")
        for m in manques:
            print(f"  {m}")
        return 1
    print(f"Sortie écrite : {chemin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
