#!/usr/bin/env python3
"""parcours.py : une seule prochaine etape, decidee par le disque.

Le skill et la banque existent deja. Ce qui casse les packs, c'est une session
qui ecrit la strategie ou genere sans avoir ouvert la banque. Ce module ne
remplace aucune regle : il dit, a chaque appel, LA seule commande autorisee,
et refuse tout le reste.

    python3 pipeline/parcours.py suivant <ardoise>
    python3 pipeline/parcours.py statut <ardoise>
    python3 pipeline/parcours.py exiger <ardoise> --avant strategie|plan|generer

`exiger` rend 0 si le disque autorise l'etape, 1 sinon, avec le remede.
C'est le verrou a appeler avant d'ecrire un plan.md ou d'appeler le MCP.

Cible Python 3.9+. Aucune dependance externe.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

from etat import Commande  # noqa: E402
import banque as module_banque  # noqa: E402
import metaads as module_metaads  # noqa: E402
import outillage as module_outillage  # noqa: E402


def _existe(chemin: Path) -> bool:
    return chemin.exists()


def _lire_json(chemin: Path) -> Optional[dict]:
    if not chemin.exists():
        return None
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _evenements(dossier: Path) -> List[dict]:
    """Le journal de la commande, dans l'ordre où il a été écrit."""
    chemin = dossier / "journal.jsonl"
    if not chemin.exists():
        return []
    sortie = []
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        try:
            sortie.append(json.loads(ligne))
        except ValueError:
            continue
    return sortie


def _dernier(evenements: List[dict], noms: Tuple[str, ...]) -> int:
    """Rang du dernier événement portant l'un de ces noms, -1 si aucun."""
    for rang in range(len(evenements) - 1, -1, -1):
        if evenements[rang].get("evenement") in noms:
            return rang
    return -1


PUBLIE_VARIABLES = ("PUBLIE_SITE", "PUBLIE_SUPABASE_URL", "PUBLIE_SUPABASE_ANON_KEY",
                    "PUBLIE_EMAIL", "PUBLIE_PASSWORD")


def fin_de_chaine(commande: Commande) -> Dict[str, object]:
    """Ce qui reste à faire une fois les masters rendus.

    Mesuré le 25/09 sur la page blanche du client A : le parcours s'arrêtait sur
    « audit » et ne proposait jamais la suite. Douze créas validées sont restées
    en 1:1, jamais déclinées, jamais livrées. Chaque étape se lit ici sur le
    disque : les fiches, le registre de relecture et le journal.
    """
    import os
    import relecture as module_relecture

    d = commande.dossier
    creas = commande.creas()
    evenements = _evenements(d)

    a_generer = [c.identifiant for c in creas
                 if (c.prompt.scene or "").strip() and not c.master]

    registre = module_relecture.lire_registre(commande)
    etats = [module_relecture.etat_crea(commande, c, registre)
             for c in module_relecture._creas_a_relire(commande)]
    a_relire = [e["crea"] for e in etats if e["situation"] in ("a_relire", "perimee")]
    refusees = [e["crea"] for e in etats
                if e["situation"] == "jugee" and e["verdict"] == "refus"]

    # L'audit ne compte que s'il est postérieur au dernier master rangé.
    rang_audit = _dernier(evenements, ("audit",))
    audit_ok = (rang_audit > _dernier(evenements, ("master_genere", "lot_recolte"))
                and not evenements[rang_audit].get("echecs"))

    rendues = [c for c in creas if c.master and c.etat in ("master_ok", "composee", "retenue")]
    formats_manquants = [c.identifiant for c in rendues
                         if not (c.rendus.get("4x5") and c.rendus.get("9x16"))]
    etendre = _lire_json(d / "formats" / "a-etendre.json") or {}
    a_etendre = sorted((etendre.get("creas") or {}).keys())

    # Le document de sortie du skill doit être postérieur au dernier plan et
    # au dernier master : sinon il décrit un pack qui n'est plus celui-là.
    sortie_a_jour = (_dernier(evenements, ("sortie_assemblee",))
                     > _dernier(evenements, ("plan_importe", "master_genere", "lot_recolte"))
                     and (d / "sortie-strategie.md").exists())

    rang_livraison = _dernier(evenements, ("dossier_livraison",))
    livree = rang_livraison > _dernier(
        evenements, ("master_genere", "lot_recolte", "crea_declinee", "format_etendu"))

    configuree = all(os.environ.get(n) for n in PUBLIE_VARIABLES)
    rapports = sorted((d / "publication").glob("*/rapports/publication-*.json")) \
        if (d / "publication").is_dir() else []
    horodatage_livraison = evenements[rang_livraison].get("horodatage", "") \
        if rang_livraison >= 0 else ""
    publiee = bool(rapports) and livree and any(
        (_lire_json(r) or {}).get("publie_le", "") >= horodatage_livraison for r in rapports)

    return {
        "a_generer": a_generer,
        "a_relire": a_relire,
        "refusees": refusees,
        "audit_ok": audit_ok,
        "formats_manquants": formats_manquants,
        "a_etendre": a_etendre,
        "sortie_a_jour": sortie_a_jour,
        "livree": livree,
        "publication_configuree": configuree,
        "publiee": publiee,
    }


