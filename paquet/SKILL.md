---
name: kreative-production
description: Pilote la chaîne de production Kreative de bout en bout, du formulaire client rempli jusqu'au pack livré en trois formats. À utiliser quand un nouveau formulaire arrive, quand l'utilisateur demande de relever les commandes, de produire, reprendre ou livrer un pack de créas pour un client, ou nomme une commande existante par sa marque. Couvre le relevé Zite, l'aspiration du site, la banque de références, la stratégie et la copy, le devis en crédits, la génération par le MCP Higgsfield, la relecture au zoom, l'audit, les formats 1:1, 4:5 et 9:16, la livraison et la revue. Ne pas utiliser pour créer une vidéo, ni pour un client hors Kreative, ni pour modifier la plateforme de revue elle-même.
---

# Production Kreative

La chaîne complète : un formulaire rempli entre, un pack de créatives Meta
livré en trois formats sort, et personne n'intervient entre les deux sauf trois
arrêts prévus. Tout se fait en **français**, accents compris.

**Comment elle s'actionne.** Une seule boucle, jusqu'au bout :

```
python3 scripts/pipeline/parcours.py suivant <ardoise>
```

Le parcours lit le disque et donne LA prochaine action. Tu l'exécutes, tu
relances `parcours.py suivant`, et ainsi de suite jusqu'à l'étape `livree`.
Tu ne sautes aucune étape et tu n'en inventes aucune : ce que le parcours ne
propose pas n'est pas encore autorisé. Ce skill tourne dans une session Claude
Code, pas dans un cron : lire les images, écrire les prompts et juger les
masters demandent une session.

## Objectif

Kreative vend des packs de créatives statiques Meta. Ce skill orchestre leur
production : relever les formulaires, construire le dossier client, aspirer le
site, écrire la stratégie, la copy et les prompts, chiffrer, générer par le
MCP Higgsfield, relire, auditer, décliner, livrer. Résultat attendu : chaque
créa en 1:1, 4:5 et 9:16 au texte peint, relue au zoom, audit franchi, dossier
de remise créé et notifié, coût réel journalisé.

## Quand utiliser ce skill

- « Un nouveau formulaire est arrivé », « relève les commandes », « regarde
  s'il y a du nouveau côté Zite »
- « Produis le pack de [marque] », « regénère c07 de [marque] », « où en est
  la commande [marque] ? »
- « Combien coûterait le pack de [marque] ? » (devis sans générer)

## Quand NE PAS utiliser ce skill

- Une demande de vidéo, d'audio ou de 3D : la chaîne ne produit que des
  créatives statiques.
- Un client hors Kreative : ce skill porte les règles et la banque d'UNE
  agence, il n'est pas générique.

## Quick start

```
set -a && source .env && set +a               # les clés, jamais en clair
python3 scripts/kreative.py verifier          # 9 contrôles, tout doit être OK
python3 scripts/pipeline/zite.py relever      # les nouveaux formulaires
python3 scripts/kreative.py etat <ardoise>    # où en est une commande
python3 scripts/pipeline/parcours.py suivant <ardoise>   # LA prochaine action
```

## Règles d'or

1. **Trois arrêts, pas un de plus.** Brief incomplet sur une valeur
   indéductible, site inexploitable (motif écrit dans `marque/scraping.json`),
   devis au-dessus du plafond (120 crédits par défaut). Tout le reste se
   tranche, se fait, et se signale en fin de sortie dans « Ce qui a manqué ».
2. **Le disque pilote l'ordre : `parcours.py suivant` d'abord (mode Cowork).**
   Avant toute stratégie ou génération :
   `python3 scripts/pipeline/parcours.py suivant <ardoise>`.
   `exiger --avant strategie|generer` refuse si la banque n'est pas ouverte,
   lue, retenue, extraite et absorbée. Puis : ouvrir
   `python3 scripts/pipeline/atelier.py <ardoise> --ouvrir`, **Read** les
   images (planches, refs, captures), lire `references/strategie-creative.md`
   EN ENTIER, ecrire le plan creatif (concepts distincts, pas un script
   packshot), `plan.py importer`. Claude juge les images ; l'humain tranche.
   Contourner = pack generique.
