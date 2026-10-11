#!/bin/bash
# Installe le skill steal-style pour un agent qui lit les skills dans un dossier.
#   bash install.sh codex      → ~/.codex/skills/steal-style
#   bash install.sh claude     → ~/.claude/skills/steal-style
#   bash install.sh <dossier>  → <dossier>/steal-style
# Dans Claude Code, préférer le plugin (voir README) : il se met à jour tout seul.
set -euo pipefail
ici="$(cd "$(dirname "$0")" && pwd)"
case "${1:-}" in
  codex)  cible="${CODEX_HOME:-$HOME/.codex}/skills" ;;
  claude) cible="$HOME/.claude/skills" ;;
  "")     echo "Usage : bash install.sh codex | claude | <dossier>" >&2; exit 2 ;;
  *)      cible="$1" ;;
esac
mkdir -p "$cible"
rm -rf "$cible/steal-style"
cp -R "$ici/skills/steal-style" "$cible/steal-style"
echo "Installé : $cible/steal-style"
if command -v uv >/dev/null; then
  # Prépare les bibliothèques et dit ce qui manque.
  uv run "$cible/steal-style/scripts/analyse.py" verifier || true
else
  echo "Il manque uv → https://docs.astral.sh/uv/ (macOS : brew install uv)"
  echo "Puis : uv run \"$cible/steal-style/scripts/analyse.py\" verifier"
fi
echo "Ouvrir une nouvelle session, puis : « vole le style de cette vidéo : <lien> »"
