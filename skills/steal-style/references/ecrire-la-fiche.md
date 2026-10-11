# Écrire la fiche

La fiche est le seul document qui fait foi. Le gabarit, le skill et les contrôles la lisent. Elle se remplit dans `STYLE/FICHE.md`, à partir du modèle déjà en place.

## Règles d'écriture

- **Une règle, une ligne, une preuve.** Chaque ligne finit par son niveau : *Mesuré*, *Compté*, *Lu* ou *Choix*, avec le nombre de cas quand il y en a.
- **Écrire pour quelqu'un qui monte**, pas pour quelqu'un qui analyse. « Le visage ne reste jamais plus de 16 s » et non « la distribution des blocs visage présente un maximum de 16 s ».
- **Des médianes, pas des moyennes.** Une médiane avec sa fourchette (25 % – 75 %) dit ce qu'on fait d'habitude et de combien on s'en écarte.
- **Arrondir à la précision de la mesure.** Une image dure 33 ou 40 ms : écrire 240 ms, pas 237.
- **Aucun chiffre sans fichier.** Avant d'écrire une valeur, la retrouver dans `MESURES.md`, `mesures.json` ou un CSV.
- **Dire ce qu'on n'a pas trouvé.** Une section vide s'écrit « Non mesuré » avec la raison.

## Section par section