3. **Chaque créa part de la structure d'une référence absorbée.** Les créas
   de la banque sont des structures qui ont déjà performé : on reprend
   l'emplacement des zones (titre, produit, preuve, CTA), leurs proportions,
   le type de fond, le rapport texte/image, la présence ou l'absence de
   bouton. On ne reprend jamais la copy, les couleurs, les polices ni les
   produits de la référence. Chaque créa du plan porte un champ `structure`
   avec l'identifiant de cette référence (`"structure": "EC1-07"`) ;
   `plan.py importer` refuse une créa sans lui. Le prompt décrit la structure
   zone par zone et ne cite jamais l'identifiant.
4. **La copy est écrite par la session**, dans le ton et le tu/vous du
   client, selon les règles de longueur de `references/strategie-creative.md`.
   Tout chiffre vient du brief ou du site.
5. **La génération passe par le MCP Higgsfield, uniquement.** Jamais la CLI,
   jamais une API directe. Le protocole d'appel est
   décrit dans `references/chaine-kreative.md`.
6. **Les fichiers locaux font foi.** L'état d'une commande est
   `commandes/<ardoise>/commande.json` et ses créas ; la plateforme de revue
   n'est qu'une projection. Un doute se lève en lisant le disque, pas en
   se souvenant.
7. **Le devis se valide avant de générer.** `preparer` écrit le lot et son
   coût au tarif mesuré (`scripts/pipeline/couts.py`) ; au-dessus du plafond,
   c'est un arrêt. Le solde se relève avant et après chaque lot, et
   `recolter` journalise l'écart : c'est ce qui garde la table juste.
8. **Un prompt est un champ de fichier, jamais une chaîne assemblée au vol.**
   Ce que `prompts` affiche est ce qui part au modèle, à l'octet près.
9. **Aucun secret ne s'écrit** dans un fichier livrable, un commit ou une
   sortie : les clés vivent dans le `.env` de l'espace de travail et se
   référencent par leur nom.
10. **Zéro tiret cadratin, zéro emoji** dans tout ce qui est produit.

## Workflow

Étape 0, une fois par poste : `python3 scripts/pipeline/sante.py` puis
`python3 scripts/kreative.py verifier`. Chaque ligne dit ce qui est branché,
ce qui manque et le remède (détail : `references/installation.md`). Verdict
« ne doit pas tourner » : on répare, on ne contourne pas.

0. **À chaque reprise d'une commande :**
   `python3 scripts/pipeline/parcours.py suivant <ardoise>`  -  une seule
   prochaine action, décidée par le disque. Ne pas sauter à la stratégie.

1. **Relever et ouvrir.** `python3 scripts/pipeline/zite.py relever` simule et
   affiche ce qui arriverait ; avec `--appliquer`, il range chaque soumission
   dans `commandes/_zite/`, ouvre la commande (`commandes/<ardoise>/` : brief
   figé, pièces jointes rangées) et télécharge les fichiers. Une deuxième
   soumission de la même marque sous 30 jours complète la commande existante :
   le brief le plus récent gagne, les pièces jointes s'accumulent. Le mode
   sans personne, qui enchaîne tout : `python3 scripts/orchestrateur.py
   tourner`.
2. **Aspirer le site.** `python3 scripts/pipeline/scraper.py aspirer
   <ardoise>` :
   pages parcourues dans Chromium, charte MESURÉE sur les styles calculés
   (`marque/charte-site.json`), textes (`site.json`), images dédoublonnées et
   indexées (`assets-site/index.json`), candidats logo scorés, une capture
   par page dans `marque/captures/`. `scraper.py` est la RÉCOLTE et la
   MESURE, obligatoires ; il ne vaut pas analyse : ses captures figent la
   page au chargement, accordéons fermés, pop-up par-dessus. Ensuite,
   ANALYSER réellement : ouvrir le site avec le MCP Chrome DevTools, pages
   produit et FAQ comprises, déplier avant de capturer, relever la DA avec
   `evaluate_script`, puis tenter la bibliothèque publicitaire Meta (non
   bloquante : deux essais, on le dit en une ligne, on poursuit). La tentative
   se consigne, quelle qu'en soit l'issue, avec
   `python3 scripts/pipeline/metaads.py consigner <ardoise> --statut
   releve|aucune|echec` : les captures dans `marque/meta-ads/`, une note sur
   le registre et les angles déjà tournés, ou le motif de l'échec. Le parcours
   et `plan.py importer` exigent cette trace avant le premier plan ; un échec
   motivé passe, l'absence de tentative non. **Navigateur indisponible : le
   run s'arrête** (étape 0 du skill). Le parcours propose d'abord l'étape
   `outillage` : `navigate_page` vers le site, `take_screenshot` enregistré
   dans `marque/navigateur/`, puis `python3 scripts/pipeline/outillage.py
   consigner <ardoise> --navigateur ok --capture <chemin>`. S'il ne répond
   pas : `--navigateur indisponible --motif "..."`, et le parcours s'arrête
   sur `interrompu`. Le MCP Chrome ne lit jamais des
   fichiers locaux. Si le site refuse le scraping, le motif est écrit dans
   `marque/scraping.json` : c'est l'arrêt 2 si le brief seul ne porte pas
   la DA.
