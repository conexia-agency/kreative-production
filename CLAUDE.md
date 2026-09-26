# Consignes de session

Chargé au début de chaque session ouverte sur ce dépôt. Vaut pour **toutes les
commandes**, jamais pour une seule.

## Mode Cowork (obligatoire dans Claude Code)

Même système que Cowork, sans l'app Cowork :

1. **Claude juge d'abord** : ouvrir les images avec l'outil **Read** (planches,
   `session/references/`, captures, masters). Pas de plan écrit au jugé.
2. **Toi tu tranches ensuite** : goût, marque, go/no-go.
3. **Atelier visuel** (galerie en grand, pour toi + relecture) :
   ```
   python3 pipeline/atelier.py <ardoise> --ouvrir
   # ou
   python3 kreative.py atelier <ardoise> --ouvrir
   ```
4. **Interdit** : générer un plan par script générique (packshot + CTA répété).
   Chaque créa = concept distinct (formats natifs / ugly inclus si le brief le
   permet, hero, lifestyle, avis, comparaison). C'est ça qui donne la qualité
   Cowork.
5. Après absorption banque : ouvrir l'atelier, **Read** les refs retenues, puis
   seulement écrire `strategie-creative` / le plan.

## Première action, avant tout le reste : `parcours.py suivant`

```
python3 pipeline/parcours.py suivant <ardoise>
```

Le disque dit **la seule commande autorisée**. Tant que la banque n'est pas
ouverte, lue, retenue, extraite et **absorbée** (`banque.py absorber` pour
chaque ref), il est **interdit** d'écrire un plan, d'appeler `strategie-creative.md`
comme point d'entrée, ou de générer. Contourner = pack générique. Vérifier avant
stratégie / génération :

```
python3 pipeline/parcours.py exiger <ardoise> --avant strategie
python3 pipeline/parcours.py exiger <ardoise> --avant generer
```

## Règle zéro : lire `skill/strategie-creative.md` EN ENTIER, à chaque commande

**391 lignes, 18 sections, de la première à la dernière.** Pas un survol, pas les
sections dont on croit se souvenir, pas celles qui semblent utiles sur le moment.
Le fichier entier, avant d'écrire la moindre ligne de stratégie ou de prompt.

C'est la règle qui rend toutes les autres superflues. Tout ce qui suit dans ce
fichier n'existe que parce que le skill n'a pas été lu en entier.

**Depuis le 22/09/2026, elle n'est plus déclarative : `plan.py importer` refuse
le plan entier tant que la lecture n'est pas consignée.**

```
python3 pipeline/skill.py etat <ardoise>     # où on en est
python3 pipeline/skill.py lu <ardoise> --note "ce que les sections lues
                                               changent pour CETTE commande"
```

La consignation porte l'**empreinte** du fichier : si le skill change, la
lecture est à refaire. Le même gate exige que `strategie-creative.md` de la
commande existe, parce que l'étape 3 du process pose les curseurs qui décident
du registre de toute la copy.

Ce qui a motivé ce verrou, mesuré le 22/09 : le skill lu une fois au quatrième
lot de la journée, cinq lots de plus produits sans y retourner, et un scrim
dégradé réinventé de zéro alors qu'il figure dans le skill à la section
« Marier photo + lisibilité ».

**La preuve, mesurée.** Deux packs du client A ont été produits les 19 et
20/09/2026. Deux sections du skill n'avaient jamais été ouvertes :
« Performance Meta & hiérarchie de layout » et « Gestion des assets ». Les deux
échecs viennent exactement de là :

- La formule anti-régénération exacte est dans « Gestion des assets ». Elle dit
  « ne réinvente aucun détail, aucun objet **ni aucun texte** ». Une paraphrase
  affaiblie a été employée à la place, et le modèle a réécrit les étiquettes des
  flacons, inventant un format 80 ml puis 78 ml qui n'existe pas au catalogue.
- « Le prompt de génération » dit de **nommer le format visuel** dans le prompt.
  À la place, le prompt citait la référence de la banque, ce qui a produit des
  décalques au lieu de créas.
- « Performance Meta » impose de faire varier l'architecture d'une créa à
  l'autre, de varier les fonds clairs et sombres, et de passer trois tests sur
  chaque créa : rareté, lecture muette, micro-question. Rien de tout cela
  n'avait été appliqué.

Aucun de ces problèmes n'appelait un arbitrage de l'utilisateur. Tous étaient
écrits dans le skill.

**Les sections à ouvrir**, pour vérification : Contexte d'exécution · Règles d'or
· Les échelles continues · Audit du site · Ce qui fait GAGNER et PERDRE ·
Performance Meta & hiérarchie de layout · Le prompt de génération · Lecture de la
bibliothèque Meta · Banque de créas de référence · Process · Répertoire d'angles ·
Packs · Format de sortie · Style de sortie.

