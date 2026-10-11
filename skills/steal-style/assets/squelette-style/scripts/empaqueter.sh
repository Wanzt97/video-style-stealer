#!/bin/bash
# Fabrique le zip du style, à installer comme skill.
# À relancer après toute modification de la fiche, du gabarit ou du skill.
#   bash scripts/empaqueter.sh
set -euo pipefail
style="$(cd "$(dirname "$0")/.." && pwd)"
nom="$(sed -n 's/^name: *"\{0,1\}\([a-z0-9-]*\)"\{0,1\} *$/\1/p' "$style/SKILL.md" | head -1)"
[ -n "$nom" ] || { echo "SKILL.md : en-tête « name: » introuvable." >&2; exit 1; }
sortie="$(dirname "$style")/$nom.zip"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

if [ -f "$style/gabarit/lib/jetons.js" ]; then node "$style/scripts/jetons.mjs" --verifier; fi

# Le dossier analyse/ contient la vidéo d'origine : il ne part jamais dans le paquet.
rsync -a "$style/" "$tmp/$nom/" \
  --exclude '.*' --exclude 'analyse' --exclude 'MESURES.md' --exclude 'renders' --exclude 'snapshots' \
  --exclude 'export-*.html' --exclude 'node_modules'
# Le studio HyperFrames marque les éléments qu'il a vus : on retire ces repères du paquet.
if [ -d "$tmp/$nom/gabarit" ]; then
  find "$tmp/$nom/gabarit" -name '*.html' -exec perl -pi -e 's/ data-hf-id="[^"]*"//g' {} +
fi

rm -f "$sortie"
(cd "$tmp" && zip -qr "$sortie" "$nom")
echo "Paquet prêt : $sortie ($(du -h "$sortie" | cut -f1 | tr -d ' '))"