3. **Ouvrir la banque de références, sous registre (et l'absorber).**
   Suivre `parcours.py suivant` : `banque.py ouvrir` liste la famille et les
   planches. Ouvrir TOUTES les planches (outil Read), puis `lue`, `retenir`,
   `extraire`. Ensuite, pour CHAQUE `session/references/<ref>.jpg` : Read le
   fichier, puis
   `banque.py absorber <ardoise> --ref <id> --vu "une phrase layout/fond/texte"`.
   Sans absorption, `verifier` / `plan.py importer` / `moteur.py preparer`
   refusent. La banque nourrit le pack **globalement** : on n'agrafe pas une
   référence par visuel pour la décalquer. Mais chaque créa part bien de la
   structure d'une référence absorbée (règle d'or 3) : « globalement »
   n'autorise pas à inventer une mise en page.
4. **La stratégie (écriture Cowork, pas un script).** Ouvrir
   `atelier.py <ardoise> --ouvrir`. Read les refs absorbees et captures.
   Lire `references/strategie-creative.md` EN ENTIER. Ecrire le plan au
   format skill : chaque crea = concept distinct (hero, lifestyle, avis,
   comparaison, native/ugly si pertinent), posé sur la structure d'une
   référence absorbée. Chaque créa du plan porte `structure`, `point_focal`,
   `fond` et `tests` (`rarete`, `lecture_muette`, `micro_question`), et sa copy
   figure mot pour mot dans son prompt. Interdit : plan generique
   packshot+CTA. Puis
   `python3 scripts/pipeline/plan.py importer <ardoise> --fichier <plan.json>`.
   Un refus cite la règle enfreinte : on corrige et on réimporte.
   Jamais ecrire `creas/` a la main. Relecture :
   `python3 scripts/kreative.py prompts <ardoise>`. Regenerer l'atelier
   apres les masters pour juger en grand.
5. **Chiffrer et décider.** `python3 scripts/pipeline/moteur.py preparer
   <ardoise>` écrit le lot dans `jobs/` avec son devis. Il REFUSE un plan qui
   n'est pas passé par `plan.py importer` ou une banque sans registre : c'est
   le verrou, pas une erreur à contourner. Plafond dépassé : arrêt 3.
   Sinon : GO.
6. **Générer, par le MCP.** Relever `balance`, monter les références
   (`media_upload`, PUT, `media_confirm`), lancer `generate_image_batch` par
   paquets de 12 maximum, attendre `jobs_wait`, télécharger chaque
   `result_url` immédiatement (les rendus expirent en sept jours). Le protocole est dans
   `references/chaine-kreative.md`.
7. **Récolter.** `python3 scripts/pipeline/moteur.py recolter <ardoise>
   --resultats <fichier.json> --solde-avant X --solde-apres Y` range les
   masters et journalise le coût réel. Chaque entrée du fichier de résultats
   porte `crea`, `fichier`, **`job_id`** et **`references_jointes`**, la liste
   des fichiers réellement passés en référence à l'appel. Les deux derniers
   sont obligatoires et le master est refusé sans eux, avec contrôle de parité
   contre les références demandées. Sans cette trace, une photo client repeinte
   n'est attribuable ni au modèle ni à la jointure, et le défaut se reproduit
   au pack suivant.