**Le process du skill se suit dans l'ordre**, étapes 0 à 6, sans en sauter. La
synthèse stratégique de l'étape 3 pose les curseurs qui décident du registre de
toute la copy : la sauter, c'est écrire à l'aveugle.

## La banque nourrit le pack globalement, jamais créa par créa

Le skill est explicite :

> « La banque nourrit le pack globalement, **jamais créa par créa**. Tu ne colles
> pas une référence à une créa, comme s'il fallait une inspiration par visuel. Tu
> absorbes l'ensemble de ta sélection et tu composes le pack à partir de ce
> vocabulaire visuel, adapté au client. »

**Les deux fautes symétriques, toutes deux constatées :**

- **Ignorer la banque** et inventer le design. Donne des photographies de produit
  génériques avec du texte posé dessus, toutes bâties pareil. C'est le pack du
  19/09 : vingt-quatre références citées, aucune utilisée.
- **Coller une référence par créa** et la transposer littéralement. Donne des
  décalques qui ne tiennent pas, parce qu'une construction pensée pour un autre
  produit et un autre message ne se transpose pas telle quelle. C'est le pack du
  20/09.

Ce qu'on reprend : la structure de layout, la composition, le traitement du fond
et de la matière, le rapport texte/image, le type de mise en scène, le niveau de
finition. Une même référence peut irriguer plusieurs créas, et une créa peut en
croiser plusieurs. Ce qui reste non négociable, c'est que les créas du pack
soient radicalement différentes entre elles.

**« Globalement » n'autorise pas à inventer la structure.** La phrase interdit
d'agrafer une référence par visuel et de la décalquer ; elle ne permet pas de
composer une mise en page de tête. Les références sont des structures qui ont
déjà performé : chaque créa en reprend une, et il n'y a pas de créa sans
structure source. Mesuré le 25/09 sur la page blanche du client A : la phrase lue
comme une permission a donné quatre créas inventées sur douze (éprouvettes,
veste et clés, pipette, un chiffre posé sur du velours), avec des CTA sans
logique ; ce sont les quatre que l'équipe a rejetées, « du texte, une image au hasard
qui n'a aucun rapport, et le CTA au pif ». Refaites chacune sur une référence
absorbée, elles sont passées.