| Section de la fiche | D'où ça vient | Ce qu'on y écrit |
|---|---|---|
| **Comment lire les preuves** | — | Le tableau des quatre niveaux. Ne pas le retirer. |
| **1. Le style en trois phrases** | Tout | Qui porte quoi (le visage, l'animation, les extraits), ce qui rend le style reconnaissable, ce qu'il refuse. Trois phrases, pas quatre. |
| **2. Les mots de la fiche** | Étiquettes | 5 à 8 mots définis une fois (bloc, séquence, plan, animation…), puis tenus dans toute la fiche. |
| **3. Quand animer** | `croiser`, `phrases.csv`, `mesures.json` → `phrases`, `visage`, `sequences_sans_visage`, `parts_par_tiers` | Le tableau de décision, ses arbitrages, ce que dit le visage, le rythme, les différences entre début, milieu et fin. |
| **4. Comment animer** | `mouvements.csv`, `mesures.json` → `camera`, `entrees`, `mouvements` ; planches | Les règles du mouvement, le tableau des valeurs, la composition (où se posent les choses). |
| **5. Le visage** | `mesures.json` → `visage` ; planches | Cadrage, zoom lent ou non, texte posé dessus, coupes sautées. |
| **6. Le son de la référence** | `mesures.json` → `voix`, `son` | Débit, pauses, présence d'un fond sonore. Dire clairement ce qui n'est pas mesuré. |
| **7. Les types de scène** | Sous-types des plans | Liste **fermée**. Pour chacun : sa fonction, combien de fois, quand l'employer. |
| **8. Ce que le style ne fait jamais** | Planches, types d'animation absents | Les refus : c'est souvent la moitié du style. Chaque ligne se vérifie (« 0 rebond sur 278 animations »). |
| **9. Contrôler un montage fini** | `mesures.json` → `controle_propose` | Le tableau des tolérances. Ce sont des *Choix* appuyés sur des mesures. |
| **10. Ce qui reste incertain** | Tout ce qui a résisté | Les mesures peu fiables, les règles sous 75 %, ce qu'une seule vidéo ne permet pas de dire. |
| **11. Désaccords tranchés** | — | Si deux mesures ou deux lectures se contredisent : laquelle on a retenue et pourquoi. |
| **12. Les valeurs pour le gabarit** | Sections 3 à 6 | **Un seul** bloc JSON. Le gabarit et les contrôles le lisent. |
| **Sources** | `meta.json` | Le lien, la date de l'analyse, la liste des fichiers de preuve. |

## Le tableau de décision (section 3)

C'est une suite de questions posées dans l'ordre. On s'arrête au premier « oui ».

```
| N° | La phrase…                                   | Alors            | Preuve              |
| 1  | porte un chiffre, une date, un nom, une source | animation        | Compté : 29 sur 31  |
| 2  | …                                            | …                | …                   |
| 7  | sinon                                        | visage           | Compté : 63 sur 65  |
```

Pour le construire :

1. Partir du tableau croisé nature × traitement. Les natures tranchées à plus de 75 % donnent les premières lignes.
2. Mettre en tête la règle la plus forte et la plus fréquente.
3. Pour les natures partagées (40 à 60 %), chercher ce qui les départage : la phrase d'avant, la longueur, la place dans la séquence, un chiffre, une question. Tester chaque idée avec `croiser`. Si rien ne départage, c'est un **arbitrage** laissé au monteur : l'écrire comme tel.
4. Lire toutes les exceptions des règles fortes. Une exception qui se répète est une règle de plus. Une exception isolée se cite en exemple.
5. Ajouter ce qui touche au rythme et qui passe par-dessus le sens : « au bout de N secondes sans visage, on y revient » (voir `visage.absence_max_s`), « un bloc visage ne dépasse pas N secondes ».

## Le bloc de valeurs (section 12)

Les clés sont libres, sauf le bloc `controle`, lu par `scripts/controle-plan.mjs`. Les clés qu'il connaît :

```json
"controle": {
  "part_visage": [0.18, 0.32],
  "part_animation": [0.60, 0.78],
  "absence_visage_max_s": 60,
  "bloc_visage_median_s": [3, 6],
  "intervalle_entre_animations_s": [2, 3]
}
```

Une clé absente n'est pas contrôlée. Ne mettre dans le bloc que des valeurs que le gabarit utilise ou que le contrôle vérifie : tout le reste est de la prose et reste dans les sections.

Organisation conseillée : `rythme`, `camera`, `entrees`, puis un bloc par geste particulier au style (`compteur`, `surlignage`…), `visage`, `son`, `controle`. Durées en millisecondes (`_ms`), courbes en tableau de quatre nombres (`[0.6, 0, 0.4, 1]`), parts entre 0 et 1.

## L'habillage

`HABILLAGE-reference.md` décrit la peau de la référence sous forme d'**emplacements** : fond sombre, fond clair, texte, accent, police de titre, police technique, police d'emphase. Chaque emplacement a une valeur de référence et dit son rôle.

- Couleurs : celles de `couleurs.json`, vérifiées. Écrire le code et le nombre de pixels mesurés.
- Polices : ne pas chercher le nom exact de la police de l'auteur. Décrire son **rôle** et son **allure** (grotesque serrée, très grasse ; chasse fixe ; sérif en italique), puis proposer une police libre de même allure. C'est un *Choix*, à dire.
- Ce qui relève de la peau : couleurs, polices, grain, trames, arrondis, épaisseurs de trait. Ce qui relève de la grammaire et reste dans la fiche : tailles relatives, positions, nombre d'accents à la fois.

## La signature

`SIGNATURE.md` est le seul fichier qui ne vient pas de la vidéo. Il contient ce que l'utilisateur ajoute de lui-même : ses bruitages, son logo, sa formule d'ouverture ou de fin. Le lui demander. S'il n'a rien, laisser les rubriques avec « Aucune pour l'instant » : ne rien emprunter à la référence pour combler.

## Relecture finale

- [ ] Chaque chiffre de la fiche se retrouve dans `MESURES.md` ou un CSV.
- [ ] Chaque règle porte son niveau de preuve.
- [ ] La section 10 n'est pas vide.
- [ ] Le bloc JSON est valide et ne contient aucune valeur absente des sections.
- [ ] Aucun nom propre, aucune marque, aucun sujet de la vidéo d'origine dans les règles (seulement dans les exemples).
- [ ] Il ne reste aucun `{{emplacement}}`.