8. **Relire, puis auditer.** Dans cet ordre : l'audit ne lit plus les images,
   c'est toi qui lis. `python3 scripts/pipeline/loupe.py <ardoise>` découpe
   chaque master en quatre zones qui se recouvrent, dans `session/loupe/`.
   Ouvre chaque zone une par une avec Read : un texte peint ne se juge jamais
   sur la vignette entière, toutes les fautes se voient au zoom. Tu ne
   transcris pas, tu juges : une police peinte devant un nom, un mot de
   liaison peint dans une pastille, une étiquette réinventée hors catalogue
   sont des fautes qu'aucune comparaison de mots ne voit. Puis consigne, par
   créa : `python3 scripts/pipeline/relecture.py verdict <ardoise> <crea>
   --etat ok|refus --constat "ce qui a été lu, et sur quelle zone"`. Enfin
   `python3 scripts/kreative.py audit <ardoise>` : C1 échoue sur toute créa
   sans verdict, ou dont le master a été régénéré depuis son verdict.
   Une créa refusée : `python3 scripts/pipeline/etat.py reprise-visuel
   --marque <ardoise> --crea <id>`, corriger la cause du refus dans le prompt
   (pas un nouveau tirage au sort), réimporter, regénérer, relire. Le parcours
   y ramène tout seul (étape `reprendre`).
9. **Montrer.** `python3 scripts/kreative.py page <ardoise>` écrit la page de
   suivi ; les masters restent dans `commandes/<ardoise>/masters/`.
10. **Décliner.** `python3 scripts/kreative.py formats <ardoise>` tire le 4:5
    et le 9:16 de chaque master carré en ajoutant du cadre, sans toucher au
    carré. Quand le bord du master n'est pas uniforme, prolonger ferait des
    traînées : la créa part dans `formats/a-etendre.json` et le parcours
    propose `formats_etendre`. Chiffrer d'abord (`outpaint_image` avec
    `get_cost`), puis étendre par le MCP (haut et bas seulement), puis
    `python3 scripts/pipeline/formats.py ranger-extension <ardoise> --crea
    <id> --format 4x5|9x16 --fichier <image>` et
    `python3 scripts/pipeline/formats.py verifier <ardoise>`.
11. **Livrer.** `python3 scripts/kreative.py livrer <ardoise>` construit le
    dossier de remise hors de l'espace de travail (`KREATIVE_LIVRAISONS`,
    défaut `~/Kreative/livraisons`), fichiers nommés pour un humain, et
    notifie (webhook `KREATIVE_NOTIF_WEBHOOK`, sinon une note dans le dossier).
    Le pack est livré : le parcours passe à `livree`. Juste avant, le parcours
   propose `sortie` : `python3 scripts/pipeline/sortie.py assembler
   <ardoise>` assemble le « Format de sortie » de
   `references/strategie-creative.md` (synthèse, angles, créatives et
   prompts, garde-fous) ; il part dans le dossier de remise sous
   `STRATEGIE-ET-PROMPTS.md`. La synthèse doit donc porter une section
   « Garde-fous » cochée et une section « Couverture du brief » qui cite
   chaque champ du formulaire.
12. **Publier en revue, étape FACULTATIVE.** Le parcours ne la propose que si
    les cinq accès `PUBLIE_*` sont posés. Alors :
    `python3 scripts/pipeline/publier.py <ardoise> --client <slug> --dry-run`
    puis sans `--dry-run`. Les commentaires de l'équipe redescendent avec
    `python3 scripts/pipeline/retours.py <ardoise> --client <slug>`, et chaque
    reprise se range dans `reprises/` sans rien écraser.

## L'espace de travail

Le skill est immuable ; les données clientes vivent ailleurs. L'emplacement
se choisit avec la variable `KREATIVE_TRAVAIL` (défaut : `~/Kreative`), et
`commandes/` s'y crée au premier usage. Le `.env` (dont `ZITE_API_KEY`) vit
là aussi, jamais dans le skill.

## En cas de doute

- Le métier créatif (angles, copy, prompts, assets, banque de références) :
  `references/strategie-creative.md`.
- L'écriture des prompts : `references/strategie-creative.md`, et elle
  seule. Une exception, décidée le 19/09/2026 : sa phrase de fin « Nano
  Banana Pro en restant gratuit » ne s'écrit plus, le connecteur fixe le
  modèle et la facturation par ses paramètres d'appel.
- Le poste, les clés, les prérequis : `references/installation.md`.
- La carte du système, module par module : `references/architecture.md`.