def inventaire(commande: Commande) -> Dict[str, object]:
    """Ce qui est vraiment sur le disque pour cette commande."""
    d = commande.dossier
    marque = d / "marque"
    session = d / "session"
    banque_etat = _lire_json(session / "banque.json") or {}
    planches_attendues = set(banque_etat.get("planches_attendues") or [])
    planches_lues = set(banque_etat.get("planches_lues") or [])
    retenues = list(banque_etat.get("references_retenues") or [])
    absorbees = banque_etat.get("references_absorbees") or {}
    dossier_refs = session / "references"
    extraits = []
    if dossier_refs.is_dir():
        extraits = sorted(p.stem for p in dossier_refs.glob("*.jpg"))
    creas = sorted((d / "creas").glob("c*.json")) if (d / "creas").is_dir() else []
    masters = sorted((d / "masters").glob("*")) if (d / "masters").is_dir() else []

    # Une fiche n'est un plan que si elle porte un prompt. Mesuré le 25/09 sur
    # la page blanche du client A : zite.py ouvre la commande avec 48 fiches vides,
    # et compter les fichiers suffisait à déclarer « plan importé », donc à
    # autoriser la génération sans stratégie ni prompt.
    def _a_un_prompt(fiche: Path) -> bool:
        try:
            donnees = json.loads(fiche.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return bool(((donnees.get("prompt") or {}).get("scene") or "").strip())

    creas_planifiees = [c for c in creas if _a_un_prompt(c)]

    # Les fiches créas que la commande dit avoir, contre celles du disque.
    #
    # Mesuré le 22/09 sur le client A : la commande déclarait 48 générations,
    # le disque en portait 10. Les 38 autres avaient été déplacées le 19/09
    # dans `session/archive-plan-v3-*/creas/` par un archivage fait à la main,
    # hors de la chaîne, donc sans une ligne au journal. Rien ne l'a signalé
    # pendant trois jours, et les lots suivants ont réutilisé les identifiants
    # survivants, en écrasant leurs masters.
    #
    # Ce n'est pas un contrôle bloquant : archiver est une décision légitime.
    # C'est un écart à porter à l'écran, avec l'endroit où regarder.
    try:
        import skill as module_skill
        skill_fautes = module_skill.verifier(commande)
    except Exception:
        skill_fautes = []

    attendues = commande.donnees.get("quantite_generee") or 0
    archives = sorted(p for p in session.glob("archive-*/creas") if p.is_dir())
    fiches_archivees = sum(len(list(p.glob("c*.json"))) for p in archives)

    return {
        "ardoise": d.name,
        "brief": _existe(d / "brief" / "soumission.json") or _existe(d / "commande.json"),
        "charte": _existe(marque / "charte-site.json"),
        "captures": len(list((marque / "captures").glob("*"))) if (marque / "captures").is_dir() else 0,
        "banque_ouverte": bool(banque_etat),
        "planches_attendues": sorted(planches_attendues),
        "planches_lues": sorted(planches_lues),
        "planches_manquantes": sorted(planches_attendues - planches_lues),
        "references_retenues": retenues,
        "references_extraites": extraits,
        "references_sans_extrait": sorted(set(retenues) - set(extraits)),
        "references_absorbees": sorted(absorbees.keys()) if isinstance(absorbees, dict) else [],
        "references_non_absorbees": sorted(
            set(retenues) - set(absorbees.keys() if isinstance(absorbees, dict) else [])
        ),
        "plan_importe": len(creas_planifiees) > 0,
        "nb_creas": len(creas),
        "skill_fautes": skill_fautes,
        "creas_attendues": attendues,
        "creas_manquantes": max(0, attendues - len(creas)),
        "archives": [str(p.parent.relative_to(d)) for p in archives],
        "fiches_archivees": fiches_archivees,
        "nb_masters": len([m for m in masters if m.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]),
        "manquements_banque": module_banque.verifier(commande) if banque_etat else [
            "banque jamais ouverte"
        ],
        "fin": fin_de_chaine(commande) if creas_planifiees else {},
        "meta_ads": module_metaads.verifier(commande),
        "outillage": module_outillage.etat(commande),
    }


def etape_suivante(inv: Dict[str, object]) -> Tuple[str, str, List[str]]:
    """(code, titre, commandes exactes a executer)."""
    ardoise = inv["ardoise"]

    if not inv["brief"]:
        return (
            "brief",
            "Pas de commande sur le disque",
            [
                "python3 pipeline/zite.py relever --appliquer",
                f"# ou creer la commande a la main, puis : python3 pipeline/parcours.py suivant {ardoise}",
            ],
        )

    if not inv["charte"] and inv["captures"] == 0:
        return (
            "site",
            "Aspirer le site client (recolte + mesure)",
            [f"python3 pipeline/scraper.py aspirer {ardoise}"],
        )

    # Étape 0 du skill : le navigateur, vérifié avant toute analyse. Une
    # commande déjà planifiée n'est pas bloquée après coup.
    if not inv["plan_importe"]:
        if inv.get("outillage") == "indisponible":
            return (
                "interrompu",
                "Navigateur indisponible, analyse visuelle impossible, run interrompu.",
                [
                    "# Le skill s'arrete ici. Rendre le navigateur disponible, puis :",
                    f"python3 pipeline/outillage.py consigner {ardoise} --navigateur ok "
                    f"--capture marque/navigateur/accueil.png",
                ],
            )
        if inv.get("outillage") != "ok":
            return (
                "outillage",
                "Etape 0 du skill : verifier le navigateur sur le site du client",
                [
                    "# Navigateur : navigate_page vers le site, take_screenshot enregistre dans",
                    "# marque/navigateur/accueil.png. S'il ne repond pas, le run s'arrete.",
                    f"python3 pipeline/outillage.py consigner {ardoise} --navigateur ok "
                    f"--capture marque/navigateur/accueil.png",
                    f"# ou : --navigateur indisponible --motif \"...\"",
                ],
            )

    if not inv["banque_ouverte"]:
        return (
            "banque_ouvrir",
            "Ouvrir la banque de references sous registre",
            [f"python3 pipeline/banque.py ouvrir {ardoise}"],
        )

    if inv["planches_manquantes"]:
        manquantes = " ".join(inv["planches_manquantes"])  # type: ignore
        return (
            "banque_lire",
            "Ouvrir TOUTES les planches listees (outil Read), puis consigner",
            [
                "# Read chaque chemin affiche par banque.py ouvrir",
                f"python3 pipeline/banque.py lue {ardoise} --planches {manquantes}",
            ],
        )

    if not inv["references_retenues"]:
        return (
            "banque_retenir",
            "Retenir les references pertinentes (plancher du pack)",
            [
                f"python3 pipeline/banque.py retenir {ardoise} --refs AG1-07 AG2-03 ...",
                "# Remplacer par les vrais ids lus sur les planches",
            ],
        )

    if inv["references_sans_extrait"]:
        return (
            "banque_extraire",
            "Extraire chaque reference en pleine resolution",
            [f"python3 pipeline/banque.py extraire {ardoise}"],
        )

    if inv["references_non_absorbees"]:
        refs = " ".join(inv["references_non_absorbees"])  # type: ignore
        return (
            "banque_absorber",
            "Ouvrir chaque fichier session/references/<ref>.jpg et consigner une phrase",
            [
                "# Read session/references/<ref>.jpg UN PAR UN",
                f'python3 pipeline/banque.py absorber {ardoise} --ref AG1-07 --vu "layout hero produit + claim haut + CTA bas"',
                f"# Repeter pour : {refs}",
            ],
        )

    manquements = inv.get("manquements_banque") or []
    if manquements:
        return (
            "banque_reparer",
            "La banque a encore des manquements",
            [f"# {m}" for m in manquements] + [  # type: ignore
                f"python3 pipeline/banque.py verifier {ardoise}",
            ],
        )

    if not inv["plan_importe"] and inv.get("meta_ads"):
        return (
            "meta_ads",
            "Tenter la bibliotheque publicitaire Meta (non bloquante, mais obligatoire a tenter)",
            [
                "# Navigateur (Chrome DevTools, de preference un Chrome deja connecte) :",
                "# facebook.com/ads/library, nom de la marque, pays, faire defiler, capturer",
                "# Ne regarder que les statiques : registre, anciennete, angles deja tournes",
                f"python3 pipeline/metaads.py consigner {ardoise} --statut releve "
                f"--captures marque/meta-ads/01.png --annonces <annonces.json> --note \"...\"",
                f"# ou, sans annonce : --statut aucune --captures ... --note \"...\"",
                f"# ou, apres deux essais rates : --statut echec --motif \"...\"",
            ],
        )

    if not inv["plan_importe"]:
        return (
            "strategie",
            "Mode Cowork : atelier + Read images + strategie-creative + plan",
            [
                f"python3 pipeline/atelier.py {ardoise} --ouvrir",
                "# Read planches, session/references/*.jpg, captures (outil Read)",
                "# Lire skill/strategie-creative.md EN ENTIER",
                "# Ecrire le plan (concepts distincts, pas script packshot)",
                f"python3 pipeline/plan.py importer {ardoise} --fichier <plan.md>",
                "# Interdit : ecrire creas/ a la main",
            ],
        )

    fin = inv.get("fin") or {}

    refusees = fin.get("refusees") or []
    if refusees:
        return (
            "reprendre",
            "Des creas sont refusees a la relecture : declarer la reprise, corriger le prompt",
            [f"python3 pipeline/etat.py reprise-visuel --marque {ardoise} --crea {c}" for c in refusees]
            + [
                "# Corriger la cause du refus dans le prompt, puis :",
                f"python3 pipeline/plan.py importer {ardoise} --fichier <plan-reprise.json>",
            ],
        )

    a_generer = fin.get("a_generer") or []
    if inv["nb_masters"] == 0 or a_generer:
        limite = f" --creas {' '.join(a_generer)}" if a_generer and inv["nb_masters"] else ""
        return (
            "generer",
            "Chiffrer puis generer via MCP Higgsfield uniquement",
            [
                f"python3 pipeline/moteur.py preparer {ardoise}{limite}",
                "# Puis MCP : media_upload / generate_image_batch / jobs_wait",
                f"python3 pipeline/moteur.py recolter {ardoise} --resultats <fichier.json> --solde-avant X --solde-apres Y",
            ],
        )

    a_relire = fin.get("a_relire") or []
    if a_relire:
        return (
            "relecture",
            "Relire chaque master au zoom et consigner un verdict",
            [
                f"python3 pipeline/loupe.py {ardoise} --creas {' '.join(a_relire)}",
                "# Read chaque zone session/loupe/<crea>-*.png, etiquette comprise",
                f"python3 pipeline/relecture.py verdict {ardoise} <crea> --etat ok|refus --constat \"...\"",
            ],
        )

    if not fin.get("audit_ok"):
        return (
            "audit",
            "Passer l'audit mecanique sur les masters presents",
            [
                f"python3 kreative.py audit {ardoise}",
                f"python3 pipeline/atelier.py {ardoise} --ouvrir",
                f"python3 kreative.py page {ardoise}",
            ],
        )

    if fin.get("a_etendre"):
        return (
            "formats_etendre",
            "Etendre par le connecteur les formats que le bord du master ne permet pas de prolonger",
            [
                f"# Lire {ardoise}/formats/a-etendre.json : creas {', '.join(fin['a_etendre'])}",
                "# MCP Higgsfield : outpaint, expand_top et expand_bottom seuls, le carre reste intact",
                f"python3 pipeline/formats.py ranger-extension {ardoise} --crea <crea> --format 4x5|9x16 --fichier <image>",
                f"python3 pipeline/formats.py verifier {ardoise}",
            ],
        )

    if fin.get("formats_manquants"):
        return (
            "formats",
            "Tirer le 4:5 et le 9:16 de chaque master carre",
            [f"python3 kreative.py formats {ardoise}"],
        )

    if not fin.get("livree") and not fin.get("sortie_a_jour"):
        return (
            "sortie",
            "Assembler le document de sortie du skill : synthese, angles, creatives et prompts, garde-fous",
            [
                "# strategie-creative.md doit porter les sections synthese strategique, angles, garde-fous",
                f"python3 pipeline/sortie.py assembler {ardoise}",
            ],
        )

    if not fin.get("livree"):
        return (
            "livrer",
            "Construire le dossier de remise et notifier",
            [
                f"python3 kreative.py livrer {ardoise}",
                f"python3 kreative.py page {ardoise}",
            ],
        )

    if fin.get("publication_configuree") and not fin.get("publiee"):
        return (
            "publier",
            "Pousser le pack livre vers la plateforme de revue",
            [
                f"python3 pipeline/publier.py {ardoise} --client <slug-client> --dry-run",
                f"python3 pipeline/publier.py {ardoise} --client <slug-client>",
            ],
        )

    if fin.get("publiee"):
        return (
            "livree",
            "Pack livre et publie : relever les retours de la plateforme",
            [f"python3 pipeline/retours.py {ardoise} --client <slug-client>"],
        )

    return (
        "livree",
        "Pack livre. Publication non configuree (variables PUBLIE_* absentes) : rien d'autre a faire",
        [f"# Dossier de remise : voir le journal, evenement dossier_livraison"],
    )


def formater(inv: Dict[str, object], code: str, titre: str, cmds: List[str]) -> str:
    lignes = [
        f"PARCOURS  {inv['ardoise']}",
        f"etape     {code}  -  {titre}",
        "",
        "Disque :",
        f"  brief/charte     {'ok' if inv['brief'] else 'non'} / {'ok' if inv['charte'] else 'non'} ({inv['captures']} captures)",
        f"  banque          {'ouverte' if inv['banque_ouverte'] else 'NON'}",
        f"  planches        {len(inv['planches_lues'])}/{len(inv['planches_attendues'])} lues",
        f"  refs retenues   {len(inv['references_retenues'])}",
        f"  refs extraites  {len(inv['references_extraites'])}",
        f"  refs absorbees  {len(inv['references_absorbees'])}",
        f"  plan importe    {'oui' if inv['plan_importe'] else 'non'} ({inv['nb_creas']} creas)",
        f"  masters         {inv['nb_masters']}",
    ]
    if inv.get("skill_fautes"):
        lignes.append("  REGLE ZERO      le skill n'est pas en regle pour cette commande :")
        for f in inv["skill_fautes"]:
            lignes.append(f"                  {f[:110]}")
    if inv.get("creas_manquantes"):
        lignes.append(
            f"  ECART FICHES    la commande declare {inv['creas_attendues']} "
            f"generations, le disque porte {inv['nb_creas']} fiche(s)"
        )
        if inv.get("archives"):
            lignes.append(
                f"                  {inv['fiches_archivees']} fiche(s) sont dans "
                f"{', '.join(inv['archives'])}"
            )
        lignes.append(
            "                  un plan ne peut viser que les fiches presentes : "
            "les identifiants absents seront refuses"
        )
    lignes += [
        "",
        "PROCHAINE ACTION (la seule autorisee) :",
    ]
    for c in cmds:
        lignes.append(f"  {c}")
    lignes += [
        "",
        "Interdit tant que cette etape n'est pas faite :",
        "  ecrire un plan.md / generer / appeler Higgsfield / modifier creas/ a la main",
        "",
        f"Relancer : python3 pipeline/parcours.py suivant {inv['ardoise']}",
    ]
    return "\n".join(lignes)


def exiger(commande: Commande, avant: str) -> int:
    """0 si l'etape demandee est autorisee, 1 sinon."""
    inv = inventaire(commande)
    code, titre, cmds = etape_suivante(inv)
    ordre = [
        "brief", "site", "interrompu", "outillage", "banque_ouvrir", "banque_lire", "banque_retenir",
        "banque_extraire", "banque_absorber", "banque_reparer", "meta_ads", "strategie",
        "reprendre", "generer", "relecture", "audit", "formats", "formats_etendre",
        "sortie", "livrer", "publier", "livree",
    ]
    alias = {
        "strategie": "strategie",
        "plan": "strategie",
        "generer": "generer",
        "generation": "generer",
        "mcp": "generer",
        "audit": "audit",
        "formats": "formats",
        "livrer": "livrer",
    }
    cible = alias.get(avant, avant)
    if cible not in ordre or code not in ordre:
        print(formater(inv, code, titre, cmds))
        return 1
    if ordre.index(code) > ordre.index(cible):
        print(f"OK  -  etape '{avant}' autorisee (disque a '{code}').")
        return 0
    if code == cible:
        print(f"OK  -  etape '{avant}' est la prochaine.")
        print(formater(inv, code, titre, cmds))
        return 0
    print(f"REFUS  -  impossible de faire '{avant}' maintenant.")
    print(formater(inv, code, titre, cmds))
    return 1


def main() -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    sous = parseur.add_subparsers(dest="action", required=True)

    p = sous.add_parser("suivant", help="Afficher la seule prochaine etape")
    p.add_argument("ardoise")

    p = sous.add_parser("statut", help="Inventaire disque + prochaine etape")
    p.add_argument("ardoise")

    p = sous.add_parser("exiger", help="Gate avant strategie|plan|generer")
    p.add_argument("ardoise")
    p.add_argument("--avant", required=True,
                   choices=["strategie", "plan", "generer", "generation", "mcp", "audit",
                            "formats", "livrer"])

    a = parseur.parse_args()
    try:
        commande = Commande.charger(a.ardoise)
    except FileNotFoundError as err:
        print(f"Erreur : {err}", file=sys.stderr)
        print("Creer ou relever la commande d'abord.")
        return 1

    if a.action in ("suivant", "statut"):
        inv = inventaire(commande)
        code, titre, cmds = etape_suivante(inv)
        print(formater(inv, code, titre, cmds))
        return 0

    if a.action == "exiger":
        return exiger(commande, a.avant)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
