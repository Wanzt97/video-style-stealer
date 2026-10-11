# Fiche {{nom-du-style}} — la grammaire de montage

Cette fiche fait foi. Le gabarit, le skill et les contrôles l'appliquent ; en cas de désaccord, c'est elle qui a raison.

Elle décrit une façon de monter, tirée d'une seule vidéo de référence. Elle ne contient ni image, ni son, ni texte de cette vidéo.

## Comment lire les preuves

| Niveau | Ce que ça veut dire |
|---|---|
| **Mesuré** | Calculé sur les images ou le son, avec le nombre de cas. |
| **Compté** | Tant de cas pour, tant contre. |
| **Lu** | Vu sur des planches d'images, sans décompte. |
| **Choix** | Rien dans la référence ne tranche : c'est une décision. |

## 1. Le style en trois phrases

{{trois phrases : qui porte quoi, ce qui rend le style reconnaissable, ce qu'il refuse}}

## 2. Les mots de la fiche

| Mot | Sens |
|---|---|
| {{mot}} | {{définition en une ligne}} |

## 3. Quand animer : la décision

Poser les questions dans l'ordre. S'arrêter au premier « oui ».

| N° | La phrase… | Alors | Preuve |
|---|---|---|---|
| 1 | {{condition}} | {{traitement}} | {{Compté : x sur y}} |

### Les arbitrages

{{les cas que le compte ne tranche pas, et comment décider}}

### Le rythme

| Règle | Valeur | Preuve |
|---|---|---|
| Part du visage | {{…}} | {{Mesuré}} |
| Part de l'animation | {{…}} | {{Mesuré}} |
| Durée d'un bloc visage | {{médiane, fourchette, maximum}} | {{Mesuré : n blocs}} |
| Plus longue absence du visage | {{…}} | {{Mesuré}} |
| Une animation toutes les | {{…}} | {{Mesuré : n animations}} |

### Début, milieu, fin

{{ce qui change entre les trois tiers de la vidéo, ou « rien de mesurable »}}

## 4. Comment animer : le mouvement

### Les règles

{{une règle par ligne, chacune avec sa preuve}}

### Les valeurs

| Geste | Durée | Courbe | Preuve |
|---|---|---|---|
| {{geste}} | {{ms}} | {{cubic-bezier(…) ou nom}} | {{Mesuré : n cas}} |

### La composition

{{où se posent les éléments, combien à la fois, combien d'accents}}

## 5. Le visage

{{cadrage, zoom lent ou non, texte posé dessus, coupes sautées}}

## 6. Le son de la référence

{{débit, pauses, fond sonore ; dire ce qui n'est pas mesuré}}

## 7. Les types de scène

La liste est fermée. Un passage qui n'entre dans aucun type se signale : on n'en invente pas en cours de montage.

| Type | Fonction | Dans la référence | Quand l'employer |
|---|---|---|---|
| {{type}} | {{à quoi il sert}} | {{n fois}} | {{décision n° …}} |

## 8. Ce que le style ne fait jamais

{{une ligne par refus, chacune vérifiée}}

## 9. Contrôler un montage fini

| Indicateur | Attendu | D'où vient la tolérance |
|---|---|---|
| {{indicateur}} | {{de … à …}} | {{Choix, d'après …}} |

## 10. Ce qui reste incertain

{{mesures peu fiables, règles sous 75 %, limites d'une seule vidéo}}

## 11. Désaccords tranchés

{{si deux mesures ou deux lectures se contredisent : laquelle est retenue, pourquoi ; sinon « Aucun »}}

## 12. Les valeurs pour le gabarit

Un seul bloc. `scripts/jetons.mjs` le recopie dans le gabarit ; `scripts/controle-plan.mjs` lit sa partie `controle`.
Les clés ci-dessous sont celles que le moteur de base du gabarit attend. En ajouter pour chaque geste propre au style.

```json
{
  "rythme": {
    "part_visage": "{{entre 0 et 1}}",
    "part_animation": "{{entre 0 et 1}}",
    "bloc_visage_median_s": "{{s}}",
    "intervalle_entre_animations_s": "{{s}}"
  },
  "entrees": {
    "fondu_ms": "{{ms}}",
    "fondu_courbe": "{{[x1, y1, x2, y2] ou \"lineaire\"}}",
    "cascade_ms": "{{ms}}",
    "calage_apres_le_mot_ms": "{{ms}}"
  },
  "compteur": { "ms": "{{ms, ou retirer ce bloc}}" },
  "visage": { "zoom_de": 1, "zoom_a": "{{1 si le visage ne zoome pas}}" },
  "controle": {
    "part_visage": "{{[bas, haut]}}",
    "part_animation": "{{[bas, haut]}}",
    "absence_visage_max_s": "{{s}}",
    "bloc_visage_median_s": "{{[bas, haut]}}",
    "intervalle_entre_animations_s": "{{[bas, haut]}}"
  }
}
```

## Sources

- Vidéo de référence : {{titre, auteur, lien}}
- Analyse du {{date}}, avec le skill `steal-style`.
- Preuves : dossier `analyse/` (gardé hors du paquet) — `mesures.json`, `plans.csv`, `mouvements.csv`, `phrases.csv`, `couleurs.json`, planches.
