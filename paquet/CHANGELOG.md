# Journal des versions

## 1.1.0, 26 septembre 2026

La chaîne va maintenant du formulaire jusqu'au pack livré, pilotée par une
seule boucle : `parcours.py suivant`, jusqu'à l'étape `livree`.

- Fin de chaîne : après l'audit, le parcours propose les formats 4:5 et 9:16,
  leur extension par le connecteur quand le bord du master n'est pas
  uniforme, la livraison, puis la publication si les accès `PUBLIE_*` sont
  posés. Il revient seul à la reprise quand une créa est refusée.
- Gates : lecture intégrale du skill consignée (`skill.py`), fichiers du
  client tous ouverts (`dossier.py`), banque sous registre (`banque.py`),
  verdict de relecture par créa au zoom (`loupe.py`, `relecture.py`).
- Chaque créa part de la structure d'une référence absorbée : champ
  `structure` exigé par `plan.py importer`.
- La copy est écrite par la session, comme le prévoit le skill de stratégie.
- Bibliothèque publicitaire Meta : la tentative se consigne (`metaads.py`),
  exigée avant le premier plan ; un échec motivé est recevable.
- Aligné sur le skill : navigateur indisponible, le run s'arrête (`outillage.py`) ;
  le « Format de sortie » est assemblé (`sortie.py`) et livré avec le pack.
- Contrôles ajoutés : rubriques de la synthèse et couverture du brief, deux
  créas par angle, assets numérotés `PJNN-` et de résolution suffisante,
  longueur de la copy et police de la charte (alertes).
- Prérequis : tesseract n'est plus nécessaire, Pillow l'est.
- Le paquet ne contient que les fichiers versionnés du système.

## 1.0.0, 17 septembre 2026

Premier empaquetage de la chaîne complète.

- Orchestration : relevé Zite avec fusion des resoummissions sous 30 jours,
  aspiration du site aux styles calculés, stratégie, devis au tarif mesuré,
  génération par le MCP Higgsfield, gate OCR, page de suivi.
- Skill de stratégie créative v2 (17/09), adapté à la chaîne : la banque
  pilote la construction et jamais la marque du client, aucun quadrillage
  sans source, aucune scène photographique générée pour une agence, un SaaS
  ou un service.
- Doctrine des prompts entièrement mesurée : aucun délimiteur autour du
  texte, accents écrits, clause de fin obligatoire, une référence par créa,
  i2i au même prix que t2i.
- Trois arrêts : brief incomplet, site inexploitable, plafond de crédits.
- `kreative.py verifier` : neuf contrôles de poste, chacun avec son remède.
- Espace de travail séparé du skill (`KREATIVE_TRAVAIL`), aucun secret dans
  le dossier.
