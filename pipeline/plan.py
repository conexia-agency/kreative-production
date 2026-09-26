#!/usr/bin/env python3
"""plan.py : le passage de main entre le skill de Kreative et la chaîne.

Le skill de Kreative fait toute la création : la stratégie, les angles, la
copy, le choix des assets et les prompts. Ce module n'en fait aucune part. Il
répond à deux questions mécaniques :

1. `dossier` : qu'est-ce que la chaîne a déjà posé sur le disque, et où, pour
   que la session qui applique le skill n'ait rien à aller rechercher ;
2. `importer` : la session a produit son plan, on le range dans les créas.

Les contrôles de `importer` sont ceux du skill lui-même, jamais les nôtres :
son interdiction du tiret cadratin, et sa règle de parité stricte qui veut que
tout asset nommé dans un prompt existe réellement. Un contrôle qui ne renvoie
pas à une ligne de son skill n'a rien à faire ici. Une exception, décidée par
l'équipe le 19/09/2026 : la phrase de fin « Nano Banana Pro en restant gratuit »
de son skill ne s'exige plus et se retire des prompts si elle s'y trouve, le
connecteur fixant modèle et facturation par ses paramètres d'appel. Écart à
signaler à Evan.

    python3 pipeline/plan.py dossier <ardoise>
    python3 pipeline/plan.py importer <ardoise> --fichier plan.json
    python3 pipeline/plan.py verifier <ardoise>

Cible Python 3.9+. Aucune dépendance externe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))

from etat import Commande, Crea, maintenant  # noqa: E402

SCHEMA = "kreative-plan/1"

# Le caractère s'écrit par son code : ce fichier ne doit en contenir aucun.
TIRET_CADRATIN = chr(0x2014)

# Vocabulaire de formats visuels du skill, section « Le prompt de génération ».
# La liste n'est pas fermée, elle sert à détecter qu'UN format est nommé, pas à
# imposer lequel : le skill dit explicitement que le choix est ouvert.
_FORMATS_VISUELS = (
    "photographie", "photographiee", "photographie de", "nature morte",
    "macrophotographie", "macro", "infographie", "portrait", "split-screen",
    "split screen", "packshot", "illustration", "collage", "rendu 3d",
    "mise en scene", "capture", "format emprunte", "note manuscrite",
    "ticket", "affiche", "plan large", "plan moyen", "gros plan",
    "vue de dessus", "a plat", "flat lay", "diptyque", "sequence",
)

# Skill, « Performance Meta & hiérarchie de layout » : trois tests à passer
# sur CHAQUE créa. Les nommer oblige à les passer ; une case cochée, non.
_TESTS = ("rarete", "lecture_muette", "micro_question")
_TEST_MINIMUM = 25

# Formule anti-régénération, skill « Gestion des assets ». On accepte les
# formulations équivalentes, pas seulement la phrase canonique : ce qui compte
# est que l'interdiction de recréer soit présente.
_ANTI_REGENERATION = (
    "ne le recree pas", "ne la recree pas", "ne recree pas",
    "ne reinvente", "sans le recreer", "exactement ce flacon",
    "exactement ce produit", "utilise exactement",
)


# Skill de Kreative, section « Règles du prompt » : « chaque prompt se termine,
# en toute dernière phrase, par ce texte exact ». On ne le paraphrase pas, on le
# recopie, et on vérifie qu'il est là.
PHRASE_DE_FIN = "Utilise la meilleure qualité de Nano Banana Pro en restant gratuit."


def _plier_texte(texte: str) -> str:
    """Sans accents, en minuscules : pour comparer des libelles de fond."""
    n = unicodedata.normalize("NFD", texte or "")
    return "".join(c for c in n if unicodedata.category(c) != "Mn").lower().strip()


def _sans_phrase_de_fin(prompt: str) -> str:
    """Retire la phrase de fin héritée du contexte Cowork, si présente."""
    nettoye = prompt.rstrip()
    if nettoye.endswith(PHRASE_DE_FIN):
        nettoye = nettoye[: -len(PHRASE_DE_FIN)].rstrip()
    return nettoye

# Le modèle que nomme cette phrase. La chaîne ne choisit pas le moteur : elle
# lit celui que le skill impose.
MODELE_PAR_DEFAUT = "nano_banana_pro"


# ---------------------------------------------------------------------------
# 1. Le dossier d'entrée : ce que la chaîne a posé, et où
# ---------------------------------------------------------------------------

def _lister(dossier: Path, motif: str = "*") -> List[str]:
    if not dossier.is_dir():
        return []
    return sorted(str(f.relative_to(dossier.parent.parent))
                  for f in dossier.rglob(motif) if f.is_file())


def dossier_entrees(commande: Commande) -> dict:
    """L'inventaire de ce qui est sur le disque au moment où le skill démarre."""
    base = commande.dossier
    marque = base / "marque"
    brief = commande.donnees.get("brief") or {}

    def present(chemin: Path) -> bool:
        return chemin.exists()

    scraping = {}
    fichier_scraping = marque / "scraping.json"
    if fichier_scraping.exists():
        try:
            scraping = json.loads(fichier_scraping.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            scraping = {"issue": "marqueur illisible"}

    return {
        "ardoise": commande.donnees["ardoise"],
        "marque": commande.donnees.get("marque"),
        "url_site": commande.donnees.get("url_site"),
        "pack": commande.donnees.get("pack"),
        "creas_attendues": commande.donnees.get("quantite_generee"),
        "identifiants": [c.identifiant for c in commande.creas()],
        "brief": {
            "redige": bool(brief.get("_redige")),
            "fichier": "brief/brief.json" if present(base / "brief" / "brief.json") else None,
            "a_completer": brief.get("a_completer") or [],
            "declare_sans_fournir": brief.get("_declare_sans_fournir") or [],
        },
        "pieces_jointes": _lister(base / "brief" / "pieces-jointes"),
        "site": {
            "issue": scraping.get("issue"),
            "charte": "marque/charte-site.json" if present(marque / "charte-site.json") else None,
            "contenu": "marque/site.json" if present(marque / "site.json") else None,
            "assets": ("marque/assets-site/index.json"
                       if present(marque / "assets-site" / "index.json") else None),
            "logos": ("marque/logo/candidats.json"
                      if present(marque / "logo" / "candidats.json") else None),
            "captures": _lister(marque / "captures"),
        },
    }


def ecrire_dossier(commande: Commande) -> Path:
    entrees = dossier_entrees(commande)
    chemin = commande.dossier / "session" / "entrees.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(entrees, ensure_ascii=False, indent=2), encoding="utf-8")
    commande.tracer("dossier_entrees_ecrit",
                    pieces_jointes=len(entrees["pieces_jointes"]),
                    captures=len(entrees["site"]["captures"]),
                    charte=bool(entrees["site"]["charte"]))
    return chemin


def rapport_dossier(entrees: dict) -> str:
    site = entrees["site"]
    lignes = [
        f"{entrees['marque']} ({entrees['ardoise']}), pack {entrees['pack']}, "
        f"{entrees['creas_attendues']} créas attendues.",
        "",
        "Brief",
        f"  rédigé            {'oui' if entrees['brief']['redige'] else 'NON'}",
        f"  à compléter       {len(entrees['brief']['a_completer'])}",
        f"  pièces jointes    {len(entrees['pieces_jointes'])}",
        "",
        f"Site ({entrees['url_site'] or 'aucune adresse'})",
        f"  relevé            {site['issue'] or 'pas encore fait'}",
        f"  charte mesurée    {site['charte'] or 'ABSENTE'}",
        f"  contenu des pages {site['contenu'] or 'ABSENT'}",
        f"  images du site    {site['assets'] or 'ABSENT'}",
        f"  candidats logo    {site['logos'] or 'ABSENT'}",
        f"  captures          {len(site['captures'])}",
    ]
    if entrees["brief"]["declare_sans_fournir"]:
        lignes += ["", "Déclaré par le client sans fichier joint :"]
        lignes += [f"  {x}" for x in entrees["brief"]["declare_sans_fournir"]]
    return "\n".join(lignes)


# ---------------------------------------------------------------------------
# 2. Lire la sortie du skill, telle qu'il l'écrit
# ---------------------------------------------------------------------------

# Le skill de Kreative impose son propre format de sortie, en markdown, sous le
# titre « Format de sortie (à respecter exactement) ». Il ne produit pas de
# JSON. C'est donc à nous de lire son markdown, pas à lui de changer de format :
# lui demander du JSON reviendrait à modifier son skill, ce qui est exactement
# ce qui lui a été reproché le 18/09.
#
# La structure qu'on lit, et rien d'autre : un titre « Angle N », puis pour
# chaque créa une ligne « Créa N » suivie de ses champs à puces, « Titre
# (headline) », « Sous-titre », « Texte additionnel », « CTA », « Assets à
# joindre » et « Prompt de génération ».
#
# Les créas sont numérotées dans leur ordre d'apparition : angle 1 créa 1
# devient c01, angle 1 créa 2 devient c02, angle 2 créa 1 devient c03.

MOTIF_ANGLE = re.compile(
    r"^#{2,4}\s*Angle\s*(\d+)\s*[:.\-" + chr(0x2014) + r"]?\s*(.*)$", re.I)
MOTIF_CREA = re.compile(r"^\*{0,2}\s*Cr[ée]a\s*(\d+)\s*\*{0,2}\s*$", re.I)
MOTIF_CHAMP = re.compile(r"^[-*]\s*\**\s*([^:*]+?)\s*\**\s*:\s*(.*)$")

# Les libellés du skill, dans sa langue, vers nos champs. Une clé absente du
# tableau est ignorée : le skill peut ajouter une ligne sans casser la lecture.
CHAMPS_DU_SKILL = {
    "titre": "accroche",
    "titre (headline)": "accroche",
    "headline": "accroche",
    "sous-titre": "sous_accroche",
    "sous titre": "sous_accroche",
    "texte additionnel": "badge",
    "cta": "cta",
    "assets a joindre": "assets_texte",
    "prompt de generation": "prompt",
    "prompt": "prompt",
}

# Les guillemets dont le skill entoure ses prompts, et qui n'en font pas partie.
GUILLEMETS = "«»“”\"'"

# Le tiret cadratin, écrit par son code : ce fichier n'en contient aucun. Le
# skill s'en sert comme d'un « rien ici » dans ses champs vides, et il le fait
# dans SON fichier : on le lit, on ne le lui reproche pas.
VIDE = {chr(0x2014), "-", "--", ""}

# Les mots par lesquels le skill dit « ce champ est vide, volontairement ».
# Son format prescrit le tiret cadratin pour cela ; une session qui respecte
# l'interdit de ce caractère écrit autre chose : « (délibéré) », « aucun »,
# « néant ». Tous valent un champ vide, sinon le contrôle de copy exige de
# peindre le mot « délibéré » dans l'image. Signalé par Kreative le 20/09,
# sur un CTA volontairement absent.
MOTS_ABSENCE = {"delibere", "deliberee", "deliberement", "aucun", "aucune",
                "neant", "rien", "sans", "vide", "non", "na", "nul",
                "absent", "absente", "volontaire", "volontairement"}

PONCTUATION = re.compile(
    "[" + re.escape("-*()[]{}.,:;!?\"'/" + chr(0x2013) + chr(0x2014)) + r"\s]+")


def _est_absence(valeur: str) -> bool:
    """Le champ dit-il « rien », sous une forme ou une autre ?"""
    nu = PONCTUATION.sub(" ", valeur or "").strip()
    if not nu:
        return True
    return {_cle(mot) for mot in nu.split()} <= MOTS_ABSENCE


def _nettoyer(valeur: str) -> str:
    valeur = valeur.strip()
    if valeur in VIDE or _est_absence(valeur):
        return ""
    return valeur.strip(GUILLEMETS).strip()


def _cle(libelle: str) -> str:
    plie = unicodedata.normalize("NFD", libelle.strip().lower())
    return "".join(c for c in plie if unicodedata.category(c) != "Mn")


def _chemins_dans(texte: str, base: Path) -> List[str]:
    """Les fichiers réellement présents que cette ligne d'assets désigne.

    Le skill écrit ses assets en langage naturel, avec un nom de fichier et
    parfois un lien : « PJ01-logo.png », « photo du coffret exact (à joindre) ».
    On ne devine pas : on cherche les noms de fichiers cités, et on ne retient
    que ceux qui existent sur le disque. Ce qui n'est pas trouvé n'est pas
    inventé, il ressort dans les alertes.
    """
    if not texte:
        return []
    trouves: List[str] = []
    for brut in re.findall(r"[\w\-./]+\.(?:png|jpe?g|webp|svg|gif|avif)", texte, re.I):
        candidat = brut.lstrip("./")
        direct = base / candidat
        if direct.exists():
            trouves.append(str(direct.relative_to(base)))
            continue
        # Sinon on cherche le fichier par son nom seul, où qu'il soit rangé
        # dans la commande : le skill nomme « PJ01-logo.png », la chaîne l'a
        # posé dans brief/pieces-jointes/ ou marque/assets-site/.
        nom = Path(candidat).name
        for dossier in ("brief/pieces-jointes", "marque/assets-site",
                        "marque/logo", "assets"):
            racine = base / dossier
            if not racine.is_dir():
                continue
            trouve = next(iter(racine.rglob(nom)), None)
            if trouve is not None:
                trouves.append(str(trouve.relative_to(base)))
                break
    return list(dict.fromkeys(trouves))


def lire_markdown(texte: str, base: Path) -> dict:
    """Transforme la sortie markdown du skill en plan lisible par `importer`."""
    creas: List[dict] = []
    angle_courant = ""
    courante: Optional[dict] = None
    champ_courant: Optional[str] = None
    manque: List[str] = []
    dans_manque = False

    def clore() -> None:
        nonlocal courante
        if courante:
            creas.append(courante)
            courante = None

    for ligne in texte.splitlines():
        depouille = ligne.strip()

        if depouille.startswith("#"):
            # Le skill numérote ses titres, « ## 4. Ce qui a manqué ». On
            # retire la numérotation avant de reconnaître la section, sinon le
            # bloc des carences repart dans le prompt de la dernière créa.
            titre = _cle(re.sub(r"^[\d.\s)]+", "", depouille.lstrip("#").strip()))
            angle = MOTIF_ANGLE.match(depouille)
            # TOUT titre ferme la créa en cours, pas seulement un titre
            # d'angle. Le format de sortie du skill prescrit après les créas
            # une section « Garde-fous » dont les lignes commencent par
            # « - Prompt : ... », « - Assets : ... », « - Copy : ... » : sans
            # cette fermeture, le parseur les lit comme les champs de la
            # DERNIÈRE créa et les écrase. Signalé par Kreative le 20/09, le
            # prompt de c24 remplacé par une ligne de checklist. Leur format
            # n'est pas en cause : c'est au parseur de le suivre.
            clore()
            champ_courant = None
            dans_manque = titre.startswith("ce qui a manque")
            if angle:
                angle_courant = _nettoyer(angle.group(2)) or f"angle {angle.group(1)}"
            continue

        if dans_manque:
            if depouille.startswith(("-", "*")):
                manque.append(depouille.lstrip("-* ").strip())
            continue

        if MOTIF_CREA.match(depouille):
            clore()
            courante = {"angle": angle_courant, "accroche": "", "sous_accroche": "",
                        "cta": "", "badge": "", "prompt": "", "assets_texte": ""}
            champ_courant = None
            continue

        if courante is None:
            continue

        champ = MOTIF_CHAMP.match(depouille)
        if champ:
            cle = CHAMPS_DU_SKILL.get(_cle(champ.group(1)))
            if cle:
                courante[cle] = _nettoyer(champ.group(2))
                champ_courant = cle
            else:
                champ_courant = None
            continue

        # Une ligne sans puce prolonge le champ précédent : un prompt tient
        # rarement sur une seule ligne.
        if champ_courant and depouille:
            courante[champ_courant] = _nettoyer(
                f"{courante[champ_courant]} {depouille}".strip())

    clore()

    sorties = []
    for rang, crea in enumerate(creas, start=1):
        sorties.append({
            "id": f"c{rang:02d}",
            "angle": crea["angle"],
            "accroche": crea["accroche"],
            "sous_accroche": crea["sous_accroche"],
            "cta": crea["cta"],
            "badge": crea["badge"],
            "prompt": crea["prompt"],
            "modele": MODELE_PAR_DEFAUT,
            "assets": _chemins_dans(crea["assets_texte"], base),
            "_assets_texte": crea["assets_texte"],
        })
    # Le texte entier est conservé : c'est lui qui porte la ligne « Références
    # visuelles retenues » du skill, que le contrôle de la banque recoupe avec
    # ce qui a réellement été ouvert.
    return {"schema": SCHEMA, "creas": sorties, "ce_qui_a_manque": manque,
            "_texte_brut": texte}


def charger_plan(fichier: Path, commande: Commande) -> dict:
    """Lit un plan, que le fichier soit du markdown du skill ou du JSON."""
    texte = fichier.read_text(encoding="utf-8")
    if fichier.suffix.lower() in (".md", ".markdown", ".txt"):
        return lire_markdown(texte, commande.dossier)
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        # Un fichier sans extension connue et qui n'est pas du JSON : on tente
        # le markdown plutôt que d'échouer sur une virgule.
        return lire_markdown(texte, commande.dossier)


# ---------------------------------------------------------------------------
# 3. Importer le plan produit par la session
# ---------------------------------------------------------------------------

# Skill, « Packs » : starter 3 angles, growth 6, scale 12, et « 2 créas par
# angle est le plancher : en dessous, on ne distingue plus "l'angle ne marche
# pas" de "cette exécution ne marche pas" ».
ANGLES_PAR_PACK = {"starter": 3, "growth": 6, "scale": 12}
CREAS_PAR_ANGLE_MINIMUM = 2

# Skill, « Longueur de la copy » : titre visé sous dix mots, sous-titre d'une
# douzaine de mots au plus. Il précise que le dosage est un curseur et non un
# plafond : ce sont des alertes, pas des refus.
MOTS_TITRE_MAXIMUM = 10
MOTS_SOUS_TITRE_MAXIMUM = 12

# Skill, checklist : « police exacte relevée sur le site et identique sur TOUS
# les prompts ». Les noms que le contrôle sait reconnaître dans un prompt.
POLICES_CONNUES = (
    "poppins", "helvetica", "arial", "inter", "georgia", "roboto", "dm sans",
    "glacial indifference", "ibm plex", "montserrat", "lato", "open sans",
    "raleway", "oswald", "nunito", "manrope", "space grotesk", "playfair",
    "futura", "gotham", "proxima")

# Skill, « Récupération et livraison des assets » : numérotés globalement
# (« PJ01-logo.png »), rangés dans assets/, résolution vérifiée.
NOM_ASSET = re.compile(r"^assets/PJ\d{2}-[^/]+$")
COTE_ASSET_MINIMUM = 600


def _plier_texte(texte: str) -> str:
    n = unicodedata.normalize("NFD", texte or "")
    return "".join(c for c in n if unicodedata.category(c) != "Mn").lower()


def _polices_nommees(texte: str) -> set:
    """Les polices connues citées en mots entiers : « inter » n'est pas « interface »."""
    plie = _plier_texte(texte)
    return {p for p in POLICES_CONNUES
            if re.search(rf"(?<![a-z]){re.escape(p)}(?![a-z])", plie)}


def _polices_de_reference(commande: Commande) -> set:
    """Les polices que le brief impose et que le site porte réellement."""
    trouvees = set()
    reponses = ((commande.donnees.get("brief") or {}).get("reponses") or {})
    sources = [str(reponses.get("polices") or "")]
    charte = commande.dossier / "marque" / "charte-site.json"
    if charte.exists():
        try:
            polices = json.loads(charte.read_text(encoding="utf-8")).get("polices") or {}
            sources += [str(v) for v in polices.values()]
        except (OSError, ValueError):
            pass
    return _polices_nommees(" ".join(sources))


def _controles_du_pack(commande: Commande, recevables: List[dict],
                       refus: List[str], alertes: List[str]) -> List[dict]:
    """Les règles du skill qui portent sur le pack entier, pas sur une créa."""
    # 1. Les assets : numérotation globale et résolution.
    gardees = []
    for c in recevables:
        mal_nommes = [a for a in c["assets"] if not NOM_ASSET.match(a)]
        if mal_nommes:
            refus.append(f"{c['id']} : asset hors convention du skill, "
                         f"{', '.join(mal_nommes)}. Il se range dans assets/ sous un "
                         f"numéro global : assets/PJ01-logo.png.")
            continue
        gardees.append(c)
    recevables = gardees
    try:
        from PIL import Image
        vus = set()
        for c in recevables:
            for a in c["assets"]:
                if a in vus:
                    continue
                vus.add(a)
                with Image.open(commande.dossier / a) as image:
                    largeur, hauteur = image.size
                if min(largeur, hauteur) < COTE_ASSET_MINIMUM:
                    alertes.append(f"{a} fait {largeur}x{hauteur} : trop petit pour "
                                   f"une créa, chercher une version haute définition "
                                   f"sur le site, sinon le signaler.")
    except ImportError:
        alertes.append("Pillow absent : résolution des assets non vérifiée.")

    # 2. Deux créas par angle au moins, sur l'état final du pack : les créas
    #    déjà planifiées comptent, celles du plan les remplacent.
    angle_de = {x.identifiant: (x.angle or "").strip()
                for x in commande.creas() if (x.prompt.scene or "").strip()}
    for c in recevables:
        angle_de[c["id"]] = c["angle"].strip()
    effectifs: Dict[str, int] = {}
    for angle in angle_de.values():
        effectifs[angle] = effectifs.get(angle, 0) + 1
    gardees = []
    for c in recevables:
        angle = c["angle"].strip()
        if not angle:
            refus.append(f"{c['id']} : aucun angle nommé. Le skill nomme chaque "
                         f"angle et le justifie en une ligne.")
            continue
        if effectifs[angle] < CREAS_PAR_ANGLE_MINIMUM:
            refus.append(f"{c['id']} : l'angle « {angle} » n'a que {effectifs[angle]} "
                         f"créa. Le skill en veut {CREAS_PAR_ANGLE_MINIMUM} au moins "
                         f"par angle, d'exécution différente.")
            continue
        gardees.append(c)
    recevables = gardees
    attendus = ANGLES_PAR_PACK.get(commande.donnees.get("pack") or "")
    nb_angles = len([a for a in effectifs if a])
    if recevables and attendus and nb_angles != attendus:
        alertes.append(f"{nb_angles} angle(s) pour {attendus} au pack "
                       f"{commande.donnees.get('pack')}")

    # 3. La longueur de la copy.
    for c in recevables:
        titre = len(c["accroche"].split())
        sous = len(c["sous_accroche"].split())
        if titre > MOTS_TITRE_MAXIMUM:
            alertes.append(f"{c['id']} : titre de {titre} mots, le skill vise moins "
                           f"de {MOTS_TITRE_MAXIMUM}. Justifié par la mécanique ?")
        if sous > MOTS_SOUS_TITRE_MAXIMUM:
            alertes.append(f"{c['id']} : sous-titre de {sous} mots, le skill en veut "
                           f"une douzaine au plus. Justifié par la mécanique ?")

    # 4. La même police partout.
    reference = _polices_de_reference(commande)
    if reference:
        for c in recevables:
            nommees = _polices_nommees(c["prompt"])
            etrangeres = nommees - reference
            if etrangeres:
                alertes.append(f"{c['id']} : police hors charte nommée, "
                               f"{', '.join(sorted(etrangeres))}.")
            if not nommees & reference:
                alertes.append(f"{c['id']} : aucune police de la charte nommée "
                               f"({', '.join(sorted(reference))}).")
    return recevables


def controler(plan: dict, commande: Commande) -> Tuple[List[dict], List[str], List[str]]:
    """Sépare les créas recevables des refus. Rend (creas, refus, alertes).

    Chaque refus cite la règle du skill de Kreative qu'il fait respecter. Rien
    n'est corrigé en silence : une créa qui ne passe pas est rendue à la
    session, avec le motif.
    """
    refus: List[str] = []
    alertes: List[str] = []
    recevables: List[dict] = []

    connus = {c.identifiant for c in commande.creas()}
    vus: Dict[str, int] = {}

    # Les références que la session a réellement absorbées : seules elles
    # peuvent servir de structure source à une créa.
    import banque as module_banque
    absorbees = set((module_banque._lire_etat(commande).get("references_absorbees") or {}).keys())

    for rang, entree in enumerate(plan.get("creas") or [], start=1):
        identifiant = str(entree.get("id") or entree.get("crea") or "").strip()
        etiquette = identifiant or f"créa n°{rang}"

        if not identifiant:
            refus.append(f"{etiquette} : aucun identifiant")
            continue
        if identifiant not in connus:
            refus.append(f"{etiquette} : cet identifiant n'existe pas dans la commande "
                         f"({', '.join(sorted(connus))})")
            continue
        vus[identifiant] = vus.get(identifiant, 0) + 1
        if vus[identifiant] > 1:
            refus.append(f"{etiquette} : identifiant présent {vus[identifiant]} fois")
            continue

        prompt = (entree.get("prompt") or "").strip()
        if not prompt:
            refus.append(f"{etiquette} : prompt vide")
            continue

        # Écart assumé au skill de Kreative, décidé par l'équipe le 19/09/2026 : la
        # phrase de fin « Utilise la meilleure qualité de Nano Banana Pro en
        # restant gratuit » ne s'exige plus. Elle vient du contexte Cowork ;
        # ici le modèle, la résolution et la facturation sont fixés par les
        # paramètres d'appel du connecteur, pas par le prompt, et « en restant
        # gratuit » n'a aucun sens sur un appel facturé. Si elle traîne encore
        # dans un prompt, on la retire silencieusement plutôt que de refuser :
        # un plan déjà écrit avec elle reste valable.
        prompt = _sans_phrase_de_fin(prompt)

        # Une créa déjà générée avec CE prompt exact ne se refuse plus pour un
        # risque d'écriture : la dépense est faite, l'image existe, et c'est
        # l'audit OCR qui dit si le risque s'est matérialisé. Les contrôles
        # préventifs ci-dessous ne bloquent que ce qui reste à générer. La
        # comparaison ignore la phrase de fin des deux côtés : sa disparition
        # ne change pas l'image, elle ne doit pas faire regénérer un master.
        try:
            existante = commande.lire_crea(identifiant)
            deja_generee = bool(existante.master) and \
                _sans_phrase_de_fin((existante.prompt.scene or "").strip()) == prompt
        except FileNotFoundError:
            deja_generee = False

        # Skill de Kreative, « Règles du prompt » : tiret cadratin interdit, ni
        # dans le texte affiché, ni comme élément graphique.
        if TIRET_CADRATIN in prompt:
            refus.append(f"{etiquette} : tiret cadratin dans le prompt, interdit par le skill")
            continue

        # Trois exigences du skill que rien ne vérifiait, ajoutées le 22/09/2026
        # après une journée d'erreurs qui toutes étaient écrites dans le skill.
        # On compare sans accents : un prompt peut légitimement être rédigé en
        # ASCII, seule la copy à peindre porte ses accents.
        def _plier(texte: str) -> str:
            n = unicodedata.normalize("NFD", texte)
            return "".join(c for c in n if unicodedata.category(c) != "Mn").lower()

        # L'ouverture et le format visuel se jugent en tete de prompt, la ou le
        # skill les impose. La formule anti-regeneration, elle, vit avec le bloc
        # des assets, donc en fin : la chercher dans l'entete seule la manque.
        entete = _plier(prompt[:600])
        plie = _plier(prompt)

        # 1. « Type + format, en tout premier. » Le skill ouvre là-dessus, et
        #    c'est l'oubli qui fait générer un mauvais ratio.
        if "format carre 1:1" not in entete and "format carre 1 :1" not in entete:
            refus.append(
                f"{etiquette} : le prompt n'ouvre pas sur le format. Le skill "
                f"l'impose en tout premier, « Creative publicitaire statique, "
                f"format carre 1:1. », et c'est cet oubli qui fait sortir un "
                f"mauvais ratio.")
            continue

        # 2. « Tu NOMMES ce format dans le prompt. » Mesuré les 19 et 20/09 :
        #    les prompts citaient la référence de la banque au lieu de nommer
        #    un format visuel, ce qui a produit des décalques au lieu de créas.
        if not any(mot in entete for mot in _FORMATS_VISUELS):
            refus.append(
                f"{etiquette} : aucun format visuel nommé. Le skill demande de "
                f"nommer le format qui sert CETTE créa, librement choisi : "
                f"photographie, nature morte, macrophotographie, infographie, "
                f"portrait, split-screen, format emprunte au reel, rendu 3D, "
                f"collage, illustration... Citer une référence de la banque a "
                f"la place donne un décalque.")
            continue

        # 3. « Formule anti-régénération à coller dans chaque prompt qui
        #    utilise un asset réel. » Sans elle, le modèle réinvente le
        #    produit : trois volumes différents peints sur un flacon qui n'en
        #    a qu'un, les 21 et 22/09.
        assets_declares = entree.get("assets") or entree.get("references") or []
        if assets_declares and not any(f in plie for f in _ANTI_REGENERATION):
            refus.append(
                f"{etiquette} : {len(assets_declares)} asset(s) joint(s) mais "
                f"aucune formule anti-regeneration dans le prompt. Sans elle le "
                f"modele recree le produit au lieu de l'utiliser. Le skill "
                f"donne la formule : « ne le recree pas, ne reinvente aucun "
                f"detail, aucun objet ni aucun texte ».")
            continue

        # 4. Le point focal unique, le fond, et les trois tests. Le skill les
        #    impose sur CHAQUE créa ; rien ne les vérifiait. Le pack du 19/09
        #    n'avait aucun point focal décidé et ses dix créas partageaient le
        #    même fond crème, ce que le skill appelle du quasi-clonage.
        manques = []
        # La structure source. Dit par l'équipe le 25/09 sur la page blanche du client A :
        # « il invente les structures, il met du texte, une image au hasard
        # qui n'a aucun rapport, et il met le CTA au pif ». La banque est une
        # collection de structures gagnantes, et le skill fait reprendre leur
        # layout, leur rapport texte/image et le placement du CTA. Mesuré sur
        # ce lot : les quatre créas sans structure source étaient les quatre
        # rejetées. Chaque créa nomme désormais la référence absorbée dont
        # elle reprend la construction. Le contenu reste celui du client.
        structure = str(entree.get("structure") or "").strip().upper()
        if not structure:
            manques.append("structure, l'identifiant de la reference dont la crea "
                           "reprend la construction (ex. EC1-07)")
        elif structure not in absorbees:
            manques.append(f"structure {structure}, qui n'est pas une reference "
                           f"absorbee de cette commande ({', '.join(sorted(absorbees)) or 'aucune'})")
        if len((entree.get("point_focal") or "").strip()) < 12:
            manques.append("point_focal, ce qui domine le cadre en une phrase")
        if len((entree.get("fond") or "").strip()) < 6:
            manques.append("fond, son libelle court, clair ou sombre")
        tests = entree.get("tests") or {}
        for nom in _TESTS:
            if len(str(tests.get(nom, "")).strip()) < _TEST_MINIMUM:
                manques.append(f"tests.{nom}, au moins {_TEST_MINIMUM} caracteres")
        if manques:
            refus.append(
                f"{etiquette} : le skill impose de decider ces points sur CHAQUE "
                f"crea, ils manquent ou sont trop courts : "
                f"{' ; '.join(manques)}. Un point focal unique, un fond qui "
                f"varie d'une crea a l'autre, et les trois tests rarete, "
                f"lecture muette, micro-question.")
            continue

        # La copy déclarée doit être DANS le prompt. Le texte est peint par le
        # modèle : une copy qui n'apparaît pas dans le prompt ne sera jamais
        # dans l'image, et l'audit la comptera absente à raison. C'est la
        # règle de cohérence du skill, « le concept, la liste des assets et le
        # prompt doivent être parfaitement alignés », appliquée à la copy.
        # Mesuré le 19/09 : trois créas déclaraient un sous-titre que leur
        # prompt ne peignait pas, et l'audit les a signalées après 6 crédits
        # de génération au lieu d'avant.
        import unicodedata as _ud

        def _mots(texte: str) -> set:
            plie = unicodedata.normalize("NFD", texte or "")
            plie = "".join(c for c in plie if unicodedata.category(c) != "Mn").lower()
            return set(re.findall(r"[a-z]{4,}", plie))

        copy_hors_prompt = sorted(
            (_mots(entree.get("accroche")) | _mots(entree.get("sous_accroche"))
             | _mots(entree.get("cta")) | _mots(entree.get("badge")))
            - _mots(prompt))
        if copy_hors_prompt:
            refus.append(f"{etiquette} : la copy déclarée porte des mots que le "
                         f"prompt ne peint pas : {', '.join(copy_hors_prompt[:8])}. "
                         f"Aligner les champs de copy sur le texte réellement "
                         f"écrit dans le prompt.")
            continue

        # Une indication TECHNIQUE collée au texte à peindre finit peinte.
        # Mesuré trois fois le 19/09 sur un même lot : un bouton portant
        # « #BE93FA Lire la suite », deux cartes portant « Poppins SemiBold:
        # vos créas livrées », et un corps de texte en lorem ipsum lisible.
        # Le modèle ne distingue pas la consigne de rendu du contenu à écrire
        # quand les deux sont dans la même phrase, juste avant les deux points.
        #
        # Ce n'est pas une règle de création : c'est la mécanique d'appel au
        # modèle, elle nous appartient. Le contrôle ne réécrit rien, il refuse
        # et montre le passage fautif.
        faute_technique = None
        for motif, quoi in (
            (r"#[0-9A-Fa-f]{6}\s*:", "un code couleur juste avant les deux points"),
            (r"(?:Poppins|Helvetica|Arial|Inter|Georgia|Roboto|DM Sans|Glacial(?:\s+Indifference)?"
             r"|IBM Plex(?:\s+Mono)?|Montserrat|Lato|Open Sans|Raleway|Oswald|Nunito|Manrope"
             r"|Space Grotesk|Playfair|Futura|Gotham|Proxima)[^:.]{0,30}:",
             "un nom de police juste avant les deux points"),
            (r"(?i)lorem\s+ipsum", "la mention lorem ipsum"),
        ):
            trouve = re.search(motif, prompt)
            if trouve:
                faute_technique = (quoi, trouve.group(0)[:48])
                break
        if faute_technique:
            message = (f"{etiquette} : {faute_technique[0]}, "
                       f"« {faute_technique[1]} ». Le modèle peut le peindre dans "
                       f"l'image : écrire la consigne de rendu dans une phrase "
                       f"séparée du texte à afficher.")
            if deja_generee:
                alertes.append(message + " Créa déjà générée avec ce prompt : "
                               "l'audit OCR tranche, rien n'est regénéré.")
            else:
                refus.append(message)
                continue

        # Skill de Kreative, « Gestion des assets », parité stricte : tout asset
        # nommé dans le prompt figure en pièce jointe.
        assets = [str(a) for a in (entree.get("assets") or entree.get("references") or [])]
        absents = [a for a in assets if not (commande.dossier / a).exists()]
        if absents:
            refus.append(f"{etiquette} : asset introuvable sur le disque, "
                         f"{', '.join(absents)}")
            continue

        recevables.append({
            "id": identifiant,
            "angle": str(entree.get("angle") or entree.get("concept") or ""),
            "accroche": str(entree.get("accroche") or ""),
            "sous_accroche": str(entree.get("sous_accroche") or ""),
            "cta": str(entree.get("cta") or ""),
            "badge": str(entree.get("badge") or ""),
            "prompt": prompt,
            "modele": str(entree.get("modele") or MODELE_PAR_DEFAUT),
            "assets": assets,
            "point_focal": str(entree.get("point_focal") or "").strip(),
            "structure": str(entree.get("structure") or "").strip().upper(),
            "fond": str(entree.get("fond") or "").strip(),
            "tests": {k: str(v).strip()
                      for k, v in (entree.get("tests") or {}).items()},
        })

    recevables = _controles_du_pack(commande, recevables, refus, alertes)

    attendues = commande.donnees.get("quantite_generee") or 0
    if recevables and len(recevables) != attendues:
        alertes.append(f"{len(recevables)} créa(s) reçues pour {attendues} attendues sur "
                       f"le pack {commande.donnees.get('pack')}")

    sans_asset = [c["id"] for c in recevables if not c["assets"]]
    if recevables and len(sans_asset) > len(recevables) / 2:
        # Skill de Kreative : « un pack où la majorité des créas ne demandent
        # que le logo est un ÉCHEC ». On ne bloque pas, on le dit.
        alertes.append(f"{len(sans_asset)} créa(s) sur {len(recevables)} ne joignent aucun "
                       f"asset : {', '.join(sans_asset)}")

    return recevables, refus, alertes


def importer(ardoise: str, fichier: Path) -> dict:
    commande = Commande.charger(ardoise)
    plan = charger_plan(fichier, commande)
    if plan.get("schema") not in (None, SCHEMA):
        raise ValueError(f"schéma inconnu : {plan.get('schema')}, attendu {SCHEMA}")

    recevables, refus, alertes = controler(plan, commande)

    # La banque de références, avant tout le reste. Le skill demande d'ouvrir
    # toutes les planches de la famille et les retenues en pleine résolution
    # AVANT d'écrire les créas, et il fait cocher cette étape dans sa propre
    # liste de contrôle. Cocher ne prouve rien : le 19/09, un run a cité seize
    # références après avoir ouvert deux planches sur vingt et aucun fichier
    # pleine résolution. Rien ne l'a arrêté. Désormais si.
    #
    # Ce contrôle ne juge aucun choix créatif. Il vérifie que les références
    # citées ont réellement été demandées, que la famille est celle que le
    # secteur désigne, et qu'aucune ancienne créa du client du jour n'est
    # reprise. C'est son process, rendu mesurable.
    import banque as module_banque

    citees = module_banque.references_citees(plan.get("_texte_brut") or "")
    manquements = module_banque.verifier(commande, citees or None)

    # Le matériel du CLIENT, au même rang que la banque. Le 21/09 sur le client A :
    # la charte officielle, le registre visuel réel de la marque et une créa
    # de septembre portant déjà l'accroche du jour dormaient dans la commande,
    # jamais ouverts, et le plan s'est écrit contre eux sans le savoir.
    import dossier as module_dossier

    manquements += module_dossier.verifier(commande)

    # La bibliothèque publicitaire Meta, avant le PREMIER plan. Le skill la
    # veut tentée à chaque commande ; le 25/09 sur le client A elle ne l'a pas été,
    # et rien ne l'a vu. Un échec motivé est recevable. Une commande déjà
    # planifiée (une reprise) n'est pas bloquée après coup.
    if not any((c.prompt.scene or "").strip() for c in commande.creas()):
        import metaads as module_metaads
        manquements += module_metaads.verifier(commande)
        import outillage as module_outillage
        manquements += module_outillage.verifier(commande)

    # La règle zéro, au même rang que les deux précédentes et pour la même
    # raison. Le CLAUDE.md du dépôt la nomme « la règle qui rend toutes les
    # autres superflues » : lire le skill EN ENTIER, à chaque commande, avant
    # d'écrire une ligne de stratégie ou de prompt. Elle n'était tenue par
    # rien. Le 22/09, le skill a été lu une fois au quatrième lot de la
    # journée, et cinq lots de plus ont suivi sans y retourner : le format
    # visuel n'était nommé nulle part, la synthèse stratégique n'existait pas,
    # et un scrim dégradé a été réinventé alors qu'il y figure depuis toujours.
    import skill as module_skill

    manquements += module_skill.verifier(commande)

    # Un manquement de banque invalide le PLAN ENTIER, pas une créa : la
    # sélection de références nourrit le pack globalement, le skill le dit
    # lui-même. On ne range donc rien du tout, plutôt que de laisser passer
    # dix-sept créas construites sans avoir regardé les références.
    refus_plan = [f"banque de références : {m}" for m in manquements]

    # La variété des fonds, sur l'ensemble du lot. Le skill : « Une DA
    # dominante n'oblige PAS à faire tout le pack sur ce même fond. Faire les
    # 12 créas sur le même noir = quasi-clonage. » Mesuré le 19/09 : dix créas
    # sur dix sur le même crème. On ne juge pas le goût, on compte.
    fonds = [_plier_texte(c.get("fond") or "") for c in recevables]
    fonds = [f for f in fonds if f]
    if len(fonds) >= 3:
        from collections import Counter
        commun, combien = Counter(fonds).most_common(1)[0]
        if combien > len(fonds) * 0.6:
            refus_plan.append(
                f"variete des fonds : {combien} crea(s) sur {len(fonds)} "
                f"partagent le meme fond, « {commun} ». Le skill appelle ca du "
                f"quasi-clonage et demande de varier les fonds d'une crea a "
                f"l'autre, versions claires ou inversees comprises.")


    # Un asset que le skill a nommé mais que la chaîne n'a pas trouvé sur le
    # disque. Ce n'est pas un refus : le skill peut nommer un asset en langage
    # naturel sans fichier. Mais sa règle de parité stricte veut que le prompt
    # ne réclame que des fichiers joints, donc on le montre.
    for entree in plan.get("creas") or []:
        texte = entree.get("_assets_texte") or ""
        cites = re.findall(r"[\w\-./]+\.(?:png|jpe?g|webp|svg|gif|avif)", texte, re.I)
        manquants = [n for n in cites
                     if not any(n.split("/")[-1] in a for a in (entree.get("assets") or []))]
        if manquants:
            alertes.append(f"{entree.get('id')} : asset nommé mais introuvable sur le "
                           f"disque, {', '.join(manquants)}")

    if refus_plan:
        commande.tracer("plan_refuse", motifs=len(refus_plan), creas=len(recevables))
        return {"importees": [], "refus": refus_plan + refus, "alertes": alertes,
                "ce_qui_a_manque": [], "plan_entier_refuse": True}

    for entree in recevables:
        crea = commande.lire_crea(entree["id"])
        # Deux cas de réimport, et ils suivent le 7.2 du cahier des charges.
        # Le prompt change : l'image ne correspond plus, le master tombe et la
        # créa repart en génération. Le prompt est inchangé : seuls la copy ou
        # l'angle bougent, le master validé est conservé tel quel et rien ne
        # se regénère. Sans cette distinction, corriger une faute de copy
        # renvoyait tout le pack au modèle, à deux crédits la créa. La phrase
        # de fin héritée de Cowork s'ignore des deux côtés : sa disparition ne
        # change pas l'image.
        prompt_change = _sans_phrase_de_fin((crea.prompt.scene or "").strip()) \
            != _sans_phrase_de_fin((entree["prompt"] or "").strip())
        crea.angle = entree["angle"]
        crea.copy.accroche = entree["accroche"]
        crea.copy.sous_accroche = entree["sous_accroche"]
        crea.copy.cta = entree["cta"]
        crea.copy.badge = entree["badge"]
        crea.prompt.scene = entree["prompt"]
        crea.prompt.modele = entree["modele"]
        crea.prompt.references = entree["assets"]
        # Les trois décisions que le skill impose par créa. Rangées sur la
        # fiche, elles survivent à la session qui les a prises : la page de
        # suivi peut les montrer, et une reprise sait sur quoi elle revient.
        crea.point_focal = str(entree.get("point_focal") or "").strip()
        crea.fond = str(entree.get("fond") or "").strip()
        crea.tests = {k: str(v).strip()
                      for k, v in (entree.get("tests") or {}).items()}
        crea.structure = str(entree.get("structure") or "").strip().upper()
        if prompt_change or not crea.master:
            crea.master = None
            crea.job_generation = None
            crea.rendus = {}
            crea.audit = {}
            crea.etat = "briefee"
        commande.ecrire_crea(crea)

    manque = plan.get("ce_qui_a_manque") or plan.get("carences") or []
    if manque:
        commande.donnees["ce_qui_a_manque"] = manque
    if recevables:
        commande.donnees["etat"] = "strategie"
    commande.sauver()

    (commande.dossier / "session").mkdir(parents=True, exist_ok=True)
    (commande.dossier / "session" / "plan-recu.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    # Le marqueur que moteur.py preparer exige avant de constituer un lot.
    # Il n'existe que si les créas sont passées par cet import, donc par les
    # gates (banque comprise) : une créa écrite à la main dans creas/ n'y
    # figure pas et ne partira jamais en génération. Les imports successifs
    # s'accumulent, un pack se construit souvent en plusieurs plans.
    chemin_valide = commande.dossier / "session" / "plan-valide.json"
    couvertes: List[str] = []
    if chemin_valide.exists():
        try:
            couvertes = list(json.loads(chemin_valide.read_text(encoding="utf-8")).get("creas") or [])
        except Exception:
            couvertes = []
    couvertes = sorted(set(couvertes) | {c["id"] for c in recevables})
    chemin_valide.write_text(json.dumps({
        "creas": couvertes,
        "plan": hashlib.sha256(fichier.read_bytes()).hexdigest(),
        "date": maintenant(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    commande.tracer("plan_importe", creas=len(recevables), refus=len(refus),
                    alertes=len(alertes), carences=len(manque))
    return {"importees": [c["id"] for c in recevables], "refus": refus,
            "alertes": alertes, "ce_qui_a_manque": manque}


def verifier(ardoise: str) -> List[str]:
    """Rejoue les contrôles sur les créas déjà rangées."""
    commande = Commande.charger(ardoise)
    plan = {"creas": [
        {"id": c.identifiant, "angle": c.angle, "accroche": c.copy.accroche,
         "sous_accroche": c.copy.sous_accroche, "cta": c.copy.cta,
         "badge": c.copy.badge, "prompt": c.prompt.scene,
         "modele": c.prompt.modele, "assets": c.prompt.references,
         "point_focal": c.point_focal, "fond": c.fond, "tests": c.tests,
         "structure": c.structure}
        for c in commande.creas() if c.prompt.scene
    ]}
    _, refus, alertes = controler(plan, commande)
    return refus + alertes


# ---------------------------------------------------------------------------

def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = analyseur.add_subparsers(dest="action", required=True)

    p = sous.add_parser("dossier", help="inventorier ce que le skill trouvera sur le disque")
    p.add_argument("ardoise")

    p = sous.add_parser("importer", help="ranger le plan produit par la session")
    p.add_argument("ardoise")
    p.add_argument("--fichier", required=True, type=Path)

    p = sous.add_parser("verifier", help="rejouer les contrôles sur les créas rangées")
    p.add_argument("ardoise")

    args = analyseur.parse_args()

    try:
        if args.action == "dossier":
            commande = Commande.charger(args.ardoise)
            chemin = ecrire_dossier(commande)
            print(rapport_dossier(dossier_entrees(commande)))
            print(f"\nInventaire écrit : {chemin}")
            return 0

        if args.action == "importer":
            bilan = importer(args.ardoise, args.fichier)
            print(f"{len(bilan['importees'])} créa(s) rangée(s) : "
                  f"{', '.join(bilan['importees'])}")
            for refus in bilan["refus"]:
                print(f"  REFUS   {refus}")
            for alerte in bilan["alertes"]:
                print(f"  ALERTE  {alerte}")
            for ligne in bilan["ce_qui_a_manque"]:
                print(f"  manqué  {ligne}")
            return 1 if bilan["refus"] else 0

        ecarts = verifier(args.ardoise)
        print(f"{len(ecarts)} écart(s)")
        for ecart in ecarts:
            print(f"  {ecart}")
        return 1 if ecarts else 0

    except (FileNotFoundError, ValueError, json.JSONDecodeError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