La différence entre reprendre et décalquer : on reprend l'emplacement des zones
(titre, produit, preuve, CTA), leurs proportions, le type de fond, le rapport
texte/image et la présence ou l'absence de bouton. On ne reprend jamais la copy,
les couleurs, les polices, les produits ni la marque de la référence. Le prompt
décrit la structure zone par zone, sans jamais citer l'identifiant de la
référence (ça, c'est ce qui produit le décalque).

**Depuis le 25/09, `plan.py importer` l'exige.** Chaque créa du plan porte un
champ `structure` : l'identifiant de la référence dont elle reprend la
construction (ex. `"structure": "EC1-07"`), qui doit être une référence absorbée
de la commande. Sans lui, ou avec une référence non absorbée, la créa est
refusée. Le champ est rangé sur la fiche. Les autres champs exigés par créa, au
même titre : `point_focal`, `fond`, et `tests` (`rarete`, `lecture_muette`,
`micro_question`).

## La copy ne se reprend JAMAIS d'une référence

> « Ce que tu ne reprends jamais : ses couleurs, ses polices, **sa copy**, sa
> marque, ses produits, ses visuels. Tout ça vient du client. »
> « Les headlines sont toujours **dérivées de l'angle et du brief, jamais
> plaquées**. »

Le skill liste des **motifs** de headline : affirmation définitive,
question-douleur, hook négatif, secret ou curiosité, douleur incarnée en une
phrase, différenciation, bénéfice en contraste. Le motif se réutilise. **La
phrase de la référence, jamais.**

Mesuré le 20/09 sur le client A : cinq accroches sur dix-huit étaient des
traductions de la banque. « Notre flacon n'est pas comme les autres » venait de
EC1-07, « N'achetez pas ce parfum » de EC1-13, « Notre politique de retour ? Vous
n'en aurez pas besoin » de UG6-02. Elles sonnaient creux parce qu'elles ne
sortaient pas du brief du client.

Rappels de dosage, du skill : headline courte et frappante, viser moins de dix
mots, si un mot peut sauter il saute. Sous-titre d'une ligne, deux au maximum,
jamais trois, et il ajoute UNE précision. Le pavé est la faute numéro un.

## L'analyse du site se fait au navigateur

**Chrome DevTools MCP est l'outil d'analyse. Playwright ne l'est pas.**

`pipeline/scraper.py` pilote Playwright, télécharge et range les assets,
packshots haute définition compris, et mesure la charte dans `charte-site.json`.
C'est un outil de **récolte et de mesure**, obligatoire, mais ses captures ne
valent pas analyse : elles figent la page au chargement, accordéons fermés,
onglets non cliqués, pop-up par-dessus le contenu.

**Ordre, pour toute commande :** `scraper.py aspirer` récolte et mesure, puis
Chrome DevTools ouvre le site et l'analyse réellement, pages produit et FAQ
comprises, en dépliant avant de capturer et en relevant les valeurs de DA avec
`evaluate_script`, puis la bibliothèque publicitaire Meta.

Le 19/09, vingt-cinq captures produites et une seule ouverte. Ont été manqués :
le badge UNISEXE des fiches produit alors que toute la copy était au féminin, la
tenue officielle « jusqu'à 10h » alors qu'une créa en promettait seize, une
troisième police, les mentions cruelty free et vegan, une promotion en cours, et
le portrait de marque du hero, caché par une pop-up, d'où la conclusion erronée
que le client n'avait aucune photographie lifestyle.

**Navigateur indisponible : le run s'arrête**, comme le veut le skill à son
étape 0 (« Navigateur indisponible, analyse visuelle impossible, run
interrompu »). Jusqu'au 26/09 ce fichier autorisait à continuer sur les
captures : c'est ce qui s'est passé le 25/09 sur le client A, contre la lettre du
skill. Aligné sur lui, décision de l'équipe. L'étape se consigne avec
`pipeline/outillage.py consigner` ; le parcours s'arrête sur `interrompu` tant
que le navigateur est déclaré indisponible.

## La bibliothèque publicitaire Meta se consulte à chaque fois

Sans elle, on ignore quels angles le client diffuse déjà et on risque de les
redoubler. Elle reste non bloquante : si elle ne charge pas ou exige une
connexion, on abandonne après deux tentatives, on le dit en une ligne, et on
poursuit. Ce qui n'est pas permis, c'est de ne pas essayer.

**Depuis le 26/09, la tentative se consigne** avec `pipeline/metaads.py
consigner` (`releve`, `aucune` ou `echec`), dans `marque/meta-ads.json`. Le
parcours propose l'étape `meta_ads` avant la stratégie, et `plan.py importer`
refuse le premier plan sans cette trace. Mesuré le 25/09 sur la page blanche
le client A : navigateurs indisponibles, bibliothèque jamais tentée, et rien ne l'a
vu ; le pack s'est écrit sans savoir que les angles « élégance et amour » et le
cadeau étaient déjà tournés.

## Le texte peint par le modèle

Contradiction levée le 19/09/2026 : la docstring de `pipeline/etat.py` datait
de l'architecture abandonnée (copy posée par un compositeur). Elle dit
désormais la même chose que `pipeline/plan.py` : le texte est peint par le
modèle, la copy figure mot pour mot dans le prompt, et `plan.py` le vérifie.

Tant que le texte est peint, deux précautions :

- **Ne jamais nommer une police dans la phrase qui porte le texte à afficher**, et
  ne jamais employer un mot de liaison comme « puis » entre deux textes à
  afficher. Le modèle les peint. Constaté quatre fois : « DM Sans: » devant le
  nom d'un client, « Glacial » dans un titre, « puis » dans une pastille.
  `plan.py` garde contre ce cas, et sa liste contient bien DM Sans, Glacial
  Indifference et IBM Plex Mono : elle refuse le plan. Vérifié le 22/09.
- **Relire chaque master au zoom, jamais sur la vignette.** Le modèle reconstruit
  les étiquettes des flacons passés en référence et se trompe environ quatre fois
  sur dix. Cadrer les produits pour que les mentions légales ne soient pas
  lisibles réduit le risque à la source.
- **Donner le texte plutôt qu'interdire de l'inventer.** Mesuré le 22/09 sur
  le client A : trois lots portaient la formule anti-régénération complète, y compris
  le « ni aucun texte », et le modèle a quand même écrit 80 ml, 30 ml puis
  « 1.7 fl. es. » pour un produit qui n'existe qu'en 50 ml. Le quatrième lot a
  écrit le contenu exact de l'étiquette dans le prompt, ligne par ligne, en
  précisant qu'il est déjà imprimé sur l'asset fourni : les deux étiquettes
  lisibles sont sorties justes. L'interdiction seule ne suffit pas, la consigne
  positive change le résultat.

## Un master ne s'écrase jamais sans reprise déclarée

Mesuré les 21 et 22/09 sur le client A. Trois lots successifs ont visé les
identifiants `c01` à `c10`, et quatre masters du premier pack ont été détruits,
leurs verdicts de relecture remplacés. `moteur.py recolter` écrivait par-dessus
sans rien vérifier, et le journal n'enregistrait qu'un `master_genere`
ordinaire, comme pour une première génération.

Depuis le 22/09, `recolter` **refuse** d'écrire sur un master existant dont la
créa est en état `master_ok`. Régénérer reste le cas courant, mais une reprise
se déclare :

```
python3 pipeline/etat.py reprise-visuel <ardoise> --crea <id>
```

Une créa **nouvelle** prend un identifiant nouveau. Si le plan vise un
identifiant qui n'existe pas, `plan.py` le refuse : créer la fiche d'abord, par
l'API de la chaîne (`Commande.ecrire_crea`), jamais en écrivant dans `creas/`
à la main.

## Archiver hors de la chaîne laisse un trou de trois jours

Le 19/09 à 19h27, un plan de 48 créas venait d'être importé, et `creas/` ainsi
que `masters/` ont été déplacés à la main vers
`session/archive-plan-v3-20260919-1927/`. Rien n'était perdu, mais rien ne le
disait non plus : aucune ligne au journal, et la commande a continué à déclarer
48 générations pour 10 fiches présentes pendant trois jours. C'est ce silence
qui a mené les lots suivants à réutiliser les identifiants survivants.

Depuis le 22/09, `parcours.py suivant` affiche l'écart et nomme l'archive :

```
  ECART FICHES    la commande declare 48 generations, le disque porte 14 fiche(s)
                  48 fiche(s) sont dans session/archive-plan-v3-20260919-1927
```

Ce n'est pas bloquant, archiver est une décision légitime. C'est un écart porté
à l'écran, avec l'endroit où regarder.

## La copy est écrite par la session

Décision de l'équipe le 26/09/2026 : titre, sous-titre et CTA sont rédigés par la
session qui applique le skill, comme leur skill le prévoit. Aucun appel à Grok
dans la chaîne. Les anciens scripts Grok (`copywriter.py`, `angles.py`) sont
dans `_ecarte-de-leur-skill/pipeline/`, avec leur motif dans `POURQUOI.md`.

## La fin de chaîne

Le parcours ne s'arrête plus à l'audit. Mesuré le 25/09 sur la page blanche
le client A : douze créas validées sont restées en 1:1, jamais déclinées, jamais
livrées, parce que rien ne proposait la suite. Depuis le 26/09,
`parcours.py suivant` enchaîne, en lisant le disque :

1. `reprendre` : une créa refusée à la relecture, reprise à déclarer ;
2. `generer` : une créa planifiée sans master, y compris après une reprise ;
3. `relecture` : un master sans verdict valable ;
4. `audit` : pas d'audit sans échec postérieur au dernier master rangé ;
5. `formats` : une créa sans son 4:5 et son 9:16 ;
6. `formats_etendre` : les formats que le bord du master ne permet pas de
   prolonger, à étendre par le connecteur (payant, à valider avant) ;
7. `livrer` : le dossier de remise et la notification ;
8. `publier` : seulement si les cinq variables `PUBLIE_*` sont posées ;
9. `livree` : état final. Sans `PUBLIE_*`, le parcours le dit et s'arrête là ;
   avec, il propose `retours.py` pour relever les commentaires de la plateforme.

`kreative.py audit` écrit désormais l'événement `audit` au journal : c'est lui
que le parcours lit pour savoir que l'audit est passé.

## Ce que la chaîne contrôle du skill, depuis le 26/09

Un audit du skill exigence par exigence, le 26/09, a trouvé des étapes que rien
ne tenait. Elles le sont désormais :

- **Synthèse** (`skill.py`) : les huit rubriques de l'étape 3 (niche, avatar,
  problématique centrale, objection clé, température, positionnement, ton,
  curseurs), et une section « Couverture du brief » qui cite chaque champ
  rempli du formulaire avec ce qu'il est devenu.
- **Pack** (`plan.py importer`) : deux créas au moins par angle (refus),
  nombre d'angles du pack (alerte), assets rangés dans `assets/` sous un numéro
  global `PJNN-` (refus) et de résolution suffisante (alerte), titre sous dix
  mots et sous-titre d'une douzaine (alerte, le skill parle d'un curseur), la
  police de la charte sur tous les prompts (alerte).
- **Sortie** (`sortie.py`) : le « Format de sortie » du skill, assemblé depuis
  la synthèse (sections synthèse stratégique, angles, garde-fous) et les fiches
  créa, prompts à l'octet près. Il part dans le dossier de remise sous
  `STRATEGIE-ET-PROMPTS.md`.

Un écart reste assumé : la phrase de fin « Nano Banana Pro en restant gratuit »
n'est pas écrite dans les prompts (décision du 19/09), et Evan doit en être
informé.
