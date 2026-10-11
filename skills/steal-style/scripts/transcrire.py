#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["faster-whisper>=1.0", "numpy>=1.26"]
# ///
"""Transcription mot à mot de la vidéo de référence (Whisper, sur cette machine).

    uv run transcrire.py <dossier-du-style> [--langue fr] [--modele small] [--noms "Nom propre, Marque"]

Écrit analyse/mots.json ([début, fin, mot, confiance]) et analyse/transcription.txt.
Les sous-titres automatiques des plateformes ne conviennent pas : leurs temps décalent d'une demi-seconde
et faussent le croisement entre la voix et l'image.
"""
import argparse, json, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("dossier")
ap.add_argument("--langue", default=None, help="code de langue (fr, en…). Sans indication : détection automatique.")
ap.add_argument("--modele", default="small", help="small (défaut), medium ou large-v3 : plus juste, plus lent")
ap.add_argument("--noms", default=None, help="noms propres et termes rares, séparés par des virgules")
a = ap.parse_args()

A = Path(a.dossier) / "analyse"
son = A / "voix16k.wav"
if not son.exists():
    sys.exit("Pas d'audio (analyse/voix16k.wav). Lancer d'abord analyse.py recuperer, ou la vidéo est muette.")

import wave
import numpy as np
from faster_whisper import WhisperModel

# L'audio est lu ici, en mono 16 kHz, pour ne pas dépendre du décodeur de la bibliothèque.
with wave.open(str(son), "rb") as w:
    ondes = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

modele = WhisperModel(a.modele, device="cpu", compute_type="int8")


def transcrire(amorce):
    segments, info = modele.transcribe(ondes, language=a.langue, word_timestamps=True, vad_filter=False,
                                       condition_on_previous_text=True, initial_prompt=amorce)
    mots, lignes = [], []
    for s in segments:
        lignes.append(f"[{int(s.start // 60):02d}:{s.start % 60:05.2f}] {s.text.strip()}")
        for w in s.words or []:
            mots.append([round(w.start, 3), round(w.end, 3), w.word.strip(), round(w.probability, 3)])
    return mots, lignes, info


fins = lambda mots: sum(m[2][-1:] in ".!?…" for m in mots)
# L'amorce donne les noms propres. Elle doit finir par un point : sans ponctuation dans l'amorce,
# Whisper rend un texte sans ponctuation, et on ne peut plus découper en phrases.
amorce = (a.noms.strip().rstrip(".") + ".") if a.noms else None
mots, lignes, info = transcrire(amorce)
if amorce and fins(mots) < len(mots) / 60:
    print("Transcription sans ponctuation : nouvel essai sans la liste de noms.", flush=True)
    essai = transcrire(None)
    if fins(essai[0]) > fins(mots):
        mots, lignes, info = essai

(A / "mots.json").write_text(json.dumps(mots, ensure_ascii=False), encoding="utf-8")
(A / "transcription.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
doutes = sum(m[3] < 0.5 for m in mots)
print(f"{len(mots)} mots, {fins(mots)} fins de phrase, langue {info.language} ; {doutes} mots peu sûrs (confiance < 0,5).")
print("Relire analyse/transcription.txt : corriger les noms propres dans mots.json sans toucher aux temps.")
