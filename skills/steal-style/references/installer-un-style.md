# Installer le style fabriqué

`empaqueter` produit `<nom>.zip` à côté du dossier du style. Il contient un dossier `<nom>/` avec son `SKILL.md`.

| Où | Comment |
|---|---|
| **Claude Code**, pour soi | Dézipper dans `~/.claude/skills/` : `unzip <nom>.zip -d ~/.claude/skills/` |
| **Claude Code**, pour un projet | Dézipper dans `.claude/skills/` du projet. |
| **claude.ai** (application et web) | Réglages → Capacités → Compétences → importer le zip. Il se synchronise ensuite vers Claude Code. |
| **Codex** | Dézipper dans `~/.codex/skills/` : `unzip <nom>.zip -d ~/.codex/skills/` |
| **Autre agent** qui lit les skills | Dézipper dans son dossier de skills. |

Une nouvelle session est nécessaire pour que le skill apparaisse.

Ensuite : « monte mes rushs dans le style `<nom>` ».

## Mettre à jour un style

Corriger `FICHE.md`, relancer `node scripts/jetons.mjs`, puis `bash scripts/empaqueter.sh` et réinstaller le zip. Le dossier du style est autonome : il se met à jour sans ce skill.

## Partager un style

Le zip ne contient aucune image de la vidéo de référence. Avant de le publier, vérifier tout de même : les polices ont une licence libre jointe, la démonstration n'utilise que du contenu neutre, `SIGNATURE.md` ne contient rien de privé.
