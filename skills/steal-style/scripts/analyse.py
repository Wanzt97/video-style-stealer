#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "numpy>=1.26",
#   "scipy>=1.11",
#   "opencv-python>=4.9,<5",
#   "scenedetect>=0.6.4",
#   "soundfile>=0.12",
#   "yt-dlp",
# ]
# ///
"""Mesures d'une vidéo de référence, pour en tirer un style de montage réutilisable.

    uv run analyse.py <commande> <dossier-du-style> [options]

Les commandes se lancent dans cet ordre. Tout ce qui est lourd va dans <dossier>/analyse/.

    verifier    dit ce qui est installé, ce qui manque et comment l'installer (sans dossier)
    demarrer    copie le squelette du style (fiche, habillage, skill, scripts)
    recuperer   télécharge ou copie la vidéo, fabrique la copie de travail et l'audio
    plans       découpe en plans, planches de vignettes à étiqueter
    signaux     une passe image par image : activité, mouvement d'ensemble, coupes sautées
    etiqueter   applique les étiquettes écrites à la main (plans, mouvements, phrases)
    mouvements  repère chaque animation, mesure durées, vols de caméra et courbes
    couleurs    fonds, couleurs d'accent, clair et sombre du texte
    phrases     croise chaque phrase prononcée avec ce qui est à l'écran
    croiser     tableau croisé de deux colonnes de phrases.csv
    mesures     rassemble tout dans mesures.json et MESURES.md
    planche     planche d'images à des instants choisis, pour vérifier à l'œil
    empaqueter  fabrique le zip du style, sans le dossier analyse/
"""
import argparse, csv, json, os, platform, re, shutil, socket, subprocess, sys, zipfile
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

FAMILLES = ("visage", "animation", "ecran", "b-roll", "autre")
ANIMEES = ("animation", "ecran")  # familles où l'on cherche des animations
SKILL = Path(__file__).resolve().parent.parent


# ───────────────────────────── outils communs ─────────────────────────────

def dossier_analyse(d):
    return Path(d) / "analyse"


def lire_meta(d):
    p = dossier_analyse(d) / "meta.json"
    if not p.exists():
        sys.exit(f"Pas de {p}. Lancer d'abord : analyse.py recuperer <source> {d}")
    return json.loads(p.read_text(encoding="utf-8"))


def lire_csv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ecrire_csv(p, lignes, champs):
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=champs, extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)


def lire_plans(d):
    p = dossier_analyse(d) / "plans.csv"
    if not p.exists():
        sys.exit("Pas de plans.csv : écrire analyse/etiquettes_plans.txt puis lancer « etiqueter ».")
    plans = lire_csv(p)
    for r in plans:
        r["a"], r["b"] = int(r["debut_image"]), int(r["fin_image"])
    return plans


def tc(s):
    return f"{int(s // 60):02d}:{s % 60:05.2f}"


def hexa(bgr):
    b, g, r = (int(round(float(v))) for v in bgr)
    return f"#{r:02X}{g:02X}{b:02X}"


def lancer(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], **kw)
    if r.returncode != 0:
        sys.exit(f"Échec de la commande : {' '.join(str(c) for c in cmd[:4])} …")
    return r


def exiger(*outils):
    manque = [o for o in outils if not shutil.which(o)]
    if manque:
        sys.exit(f"Outil manquant : {', '.join(manque)}. Installer ffmpeg (macOS : brew install ffmpeg).")


def taille_travail(meta):
    """Taille de calcul : 640 px sur le grand côté, quel que soit le format."""
    w, h = meta["proxy_largeur"], meta["proxy_hauteur"]
    f = 640 / max(w, h)
    return int(round(w * f / 2) * 2), int(round(h * f / 2) * 2)


def ouvrir(d):
    cap = cv2.VideoCapture(str(dossier_analyse(d) / "proxy.mp4"))
    if not cap.isOpened():
        sys.exit("Copie de travail illisible : relancer « recuperer ».")
    return cap


def image_a(cap, i):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
    ok, f = cap.read()
    return f if ok else None


def vignette(f, w, h, texte=None):
    v = np.zeros((h, w, 3), np.uint8) if f is None else cv2.resize(f, (w, h), interpolation=cv2.INTER_AREA)
    if texte:
        (tw, _), _ = cv2.getTextSize(texte, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(v, (0, 0), (tw + 8, 20), (0, 0, 0), -1)
        cv2.putText(v, texte, (4, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
    return v


def mosaique(vignettes, colonnes):
    vide = np.zeros_like(vignettes[0])
    vignettes = list(vignettes) + [vide] * (-len(vignettes) % colonnes)
    return np.vstack([np.hstack(vignettes[i:i + colonnes]) for i in range(0, len(vignettes), colonnes)])


def pct(v, qs):
    return [round(float(x), 3) for x in np.percentile(v, qs)] if len(v) else []


def med(v, n=2):
    return round(float(np.median(v)), n) if len(v) else None


# ───────────────────────────── courbes d'animation ─────────────────────────────

def bez(x1, y1, x2, y2, n=200):
    t = np.linspace(0, 1, n)
    x = 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t ** 2 * x2 + t ** 3
    y = 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t ** 2 * y2 + t ** 3
    return x, y


def classe_courbe(p):
    """p : progression de 0 à 1, une valeur par image. Rend le nom courant de la courbe."""
    n = len(p) - 1
    tau = np.arange(n + 1) / n
    v = np.diff(p) * n
    t50 = float(tau[np.argmin(np.abs(p - 0.5))])
    k = max(1, n // 10)
    v_debut, v_fin = float(v[:k].mean()), float(v[-k:].mean())
    if p.max() - 1 > 0.03:
        return "depassement"
    if v.max() < 1.35:
        return "lineaire"
    if t50 <= 0.36:
        return "ease-out"
    if t50 >= 0.64:
        return "ease-in"
    if v_debut < 0.6 and v_fin < 0.6:
        return "ease-in-out"
    return "ease-out" if t50 < 0.45 else "ease-in" if t50 > 0.55 else "ease-in-out"


# ───────────────────────────── verifier ─────────────────────────────

INSTALLER = {  # commande d'installation selon le système
    "ffmpeg": dict(Darwin="brew install ffmpeg", Linux="sudo apt install ffmpeg", Windows="winget install Gyan.FFmpeg"),
    "node": dict(Darwin="brew install node", Linux="voir https://nodejs.org (version 22 ou plus)", Windows="winget install OpenJS.NodeJS"),
}


def version_de(*cmd):
    """Première ligne de la sortie d'une commande, ou None si elle n'existe pas."""
    if not shutil.which(cmd[0]):
        return None
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr).strip().splitlines()[0]
    except Exception:
        return None


def cmd_verifier(a):
    systeme = platform.system()
    manque, lignes = [], []

    def noter(etat, texte, remede=""):
        lignes.append(f"  {etat:9s} {texte}" + (f"\n            → {remede}" if remede else ""))

    def titre(t):
        lignes.append(f"\n{t}")

    titre("Indispensable")
    v = version_de("uv", "--version")
    noter("OK", v) if v else noter("À SAVOIR", "uv introuvable dans ce terminal (le programme tourne quand même)",
                                   "https://docs.astral.sh/uv/ ; macOS : brew install uv")
    for outil in ("ffmpeg", "ffprobe"):
        v = version_de(outil, "-version")
        if v:
            noter("OK", " ".join(v.split()[:3]))
        else:
            manque.append(outil)
            noter("MANQUE", outil, INSTALLER["ffmpeg"].get(systeme, "installer ffmpeg"))
    libs = []
    for nom, module in (("OpenCV", "cv2"), ("NumPy", "numpy"), ("SciPy", "scipy"), ("PySceneDetect", "scenedetect"),
                        ("soundfile", "soundfile"), ("yt-dlp", "yt_dlp")):
        try:
            __import__(module)
            libs.append(nom)
        except Exception as e:
            manque.append(nom)
            noter("MANQUE", f"bibliothèque {nom} ({type(e).__name__})", "lancer ce programme avec « uv run », qui l'installe tout seul")
    if libs:
        noter("OK", "bibliothèques de mesure : " + ", ".join(libs))

    titre("Pour la transcription de la voix")
    cache = Path(os.environ.get("HF_HUB_CACHE") or os.environ.get("HUGGINGFACE_HUB_CACHE")
                 or Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub")
    if (cache / "models--Systran--faster-whisper-small").exists():
        noter("OK", "modèle de transcription déjà téléchargé")
    else:
        noter("À SAVOIR", "le modèle de transcription (500 Mo) se téléchargera au premier lancement de transcrire.py")
    try:
        socket.create_connection(("pypi.org", 443), timeout=4).close()
        noter("OK", "connexion internet")
    except OSError:
        noter("À SAVOIR", "pas de connexion internet : impossible de télécharger une vidéo, une bibliothèque ou le modèle")

    titre("Pour le gabarit HyperFrames (facultatif : sans lui, on s'arrête à la fiche)")
    v = version_de("node", "--version")
    majeure = int(re.sub(r"\D", " ", v).split()[0]) if v else 0
    if not v:
        noter("ABSENT", "Node.js", INSTALLER["node"].get(systeme, "https://nodejs.org"))
    elif majeure < 22:
        noter("ABSENT", f"Node.js {v} : HyperFrames demande la version 22 ou plus", INSTALLER["node"].get(systeme, "https://nodejs.org"))
    else:
        noter("OK", f"Node.js {v}")
        if shutil.which("npx"):
            noter("OK", "npx : HyperFrames se télécharge tout seul au premier « npx hyperframes »")
        else:
            noter("ABSENT", "npx (livré avec Node.js)", "réinstaller Node.js")
    noter("À SAVOIR", "les skills HyperFrames doivent aussi être disponibles pour l'agent : ce programme ne peut pas le voir")

    titre("Machine")
    libre = shutil.disk_usage(Path.cwd()).free / 1e9
    noter("OK" if libre >= 3 else "À SAVOIR", f"{libre:.0f} Go libres ici (compter 0,5 à 1 Go par vidéo de 15 minutes)")
    if systeme == "Windows":
        noter("À SAVOIR", "Windows : install.sh et scripts/empaqueter.sh demandent Git Bash ou WSL ; le reste marche tel quel")
    elif systeme != "Darwin":
        noter("À SAVOIR", f"{systeme} : l'outil a été mis au point sur macOS, signaler tout écart")

    print("Vérification de l'installation" + "\n".join(lignes) + "\n")
    if manque:
        sys.exit(f"Il manque : {', '.join(manque)}. Installer, puis relancer « verifier ».")
    print("Tout est prêt pour analyser une vidéo.")


# ───────────────────────────── demarrer ─────────────────────────────

def cmd_demarrer(a):
    cible = Path(a.dossier)
    cible.mkdir(parents=True, exist_ok=True)
    copies = 0
    for src in (SKILL / "assets" / "squelette-style").rglob("*"):
        if src.is_dir() or src.name.startswith("."):
            continue
        dst = cible / src.relative_to(SKILL / "assets" / "squelette-style")
        if dst.name == "SKILL.modele.md":  # rangé sous un autre nom pour ne pas être pris pour un skill
            dst = dst.with_name("SKILL.md")
        if dst.exists():
            continue  # ne jamais écraser un travail en cours
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copies += 1
    dossier_analyse(cible).mkdir(exist_ok=True)
    print(f"Squelette posé dans {cible} ({copies} fichiers copiés, rien d'écrasé).")


# ───────────────────────────── recuperer ─────────────────────────────

def sonde(fichier):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(fichier)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"Fichier illisible : {fichier}")
    return json.loads(r.stdout)


def cmd_recuperer(a):
    exiger("ffmpeg", "ffprobe")
    A = dossier_analyse(a.dossier)
    A.mkdir(parents=True, exist_ok=True)
    titre, auteur, origine = "", "", a.source
    if re.match(r"https?://", a.source):
        cmd = [sys.executable, "-m", "yt_dlp", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b",
               "--merge-output-format", "mp4", "--no-playlist", "--write-info-json", "-q", "--progress", "--no-warnings",
               "-o", str(A / "source.%(ext)s"), a.source]
        if a.de is not None or a.a is not None:
            cmd += ["--download-sections", f"*{a.de or 0}-{a.a if a.a is not None else 'inf'}"]
        lancer(cmd)
        source = A / "source.mp4"
        info = A / "source.info.json"
        if info.exists():
            fiche = json.loads(info.read_text(encoding="utf-8"))
            titre, auteur = fiche.get("title", ""), fiche.get("channel") or fiche.get("uploader") or ""
        coupe = []  # l'extrait est déjà coupé par le téléchargement
    else:
        source = Path(a.source).expanduser().resolve()
        if not source.exists():
            sys.exit(f"Fichier introuvable : {source}")
        titre = source.stem
        coupe = (["-ss", a.de] if a.de is not None else []) + (["-to", a.a] if a.a is not None else [])

    s = sonde(source)
    vid = next((x for x in s["streams"] if x["codec_type"] == "video"), None)
    if vid is None:
        sys.exit("Aucune piste vidéo dans la source.")
    audio = any(x["codec_type"] == "audio" for x in s["streams"])
    num, den = (float(x) for x in vid.get("avg_frame_rate", "25/1").split("/"))
    fps_source = num / den if den else 25.0
    # Au-delà de 30 i/s on garde une image sur deux : les durées restent justes à une image près.
    fps = fps_source / 2 if fps_source > 30.5 else fps_source
    fps = round(fps, 3)

    lancer(["ffmpeg", "-y", "-v", "error", *coupe, "-i", source,
            "-vf", f"fps={fps},scale=-2:'min(720,ih)'", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-g", "12", "-pix_fmt", "yuv420p", "-an", A / "proxy.mp4"])
    if audio:
        lancer(["ffmpeg", "-y", "-v", "error", *coupe, "-i", source, "-vn", "-ac", "2", "-ar", "44100", A / "audio.wav"])
        lancer(["ffmpeg", "-y", "-v", "error", *coupe, "-i", source, "-vn", "-ac", "1", "-ar", "16000", A / "voix16k.wav"])

    p = sonde(A / "proxy.mp4")
    pv = next(x for x in p["streams"] if x["codec_type"] == "video")
    cap = cv2.VideoCapture(str(A / "proxy.mp4"))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    meta = dict(source=origine, fichier_source=str(source), titre=titre, auteur=auteur, fps=fps, fps_source=round(fps_source, 3),
                n_images=n, duree_s=round(n / fps, 2), largeur=int(vid["width"]), hauteur=int(vid["height"]),
                proxy_largeur=int(pv["width"]), proxy_hauteur=int(pv["height"]), audio=audio,
                decalage_s=float(a.de) if (a.de is not None and coupe) else 0.0)
    (A / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"« {titre} » : {tc(meta['duree_s'])}, {fps} i/s, {meta['largeur']}×{meta['hauteur']}, audio {'oui' if audio else 'non'}")
    if meta["duree_s"] < 120:
        print("Attention : moins de 2 minutes. Les règles de rythme reposeront sur peu de cas.")


# ───────────────────────────── plans ─────────────────────────────

def fond_dominant(f):
    """Couleur la plus fréquente de l'image (cases de 16 niveaux par canal) et sa part."""
    s = cv2.resize(f, (160, 90), interpolation=cv2.INTER_AREA).reshape(-1, 3)
    cle = (s[:, 0] >> 4).astype(np.int32) << 8 | (s[:, 1] >> 4).astype(np.int32) << 4 | (s[:, 2] >> 4)
    val, nb = np.unique(cle, return_counts=True)
    k = val[np.argmax(nb)]
    return hexa(np.median(s[cle == k], 0)), float(nb.max() / len(cle))


def cmd_plans(a):
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector, AdaptiveDetector
    meta = lire_meta(a.dossier)
    A = dossier_analyse(a.dossier)
    fps, N = meta["fps"], meta["n_images"]
    mini = max(3, round(0.32 * fps))
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=27.0, min_scene_len=mini))
    sm.add_detector(AdaptiveDetector(adaptive_threshold=3.0, min_scene_len=mini, min_content_val=15))
    sm.auto_downscale = True
    sm.detect_scenes(open_video(str(A / "proxy.mp4")), show_progress=False)
    coupes = sorted({int(x.frame_num) for x, _ in sm.get_scene_list()} | {0})
    coupes = [c for i, c in enumerate(coupes) if i == 0 or c - coupes[i - 1] >= mini]  # deux détecteurs : pas de doublon
    bornes = list(zip(coupes, coupes[1:] + [N]))

    visages = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    W, H = taille_travail(meta)
    tw, th = (480, int(round(480 * H / W / 2) * 2)) if W >= H else (int(round(270 * W / H / 2) * 2), 270)
    cap = ouvrir(a.dossier)
    planches = A / "planches"
    planches.mkdir(exist_ok=True)
    for vieux in planches.glob("plans_*.jpg"):
        vieux.unlink()
    lignes, vigs = [], []
    for n, (i0, i1) in enumerate(bornes, 1):
        vus, tailles, milieu = 0, [], None
        for part in (0.2, 0.5, 0.8):
            f = image_a(cap, min(N - 1, i0 + int((i1 - i0) * part)))
            if f is None:
                continue
            if part == 0.5:
                milieu = f
            g = cv2.cvtColor(cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
            t = visages.detectMultiScale(g, scaleFactor=1.1, minNeighbors=6, minSize=(int(W * 0.09), int(W * 0.09)))
            if len(t):
                vus += 1
                tailles.append(max(w for _, _, w, _ in t) / W)
        fond, part_fond = fond_dominant(milieu) if milieu is not None else ("", 0)
        d0, d1 = i0 / fps, i1 / fps
        lignes.append(dict(plan=n, debut=tc(d0), fin=tc(d1), debut_s=f"{d0:.2f}", fin_s=f"{d1:.2f}", duree_s=f"{d1 - d0:.2f}",
                           debut_image=i0, fin_image=i1, source_coupe="detection",
                           visage_auto="oui" if vus >= 2 else "non", visage_largeur_pct=round(100 * np.median(tailles)) if tailles else "",
                           fond_hex=fond, fond_part_pct=round(100 * part_fond)))
        vigs.append(vignette(milieu, tw, th, f"#{n} {tc(d0)} {d1 - d0:.1f}s"))
    for k in range(0, len(vigs), 16):
        cv2.imwrite(str(planches / f"plans_{k // 16 + 1:02d}.jpg"), mosaique(vigs[k:k + 16], 4), [cv2.IMWRITE_JPEG_QUALITY, 85])
    ecrire_csv(A / "plans_brut.csv", lignes, list(lignes[0]))
    d = np.array([float(r["duree_s"]) for r in lignes])
    print(f"{len(lignes)} plans ; durée médiane {np.median(d):.2f} s ; visage détecté sur {sum(r['visage_auto'] == 'oui' for r in lignes)} plans")
    print(f"{(len(vigs) + 15) // 16} planches dans {planches}/plans_XX.jpg (image du milieu de chaque plan)")
    print("Suite : « signaux », puis regarder les planches et écrire analyse/etiquettes_plans.txt")


# ───────────────────────────── signaux ─────────────────────────────

def cmd_signaux(a):
    meta = lire_meta(a.dossier)
    A = dossier_analyse(a.dossier)
    N, fps = meta["n_images"], meta["fps"]
    W, H = taille_travail(meta)
    cap = ouvrir(a.dossier)
    f8, f20 = np.zeros(N, np.float32), np.zeros(N, np.float32)
    sc, dx, dy = np.ones(N, np.float32), np.zeros(N, np.float32), np.zeros(N, np.float32)
    inl, npt, res = np.zeros(N, np.float32), np.zeros(N, np.int32), np.zeros(N, np.float32)
    prev = None
    deja = (A / "signaux.npz").exists() and not a.refaire
    if deja:  # la passe est longue : on ne la refait que sur demande
        S = np.load(A / "signaux.npz")
        f8, f20, sc, dx, dy, inl, npt, res = (S[k] for k in ("f8", "f20", "sc", "dx", "dy", "inl", "npt", "res"))
    for i in range(0 if deja else N):
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        if prev is not None:
            d = cv2.absdiff(g, prev)
            f8[i], f20[i] = (d > 8).mean(), (d > 20).mean()
            res[i] = f20[i]
            p0 = cv2.goodFeaturesToTrack(prev, 400, 0.01, 6)
            if p0 is not None and len(p0) >= 8:
                p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, p0, None, winSize=(21, 21), maxLevel=3)
                u, v = p0[st[:, 0] == 1], p1[st[:, 0] == 1]
                npt[i] = len(u)
                if len(u) >= 8:
                    M, m = cv2.estimateAffinePartial2D(u, v, method=cv2.RANSAC, ransacReprojThreshold=1.0)
                    if M is not None:
                        sc[i] = np.hypot(M[0, 0], M[1, 0])
                        # déplacement du centre de l'image
                        dx[i] = M[0, 2] + (M[0, 0] - 1) * W / 2 - M[1, 0] * H / 2
                        dy[i] = M[1, 2] + M[1, 0] * W / 2 + (M[0, 0] - 1) * H / 2
                        inl[i] = m.mean()
                        w = cv2.warpAffine(prev, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
                        res[i] = (cv2.absdiff(g, w) > 20).mean()
        prev = g
        if i and i % max(1, N // 10) == 0:
            print(f"  {100 * i // N} %", flush=True)
    if not deja:
        np.savez(A / "signaux.npz", f8=f8, f20=f20, sc=sc, dx=dx, dy=dy, inl=inl, npt=npt, res=res)

    # Coupes sautées : dans un plan face caméra, une image qui change bien plus que ses voisines
    # et où les points suivis ne se retrouvent pas. Le cadre ne bouge presque pas : la détection de plans les laisse passer.
    brut = lire_csv(A / "plans_brut.csv")
    mini = max(3, round(0.32 * fps))
    v = max(2, round(12 * fps / 25))
    cand = []
    for r in brut:
        if r["visage_auto"] != "oui":
            continue
        i0, i1 = int(r["debut_image"]), int(r["fin_image"])
        for i in range(max(i0 + mini, v + 1), min(i1 - mini, N - v - 1)):
            autour = np.median(np.r_[f8[i - v:i - 1], f8[i + 2:i + v + 1]])
            if f8[i] >= max(0.02, 2.4 * autour) and f8[i] == f8[i - 2:i + 3].max() and inl[i] < 0.7:
                cand.append((i, int(r["plan"])))
    planches = A / "planches"
    for vieux in planches.glob("coupes_*.jpg"):
        vieux.unlink()
    tw, th = 213, int(round(213 * H / W / 2) * 2)
    for k in range(0, len(cand), 8):
        rangs = []
        for i, plan in cand[k:k + 8]:
            rangs.append(np.hstack([vignette(image_a(cap, i + d), tw, th, f"{i} p{plan} {tc(i / fps)}" if d == -3 else f"{d:+d}")
                                    for d in (-3, -2, -1, 0, 1, 2)]))
        cv2.imwrite(str(planches / f"coupes_{k // 8 + 1:02d}.jpg"), np.vstack(rangs), [cv2.IMWRITE_JPEG_QUALITY, 80])
    ecrire_csv(A / "coupes_candidates.csv", [dict(image=i, plan=p, instant=tc(i / fps)) for i, p in cand], ["image", "plan", "instant"])
    print(f"Signaux écrits. {len(cand)} coupes sautées possibles dans les plans avec visage : planches coupes_XX.jpg "
          "(la coupe est entre −1 et 0). Écrire les numéros d'image confirmés dans analyse/coupes_confirmees.txt.")


# ───────────────────────────── etiqueter ─────────────────────────────

def lire_etiquettes(p, n_champs):
    """Lignes « id|champ|champ… ». L'id peut être une plage (12-15). Lignes vides et # ignorées."""
    sortie = {}
    if not p.exists():
        return sortie
    for no, ligne in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        parts = [x.strip() for x in ligne.split("|")]
        parts += [""] * (n_champs + 1 - len(parts))
        m = re.fullmatch(r"([A-Za-z]*)(\d+)(?:-[A-Za-z]*(\d+))?", parts[0])
        if not m:
            sys.exit(f"{p.name}, ligne {no} : identifiant illisible « {parts[0]} »")
        prefixe, deb, fin = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
        largeur = len(m.group(2))
        for k in range(deb, fin + 1):
            sortie[f"{prefixe}{k:0{largeur}d}" if prefixe else str(k)] = parts[1:n_champs + 1]
    return sortie


ETIQUETTES = dict(mouvements=("etiquettes_mouvements.txt", ("type", "description")), phrases=("etiquettes_phrases.txt", ("nature",)))


def reporter_etiquettes(A, nom):
    """Recopie dans mouvements.csv ou phrases.csv les étiquettes écrites à la main. Appelé aussi après chaque recalcul."""
    fichier, champs_et = ETIQUETTES[nom]
    et = lire_etiquettes(A / fichier, len(champs_et))
    p = A / f"{nom}.csv"
    if not et or not p.exists():
        return ""
    lignes = lire_csv(p)
    for r in lignes:
        if r["id"] in et:
            r.update(dict(zip(champs_et, et[r["id"]])))
    ecrire_csv(p, lignes, list(lignes[0]))
    return f"{nom}.csv : {sum(r['id'] in et for r in lignes)} lignes étiquetées sur {len(lignes)}"


def cmd_etiqueter(a):
    meta = lire_meta(a.dossier)
    A = dossier_analyse(a.dossier)
    fps = meta["fps"]
    fait = []

    # 1. Les plans : famille, sous-type, description, texte à l'écran.
    et = lire_etiquettes(A / "etiquettes_plans.txt", 4)
    if et:
        brut = lire_csv(A / "plans_brut.csv")
        manque = [r["plan"] for r in brut if r["plan"] not in et]
        if manque:
            sys.exit(f"etiquettes_plans.txt : {len(manque)} plans sans étiquette ({', '.join(manque[:12])}…)")
        faux = sorted({v[0] for v in et.values() if v[0] not in FAMILLES})
        if faux:
            sys.exit(f"Famille inconnue : {', '.join(faux)}. Familles permises : {', '.join(FAMILLES)}")
        sauts = []
        p = A / "coupes_confirmees.txt"
        if p.exists():
            sauts = sorted({int(x) for x in re.findall(r"\d+", re.sub(r"#.*", "", p.read_text()))})
        plans = []
        for r in brut:
            i0, i1 = int(r["debut_image"]), int(r["fin_image"])
            bornes = [i0] + [s for s in sauts if i0 < s < i1] + [i1]
            for k in range(len(bornes) - 1):
                u, v = bornes[k], bornes[k + 1]
                fam, sous, desc, texte = et[r["plan"]]
                plans.append({**r, "plan": len(plans) + 1, "plan_origine": r["plan"], "debut": tc(u / fps), "fin": tc(v / fps),
                              "debut_s": f"{u / fps:.2f}", "fin_s": f"{v / fps:.2f}", "duree_s": f"{(v - u) / fps:.2f}",
                              "debut_image": u, "fin_image": v, "source_coupe": "detection" if k == 0 else "saut",
                              "famille": fam, "sous_type": sous, "description": desc, "texte_ecran": texte})
        champs = ["plan", "plan_origine", "debut", "fin", "debut_s", "fin_s", "duree_s", "debut_image", "fin_image",
                  "source_coupe", "famille", "sous_type", "description", "texte_ecran", "visage_auto", "fond_hex"]
        ecrire_csv(A / "plans.csv", plans, champs)
        c = Counter(r["famille"] for r in plans)
        fait.append(f"plans.csv : {len(plans)} plans ({', '.join(f'{k} {v}' for k, v in c.most_common())}), {len(sauts)} coupes sautées ajoutées")
        desaccord = [r["plan_origine"] for r in plans if (r["famille"] == "visage") != (r["visage_auto"] == "oui") and r["source_coupe"] == "detection"]
        if desaccord:
            fait.append(f"  à revérifier à l'œil, la détection de visage dit le contraire : plans {', '.join(desaccord[:20])}")

    # 2. Les mouvements (type, description) et les phrases (nature).
    fait += [x for x in (reporter_etiquettes(A, "mouvements"), reporter_etiquettes(A, "phrases")) if x]
    print("\n".join(fait) if fait else "Aucun fichier d'étiquettes trouvé dans analyse/.")


# ───────────────────────────── mouvements ─────────────────────────────

def ajuster_vol(q, a0, b0):
    """Ajuste « deux images clés + courbe de Bézier (x1,0,x2,1) » sur une trajectoire q.
    Rend début, durée (en images), x1, x2, erreur relative."""
    from scipy.optimize import least_squares
    t = np.arange(len(q), dtype=float)
    A0 = q[-1] - q[0]
    if abs(A0) < 1e-6:
        return None

    def E(u, x1, x2):
        x, y = bez(x1, 0, x2, 1, 120)
        return np.interp(np.clip(u, 0, 1), x, y)

    def modele(v):
        t0, D, x1, x2, c0, A = v
        return c0 + A * E((t - t0) / max(D, 1), x1, x2)

    mieux = None
    for x1, x2 in ((0.33, 0.67), (0.6, 0.4), (0.8, 0.2), (0.2, 0.2), (0.8, 0.8)):
        try:
            o = least_squares(lambda v: modele(v) - q, [a0 - 2, b0 - a0 + 4, x1, x2, q[0], A0],
                              bounds=([-5, 4, 0, 0, -np.inf, -np.inf], [len(q), len(q) + 10, 1, 1, np.inf, np.inf]))
        except Exception:
            continue
        if mieux is None or o.cost < mieux.cost:
            mieux = o
    if mieux is None:
        return None
    t0, D, x1, x2, _, A = mieux.x
    rms = float(np.sqrt(np.mean(mieux.fun ** 2)) / abs(A)) if abs(A) > 1e-9 else 1.0
    return dict(t0=float(t0), D=float(D), x1=float(x1), x2=float(x2), rms=rms,
                tronque=bool(t0 < 0.5 or t0 + D > len(q) - 1.5))


def cmd_mouvements(a):
    from scipy.signal import find_peaks
    from scipy.ndimage import gaussian_filter1d
    meta = lire_meta(a.dossier)
    A = dossier_analyse(a.dossier)
    fps, N = meta["fps"], meta["n_images"]
    W, H = taille_travail(meta)
    plans = lire_plans(a.dossier)
    S = np.load(A / "signaux.npz")
    f8, f20, sc, dx, dy, inl, res = (S[k] for k in ("f8", "f20", "sc", "dx", "dy", "inl", "res"))
    k25 = fps / 25  # les seuils en images ont été réglés à 25 i/s

    # 1. Chaque bosse du signal d'activité, à l'intérieur d'un plan animé, est une animation candidate.
    ev = []
    for p in plans:
        if p["famille"] not in ANIMEES or p["b"] - p["a"] < round(6 * k25):
            continue
        s = f20[p["a"] + 1:p["b"]].astype(float)  # l'image de coupe est exclue
        x = np.log10(np.maximum(gaussian_filter1d(s, k25), 1e-4))
        pk, _ = find_peaks(x, height=np.log10(0.004), prominence=0.45, distance=max(1, round(4 * k25)))
        if not len(pk):
            continue
        bornes = [0] + [pk[k] + int(np.argmin(x[pk[k]:pk[k + 1]])) for k in range(len(pk) - 1)] + [len(x) - 1]
        for k, c in enumerate(pk):
            lo, hi = bornes[k], bornes[k + 1]
            seuil = max(np.log10(0.0015), x[c] - 1.3)  # coupe les queues sous 5 % du pic
            s0 = c
            while s0 > lo and x[s0 - 1] > seuil:
                s0 -= 1
            e0 = c
            while e0 < hi and x[e0 + 1] > seuil:
                e0 += 1
            ev.append(dict(plan=int(p["plan"]), famille=p["famille"], pa=p["a"], pb=p["b"],
                           f0=p["a"] + 1 + s0, f1=p["a"] + 1 + e0, pic=float(s[c])))

    # 2. Mouvement d'ensemble : caméra virtuelle (zoom, glissement) ou élément isolé ?
    for k, e in enumerate(ev):
        sl = slice(e["f0"], e["f1"] + 1)
        Sc = np.cumprod(sc[sl].astype(float))
        P = np.cumsum(np.c_[dx[sl], dy[sl]] / Sc[:, None], axis=0)
        zoom, pan = float(np.log(Sc[-1])), float(np.hypot(*P[-1]) / W)
        ens = float(1 - res[sl].sum() / max(f20[sl].sum(), 1e-6))
        e.update(zoom_pct=round((Sc[-1] - 1) * 100, 1), pan_x_pct=round(P[-1, 0] / W * 100, 1), pan_y_pct=round(P[-1, 1] / H * 100, 1),
                 inl=round(float(inl[sl].mean()), 2), part_ensemble=round(ens, 2))
        camera = e["inl"] >= 0.6 and ens >= 0.4 and (abs(zoom) >= 0.18 or pan >= 0.08)
        e["genre"] = ("camera-zoom" if abs(zoom) >= 0.18 and abs(zoom) >= pan * 0.8 else "camera-glissement") if camera else "element"
        if camera:
            marge = round(10 * k25)
            lo = max(e["f0"] - marge, e["pa"] + 1, ev[k - 1]["f1"] + 1 if k and ev[k - 1]["plan"] == e["plan"] else 0)
            hi = min(e["f1"] + marge, e["pb"] - 1, ev[k + 1]["f0"] - 1 if k + 1 < len(ev) and ev[k + 1]["plan"] == e["plan"] else N)
            lo, hi = min(lo, e["f0"]), max(hi, e["f1"])
            s2 = slice(lo, hi + 1)
            Sc2 = np.cumprod(sc[s2].astype(float))
            P2 = np.cumsum(np.c_[dx[s2], dy[s2]] / Sc2[:, None], axis=0)
            if e["genre"] == "camera-zoom":
                q = np.log(Sc2)
            else:
                u = P2[e["f1"] - lo] - P2[max(e["f0"] - lo - 1, 0)]
                q = P2 @ (u / (np.hypot(*u) + 1e-9))
            r = ajuster_vol(np.r_[0, q], e["f0"] - lo, e["f1"] - lo + 1)
            if r:
                e.update(cles_ms=int(round(r["D"] * 1000 / fps)), x1=round(r["x1"], 2), x2=round(r["x2"], 2),
                         fiable=bool(r["rms"] < 0.015 and not r["tronque"]))

    # 3. Une lecture des images : entrée des éléments (5 % → 95 %) et planches de relecture.
    cap = ouvrir(a.dossier)
    planches = A / "planches"
    for vieux in planches.glob("mouvements_*.jpg"):
        vieux.unlink()
    tw, th = 196, int(round(196 * H / W / 2) * 2)
    rangs = []
    for k, e in enumerate(ev):
        e["id"] = f"M{k + 1:03d}"
        u, v = max(e["f0"] - 3, e["pa"]), min(e["f1"] + 5, e["pb"] - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, u)
        gris, petites = {}, {}
        voulues = set(np.linspace(max(e["f0"] - 2, u), min(e["f1"] + 2, v), 8).round().astype(int))
        for i in range(u, v + 1):
            ok, f = cap.read()
            if not ok:
                break
            gris[i] = cv2.cvtColor(cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
            if i in voulues:
                petites[i] = f
        bande = [vignette(petites.get(i), tw, th, f"{e['id']} {tc(e['f0'] / fps)} {e['genre']}" if j == 0 else f"{i - e['f0']:+d}")
                 for j, i in enumerate(sorted(voulues))]
        rangs.append(np.hstack(bande + [vignette(None, tw, th)] * (8 - len(bande))))
        if e["genre"] == "element":
            avant = gris.get(max(e["f0"] - 2, u))
            apres = [gris[i] for i in range(e["f1"] + 2, v + 1) if i in gris]
            if avant is not None and apres:
                apres = np.median(apres, 0)
                d = apres - avant
                m = cv2.morphologyEx((np.abs(d) > 25).astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool) & (np.abs(d) > 25)
                if m.sum() >= 60:
                    ref = np.abs(d)[m].mean()
                    idx = [i for i in range(max(e["f0"] - 2, u), e["f1"] + 3) if i in gris]
                    prog = np.clip(np.array([1 - np.abs(gris[i] - apres)[m].mean() / ref for i in idx]), 0, 1.2)
                    i5 = int(np.argmax(prog >= 0.05))
                    i95 = int(np.argmax(prog >= 0.95)) if (prog >= 0.95).any() else len(prog) - 1
                    n = max(i95 - i5, 0) + 1
                    ys, xs = np.nonzero(m)
                    x0, x1, y0, y1 = np.percentile(xs, 1), np.percentile(xs, 99), np.percentile(ys, 1), np.percentile(ys, 99)
                    # Fondu local : pour chaque point qui change, le temps qu'il met à passer de 10 % à 90 %.
                    pile = (np.stack([gris[i][m] for i in idx]) - avant[m]) / d[m]
                    t10, t90 = np.argmax(pile >= 0.1, 0), np.argmax(pile >= 0.9, 0)
                    arrive = (pile >= 0.9).any(0) & (t90 >= t10)
                    if arrive.sum() >= 30:
                        e["fondu_ms"] = int(round(float(np.median((t90 - t10)[arrive])) / 0.8 * 1000 / fps))
                    e.update(entree_images=n, entree_ms=int(round(n * 1000 / fps)),
                             centre_xy_pct=f"{(x0 + x1) / 2 / W * 100:.0f} / {(y0 + y1) / 2 / H * 100:.0f}",
                             taille_lh_pct=f"{(x1 - x0) / W * 100:.0f} / {(y1 - y0) / H * 100:.0f}")
                    if n >= 6:
                        seg = prog[i5:i95 + 1]
                        seg = (seg - seg[0]) / max(seg[-1] - seg[0], 1e-6)
                        e["courbe"] = classe_courbe(seg)
    for k in range(0, len(rangs), 8):
        cv2.imwrite(str(planches / f"mouvements_{k // 8 + 1:02d}.jpg"), np.vstack(rangs[k:k + 8]), [cv2.IMWRITE_JPEG_QUALITY, 80])

    lignes = []
    for e in ev:
        lignes.append(dict(id=e["id"], plan=e["plan"], famille=e["famille"], debut=tc(e["f0"] / fps), debut_s=f"{e['f0'] / fps:.2f}",
                           fin_s=f"{(e['f1'] + 1) / fps:.2f}", duree_ms=int(round((e["f1"] - e["f0"] + 1) * 1000 / fps)),
                           genre_auto=e["genre"], zoom_pct=e["zoom_pct"], pan_x_pct=e["pan_x_pct"], pan_y_pct=e["pan_y_pct"],
                           part_ensemble=e["part_ensemble"], cles_ms=e.get("cles_ms", ""),
                           bezier=f"{e['x1']}, 0, {e['x2']}, 1" if "x1" in e else "", fiable=e.get("fiable", ""),
                           entree_ms=e.get("entree_ms", ""), fondu_ms=e.get("fondu_ms", ""), courbe=e.get("courbe", ""),
                           centre_xy_pct=e.get("centre_xy_pct", ""), taille_lh_pct=e.get("taille_lh_pct", ""), type="", description=""))
    champs = ["id", "plan", "famille", "debut", "debut_s", "fin_s", "duree_ms", "genre_auto", "zoom_pct", "pan_x_pct", "pan_y_pct",
              "part_ensemble", "cles_ms", "bezier", "fiable", "entree_ms", "fondu_ms", "courbe", "centre_xy_pct", "taille_lh_pct", "type", "description"]
    ecrire_csv(A / "mouvements.csv", lignes, champs)
    reporter_etiquettes(A, "mouvements")  # un recalcul ne perd pas les étiquettes déjà écrites
    cam = [e for e in ev if e["genre"] != "element"]
    ok = [e for e in cam if e.get("fiable")]
    print(f"{len(ev)} mouvements : {len(cam)} de caméra ({len(ok)} mesurés de façon fiable), {len(ev) - len(cam)} d'éléments")
    if ok:
        print(f"  vol de caméra : médiane {int(np.median([e['cles_ms'] for e in ok]))} ms, "
              f"courbe médiane ({np.median([e['x1'] for e in ok]):.2f}, 0, {np.median([e['x2'] for e in ok]):.2f}, 1)")
    print(f"{(len(rangs) + 7) // 8} planches dans {planches}/mouvements_XX.jpg. Écrire analyse/etiquettes_mouvements.txt (id|type|description).")


# ───────────────────────────── couleurs ─────────────────────────────

def cmd_couleurs(a):
    meta = lire_meta(a.dossier)
    A = dossier_analyse(a.dossier)
    plans = lire_plans(a.dossier)
    src = Path(meta["fichier_source"])
    cap = cv2.VideoCapture(str(src)) if src.exists() else ouvrir(a.dossier)  # pleine définition si possible
    decalage = meta.get("decalage_s", 0.0) if src.exists() else 0.0
    sortie = {}
    for fam in FAMILLES:
        lot = [p for p in plans if p["famille"] == fam]
        if not lot:
            continue
        lot = lot[::max(1, len(lot) // 150)]
        fonds, accents, clairs, sombres = Counter(), [], [], []
        vrais, n_lus = {}, 0
        for p in lot:
            cap.set(cv2.CAP_PROP_POS_MSEC, (decalage + (float(p["debut_s"]) + float(p["fin_s"])) / 2) * 1000)
            ok, f = cap.read()
            if not ok:
                continue
            n_lus += 1
            px = f[::3, ::3].reshape(-1, 3)
            cle = (px[:, 0] >> 3).astype(np.int32) << 10 | (px[:, 1] >> 3).astype(np.int32) << 5 | (px[:, 2] >> 3)
            val, nb = np.unique(cle, return_counts=True)
            if nb.max() / len(cle) >= 0.25:
                k = int(val[np.argmax(nb)])
                fonds[k] += 1
                vrais.setdefault(k, []).append(np.median(px[cle == k], 0))
            hsv = cv2.cvtColor(px.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)
            vif = (hsv[:, 1] >= 140) & (hsv[:, 2] >= 150)
            if vif.sum() >= 0.0005 * len(px):
                accents.append((px[vif], hsv[vif, 0], len(px)))
            c = (hsv[:, 2] >= 200) & (hsv[:, 1] <= 40)
            s = hsv[:, 2] <= 60
            if c.sum() > 50:
                clairs.append(px[c][::7])
            if s.sum() > 50:
                sombres.append(px[s][::7])
        bloc = dict(images_lues=n_lus,
                    fonds=[dict(hex=hexa(np.median(vrais[k], 0)), part_des_plans=round(n / n_lus, 2)) for k, n in fonds.most_common(3)])
        if accents:
            tous = np.vstack([x for x, _, _ in accents])
            teintes = np.concatenate([h for _, h, _ in accents])
            bacs = (teintes // 15).astype(int)
            liste = []
            for bac, nb in Counter(bacs).most_common(3):
                sel = tous[bacs == bac]
                cle = (sel[:, 0] >> 3).astype(np.int32) << 10 | (sel[:, 1] >> 3).astype(np.int32) << 5 | (sel[:, 2] >> 3)
                val, cnt = np.unique(cle, return_counts=True)
                mode = sel[cle == val[np.argmax(cnt)]]
                presents = sum(((h // 15) == bac).sum() >= 0.0005 * n for _, h, n in accents)
                liste.append(dict(hex=hexa(np.median(mode, 0)), pixels=int(nb), part_des_pixels_vifs=round(nb / len(bacs), 2),
                                  part_des_plans=round(presents / n_lus, 2)))
            bloc["accents"] = liste

        def mode_de(paquets):
            tous = np.vstack(paquets)
            cle = (tous[:, 0] >> 3).astype(np.int32) << 10 | (tous[:, 1] >> 3).astype(np.int32) << 5 | (tous[:, 2] >> 3)
            val, cnt = np.unique(cle, return_counts=True)
            return hexa(np.median(tous[cle == val[np.argmax(cnt)]], 0))
        if clairs:
            bloc["clair_le_plus_frequent"] = mode_de(clairs)
        if sombres:
            bloc["sombre_le_plus_frequent"] = mode_de(sombres)
        sortie[fam] = bloc
    (A / "couleurs.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1), encoding="utf-8")

    # Nuancier à regarder : une ligne par famille.
    rangs = []
    for fam, bloc in sortie.items():
        cases = [("fond", x["hex"]) for x in bloc["fonds"]] + [("accent", x["hex"]) for x in bloc.get("accents", [])]
        cases += [(nom, bloc[cle]) for nom, cle in (("clair", "clair_le_plus_frequent"), ("sombre", "sombre_le_plus_frequent")) if cle in bloc]
        rang = np.full((90, 150 * 9, 3), 40, np.uint8)
        cv2.putText(rang, fam, (8, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        for j, (nom, h) in enumerate(cases[:8], 1):
            bgr = (int(h[5:7], 16), int(h[3:5], 16), int(h[1:3], 16))
            rang[4:86, j * 150 + 4:(j + 1) * 150 - 4] = bgr
            ton = (0, 0, 0) if sum(bgr) > 380 else (255, 255, 255)
            cv2.putText(rang, nom, (j * 150 + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, ton, 1, cv2.LINE_AA)
            cv2.putText(rang, h, (j * 150 + 10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, ton, 1, cv2.LINE_AA)
        rangs.append(rang)
    (A / "planches").mkdir(exist_ok=True)
    cv2.imwrite(str(A / "planches" / "couleurs.jpg"), np.vstack(rangs))
    for fam, bloc in sortie.items():
        print(f"{fam:10s} fonds {[x['hex'] for x in bloc['fonds']]}  accents {[x['hex'] for x in bloc.get('accents', [])]}")
    print(f"Nuancier : {A}/planches/couleurs.jpg. Vérifier chaque couleur sur une vraie image avant de l'écrire dans la fiche.")


# ───────────────────────────── phrases ─────────────────────────────

def lire_mots(d):
    p = dossier_analyse(d) / "mots.json"
    if not p.exists():
        sys.exit("Pas de mots.json : lancer d'abord transcrire.py.")
    return json.loads(p.read_text(encoding="utf-8"))


def pauses_de_la_voix(d):
    """Silences de la voix d'au moins 0,2 s, lus sur le son : bande 150–4000 Hz, 15 dB sous le niveau fort.
    Les temps de mots de Whisper ne conviennent pas : ils se touchent presque toujours."""
    import soundfile as sf
    import scipy.signal as sg
    p = dossier_analyse(d) / "voix16k.wav"
    if not p.exists():
        return []
    x, sr = sf.read(p)
    x = sg.sosfilt(sg.butter(4, [150, 4000], btype="band", fs=sr, output="sos"), x if x.ndim == 1 else x.mean(1))
    hop = sr // 100
    db = 20 * np.log10(np.maximum(np.sqrt((x[:len(x) // hop * hop].reshape(-1, hop) ** 2).mean(1)), 1e-9))
    bas = np.r_[db < np.percentile(db, 90) - 15, False]
    sortie, debut = [], None
    for i, v in enumerate(bas):
        if v and debut is None:
            debut = i
        elif not v and debut is not None:
            if i - debut >= 20:
                sortie.append((debut / 100, i / 100))
            debut = None
    return sortie


def famille_sur(plans, t0, t1):
    """Temps passé dans chaque famille entre t0 et t1."""
    c = Counter()
    for p in plans:
        r = min(t1, float(p["fin_s"])) - max(t0, float(p["debut_s"]))
        if r > 0:
            c[p["famille"]] += r
    return c


def cmd_phrases(a):
    A = dossier_analyse(a.dossier)
    plans = lire_plans(a.dossier)
    mots = lire_mots(a.dossier)
    mouv = [float(r["debut_s"]) for r in lire_csv(A / "mouvements.csv")] if (A / "mouvements.csv").exists() else []
    # Une phrase finit à la ponctuation forte. Si la transcription n'en a presque pas,
    # on coupe aux silences de la voix : moins juste, et on le dit.
    ponctuee = sum(bool(re.search(r"[.!?…]$", m[2])) for m in mots) >= len(mots) / 60
    silences = np.array([(s + f) / 2 for s, f in pauses_de_la_voix(a.dossier) if ponctuee is False or f - s >= 0.7])
    if not ponctuee:
        print("Attention : transcription presque sans ponctuation. Phrases coupées aux silences de la voix (0,2 s et plus).")
    phrases, cur = [], []
    for k, (d, f, w, *_) in enumerate(mots):
        cur.append((d, f, w))
        suivant = mots[k + 1][0] if k + 1 < len(mots) else None
        silence = suivant is not None and len(silences) and bool(np.any((silences > (d + f) / 2) & (silences < suivant + 0.05)))
        if (ponctuee and re.search(r"[.!?…]$", w)) or suivant is None or silence:
            phrases.append(cur)
            cur = []
    lignes = []
    for n, ph in enumerate(phrases, 1):
        t0, t1 = ph[0][0], ph[-1][1]
        texte = " ".join(w for _, _, w in ph)
        # Le traitement d'une phrase se lit sur ses 1,2 premières secondes, à la majorité.
        debut = famille_sur(plans, t0, min(t1, t0 + 1.2) if t1 - t0 > 0.4 else t0 + 0.4)
        tout = famille_sur(plans, t0, max(t1, t0 + 0.04))
        total = sum(tout.values()) or 1
        lignes.append(dict(id=f"P{n:03d}", debut=tc(t0), debut_s=f"{t0:.2f}", fin_s=f"{t1:.2f}", nb_mots=len(ph),
                           a_l_ecran=debut.most_common(1)[0][0] if debut else "",
                           part_visage=round(tout["visage"] / total, 2), part_animee=round(sum(tout[k] for k in ANIMEES) / total, 2),
                           nb_mouvements=sum(t0 - 0.2 <= m < t1 for m in mouv),
                           chiffre="oui" if re.search(r"\d", texte) else "non", question="oui" if texte.rstrip().endswith("?") else "non",
                           premier_mot=re.sub(r"[^\w'’-]", "", ph[0][2]).lower(), nature="", texte=texte))
    ecrire_csv(A / "phrases.csv", lignes, list(lignes[0]))
    reporter_etiquettes(A, "phrases")

    # Le visage revient-il en début de phrase ?
    debuts = np.array([float(r["debut_s"]) for r in lignes])
    retours = [float(p["debut_s"]) for k, p in enumerate(plans) if p["famille"] == "visage" and k and plans[k - 1]["famille"] != "visage"]
    cales = sum(np.abs(debuts - t).min() <= 0.4 for t in retours)
    stats = dict(n=len(lignes), par_traitement=dict(Counter(r["a_l_ecran"] for r in lignes)),
                 retours_visage=len(retours), retours_visage_en_debut_de_phrase=int(cales),
                 phrases_animees_sans_mouvement=sum(r["a_l_ecran"] in ANIMEES and r["nb_mouvements"] == 0 for r in lignes),
                 phrases_animees=sum(r["a_l_ecran"] in ANIMEES for r in lignes))
    (A / "phrases_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(lignes)} phrases : {stats['par_traitement']}")
    print(f"Le visage revient {len(retours)} fois, dont {cales} au début d'une phrase (à 0,4 s près).")
    print("Suite : lire phrases.csv, écrire analyse/etiquettes_phrases.txt (id|nature), « etiqueter », puis « croiser ».")


def cmd_croiser(a):
    lignes = lire_csv(dossier_analyse(a.dossier) / "phrases.csv")
    for col in (a.ligne, a.colonne):
        if col not in lignes[0]:
            sys.exit(f"Colonne inconnue : {col}. Colonnes : {', '.join(lignes[0])}")
    vides = sum(not r[a.ligne] for r in lignes)
    lignes = [r for r in lignes if r[a.ligne]]
    cols = [c for c, _ in Counter(r[a.colonne] for r in lignes).most_common()]
    print(f"{a.ligne} × {a.colonne} ({len(lignes)} phrases{f', {vides} sans étiquette ignorées' if vides else ''})\n")
    print(f"{'':28s}" + "".join(f"{c[:12]:>14s}" for c in cols) + f"{'total':>8s}")
    for val, n in Counter(r[a.ligne] for r in lignes).most_common():
        cpt = Counter(r[a.colonne] for r in lignes if r[a.ligne] == val)
        print(f"{val[:27]:28s}" + "".join(f"{f'{cpt[c]} ({100 * cpt[c] // n} %)':>14s}" for c in cols) + f"{n:>8d}")
    print("\nUne règle ne vaut que par son compte : l'écrire « x cas sur y » dans la fiche, exceptions comprises.")


# ───────────────────────────── mesures ─────────────────────────────

def suites(plans, test):
    """Regroupe les plans consécutifs qui passent le test. Rend [(debut_s, fin_s, nb_plans)]."""
    s, cur = [], None
    for p in plans:
        if test(p):
            cur = [float(p["debut_s"]), float(p["fin_s"]), 1] if cur is None else [cur[0], float(p["fin_s"]), cur[2] + 1]
        elif cur:
            s.append(tuple(cur))
            cur = None
    if cur:
        s.append(tuple(cur))
    return s


def cmd_mesures(a):
    meta = lire_meta(a.dossier)
    A = dossier_analyse(a.dossier)
    fps, duree = meta["fps"], meta["duree_s"]
    plans = lire_plans(a.dossier)
    M = dict(video=dict(titre=meta["titre"], auteur=meta.get("auteur", ""), source=meta["source"], duree_s=duree, images_par_seconde=fps))
    notes = {}

    # Parts du temps, plans, coupes.
    temps = Counter()
    for p in plans:
        temps[p["famille"]] += float(p["duree_s"])
    M["parts"] = {k: round(v / duree, 3) for k, v in temps.most_common()}
    tiers = []
    for k in range(3):
        c = famille_sur(plans, k * duree / 3, (k + 1) * duree / 3)
        tiers.append({f: round(c[f] / (duree / 3), 2) for f in M["parts"]})
    M["parts_par_tiers"] = dict(debut=tiers[0], milieu=tiers[1], fin=tiers[2])
    M["plans"] = dict(n=len(plans), coupes_par_minute=round((len(plans) - 1) / duree * 60, 1),
                      coupes_sautees=sum(p["source_coupe"] == "saut" for p in plans),
                      duree_mediane_s={f: med([float(p["duree_s"]) for p in plans if p["famille"] == f]) for f in M["parts"]})

    # Le visage : blocs, retours, absences.
    blocs = suites(plans, lambda p: p["famille"] == "visage")
    if blocs:
        d = [f - s for s, f, _ in blocs]
        trous = [blocs[0][0]] + [blocs[k + 1][0] - blocs[k][1] for k in range(len(blocs) - 1)] + [duree - blocs[-1][1]]
        trous = [t for t in trous if t > 0.2]
        M["visage"] = dict(blocs=len(blocs), bloc_median_s=med(d), bloc_p10_p90_s=pct(d, [10, 90]), bloc_max_s=round(max(d), 1),
                           retours_par_minute=round(len(blocs) / duree * 60, 1),
                           absence_mediane_s=med(trous, 1), absence_max_s=round(max(trous), 1) if trous else 0)
    seq = suites(plans, lambda p: p["famille"] != "visage")
    if seq:
        d = [f - s for s, f, _ in seq]
        M["sequences_sans_visage"] = dict(n=len(seq), mediane_s=med(d, 1), p10_p90_s=pct(d, [10, 90]), max_s=round(max(d), 1))

    # Signaux : dérive de la caméra entre deux mouvements, zoom lent du visage.
    S = np.load(A / "signaux.npz") if (A / "signaux.npz").exists() else None
    mouv = lire_csv(A / "mouvements.csv") if (A / "mouvements.csv").exists() else []
    if S is not None and blocs:
        taux = []
        for p in plans:
            if p["famille"] == "visage" and p["b"] - p["a"] >= fps:
                sl = slice(p["a"] + 2, p["b"] - 1)
                bon = S["inl"][sl] >= 0.5
                if bon.mean() >= 0.5:
                    taux.append(float(np.log(S["sc"][sl][bon]).mean() * fps * 100))
        if taux:
            M["visage"].update(zoom_pct_par_s_median=med(taux), plans_qui_zooment_part=round(float(np.mean(np.array(taux) > 0.3)), 2))
            notes["visage.zoom_pct_par_s_median"] = "indicatif : un visage qui bouge trouble la mesure, à confirmer sur planche"

    if mouv:
        deb = np.array([float(r["debut_s"]) for r in mouv])
        fin = np.array([float(r["fin_s"]) for r in mouv])
        meme = np.array([mouv[k]["plan"] == mouv[k + 1]["plan"] for k in range(len(mouv) - 1)])
        inter, pauses = np.diff(deb)[meme], (deb[1:] - fin[:-1])[meme]
        anim_s = sum(temps[f] for f in ANIMEES)
        par_seq = [sum(s <= t < f for t in deb) for s, f, _ in seq] if seq else []
        M["mouvements"] = dict(n=len(mouv), un_toutes_les_s=round(anim_s / len(mouv), 2) if len(mouv) else None,
                               intervalle_median_s=med(inter), intervalle_p25_p75_s=pct(inter, [25, 75]),
                               pause_mediane_ms=med(pauses * 1000, 0), arret_max_s=round(float(pauses.max()), 2) if len(pauses) else None,
                               arret_p90_s=pct(pauses, [90])[0] if len(pauses) else None,
                               duree_mediane_ms=med([float(r["duree_ms"]) for r in mouv], 0),
                               par_sequence_median=med([x for x in par_seq if x], 0),
                               genres=dict(Counter(r["genre_auto"] for r in mouv)),
                               types=dict(Counter(r["type"] for r in mouv if r["type"]).most_common()))
        par_type = {}
        for t, n in Counter(r["type"] for r in mouv if r["type"]).most_common():
            lot = [r for r in mouv if r["type"] == t]
            par_type[t] = dict(n=n, duree_mediane_ms=med([float(r["duree_ms"]) for r in lot], 0),
                               fondu_median_ms=med([float(r["fondu_ms"]) for r in lot if r["fondu_ms"] != ""], 0),
                               vol_median_ms=med([float(r["cles_ms"]) for r in lot if r["fiable"] == "True"], 0))
        if par_type:
            M["mouvements_par_type"] = par_type
        cam = [r for r in mouv if r["genre_auto"] != "element"]
        ok = [r for r in cam if r["fiable"] == "True"]
        if cam:
            M["camera"] = dict(n=len(cam), n_fiables=len(ok), part_des_mouvements=round(len(cam) / len(mouv), 2))
        if ok:
            x1 = [float(r["bezier"].split(",")[0]) for r in ok]
            x2 = [float(r["bezier"].split(",")[2]) for r in ok]
            M["camera"].update(vol_ms_p25_p50_p75=[int(v) for v in np.percentile([float(r["cles_ms"]) for r in ok], [25, 50, 75])],
                               courbe_mediane=[med(x1), 0, med(x2), 1],
                               part_en_s=round(float(np.mean((np.array(x1) >= 0.4) & (np.array(x2) <= 0.6))), 2),
                               zoom_abs_median_pct=med([abs(float(r["zoom_pct"])) for r in ok if r["genre_auto"] == "camera-zoom"], 0))
        el = [r for r in mouv if r["entree_ms"]]
        if el:
            e = np.array([float(r["entree_ms"]) for r in el])
            fd = np.array([float(r["fondu_ms"]) for r in el if r["fondu_ms"] != ""])
            M["entrees"] = dict(n_mesurees=len(el), installation_ms_p25_p50_p75=[int(v) for v in np.percentile(e, [25, 50, 75])],
                                fondu_local_ms_p25_p50_p75=[int(v) for v in np.percentile(fd, [25, 50, 75])] if len(fd) else None,
                                part_d_un_coup=round(float(np.mean(fd <= 1000 / fps)), 2) if len(fd) else None,
                                courbes=dict(Counter(r["courbe"] for r in el if r["courbe"]).most_common()))
            notes["entrees"] = ("installation = temps pour que tout le mouvement soit en place (plusieurs éléments en cascade compris) ; "
                                "fondu local = temps d'apparition d'un point de l'image ; d'un coup = en une image")
        if S is not None:
            calme = np.zeros(meta["n_images"], bool)
            for p in plans:
                if p["famille"] in ANIMEES:
                    calme[p["a"] + 3:p["b"] - 2] = True
            for r in mouv:
                calme[max(0, int(float(r["debut_s"]) * fps) - 3):int(float(r["fin_s"]) * fps) + 3] = False
            bon = calme & (S["inl"] >= 0.6) & (S["npt"] >= 40)
            if bon.sum() > 5 * fps:
                t = np.log(S["sc"][bon]) * fps * 100
                M.setdefault("camera", {}).update(derive_pct_par_s_median=med(t), derive_part_du_temps=round(float(np.mean(np.abs(t) > 0.3)), 2))
                notes["camera.derive_pct_par_s_median"] = "zoom continu entre deux mouvements ; proche de 0 = caméra immobile"

    # La voix et le son.
    if (A / "mots.json").exists():
        mots = lire_mots(a.dossier)
        pauses_s = pauses_de_la_voix(a.dossier)
        pauses = np.array([f - s for s, f in pauses_s if s > 0.5 and f < duree - 0.5])
        M["voix"] = dict(mots=len(mots), mots_par_minute=round(len(mots) / duree * 60), pauses_de_0_2_s_et_plus=len(pauses),
                         pause_mediane_s=med(pauses), pause_p95_s=pct(pauses, [95])[0] if len(pauses) else None,
                         pause_max_s=round(float(pauses.max()), 2) if len(pauses) else None,
                         part_du_temps_en_silence=round(float(pauses.sum() / duree), 3) if len(pauses) else 0)
        if meta["audio"] and (A / "audio.wav").exists():
            import soundfile as sf
            import scipy.signal as sg
            x, sr = sf.read(A / "audio.wav")
            x = x if x.ndim == 2 else np.c_[x, x]
            mid, cote = x.mean(1), (x[:, 0] - x[:, 1]) / 2
            db = lambda v: 20 * np.log10(np.maximum(v, 1e-9))
            hop = sr // 100
            env = lambda v: np.sqrt((v[:len(v) // hop * hop].reshape(-1, hop) ** 2).mean(1))
            e_mid = env(mid)
            parle = np.zeros(len(e_mid), bool)
            for d, f, *_ in mots:
                parle[int(d * 100):int(f * 100) + 1] = True
            silence = np.zeros(len(e_mid), bool)
            for s0, f0 in pauses_s:
                silence[int(s0 * 100) + 3:int(f0 * 100) - 3] = True
            parle &= ~silence
            M["son"] = dict(niveau_voix_db=med(db(e_mid[parle]), 1))
            if silence.sum() > 50:
                M["son"]["niveau_entre_les_phrases_db"] = med(db(e_mid[silence]), 1)
                notes["son.niveau_entre_les_phrases_db"] = "au-dessus de −50 dB : il y a un fond sonore (musique, ambiance) sous la voix"
            if mouv:
                niveau = lambda v: float(db(np.sqrt(np.mean(v ** 2))))
                stereo = niveau(cote) > max(niveau(mid) - 40, -70)  # la voix est au centre : les côtés portent musique et bruitages
                piste = cote if stereo else sg.sosfilt(sg.butter(4, 5000, btype="high", fs=sr, output="sos"), mid)
                d = db(env(piste))
                montee = d - np.r_[[d[0]] * 8, d[:-8]]
                pk, _ = sg.find_peaks(montee, height=12, distance=20)
                att = pk / 100
                touche = lambda ts: float(np.mean([np.any(np.abs(att - t) <= 0.15) for t in ts])) if len(att) and len(ts) else 0.0
                rng = np.random.default_rng(0)
                hasard = float(np.mean([touche(rng.uniform(1, duree - 1, len(deb))) for _ in range(200)]))
                M["son"].update(attaques_par_minute=round(len(att) / duree * 60, 1),
                                mouvements_avec_attaque_pct=round(100 * touche(deb)), au_hasard_pct=round(100 * hasard),
                                piste_ecoutee="côtés de la stéréo" if stereo else "aigus au-dessus de 5 kHz")
                notes["son.mouvements_avec_attaque_pct"] = "nettement au-dessus du hasard : les animations sont bruitées ; proche : non, ou non mesurable"
    if (A / "phrases_stats.json").exists():
        M["phrases"] = json.loads((A / "phrases_stats.json").read_text(encoding="utf-8"))
    if (A / "couleurs.json").exists():
        M["couleurs"] = json.loads((A / "couleurs.json").read_text(encoding="utf-8"))

    # Tolérances proposées pour contrôler un montage : la dispersion entre les trois tiers de la vidéo, élargie.
    def plage(cle):
        v = [t.get(cle, 0) for t in tiers]
        return [round(max(0, min(v) - 0.05), 2), round(min(1, max(v) + 0.05), 2)]
    C = {}
    if "visage" in M["parts"]:
        C["part_visage"] = plage("visage")
    if "animation" in M["parts"]:
        C["part_animation"] = plage("animation")
    if "visage" in M:
        C.update(absence_visage_max_s=round(M["visage"]["absence_max_s"]), bloc_visage_median_s=[round(M["visage"]["bloc_median_s"] * 0.7, 1), round(M["visage"]["bloc_median_s"] * 1.4, 1)])
    if M.get("mouvements", {}).get("un_toutes_les_s"):
        u = M["mouvements"]["un_toutes_les_s"]
        C.update(intervalle_entre_animations_s=[round(u * 0.8, 1), round(u * 1.25, 1)])
    if "voix" in M and M["voix"]["pause_max_s"] is not None:
        C["pause_voix_max_s"] = M["voix"]["pause_max_s"]
    M["controle_propose"] = C
    notes["controle_propose"] = "proposition calculée : la fiche les reprend comme des choix, pas comme des mesures"
    M["notes"] = notes
    (A / "mesures.json").write_text(json.dumps(M, ensure_ascii=False, indent=1), encoding="utf-8")

    # Version lisible.
    L = [f"# Mesures — {meta['titre']}", "", f"Source : {meta['source']}" + (f" ({meta['auteur']})" if meta.get("auteur") else ""), f"Durée : {tc(duree)} à {fps} images par seconde.", "",
         "Chaque chiffre vient d'un fichier du dossier `analyse/`. Un chiffre absent de cette page n'a pas été mesuré.", ""]

    def section(titre, bloc):
        L.append(f"## {titre}\n")
        L.append("| Mesure | Valeur |\n|---|---|")
        for k, v in bloc.items():
            L.append(f"| {k.replace('_', ' ')} | {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v} |")
        L.append("")
    noms = dict(parts="Part du temps par famille", parts_par_tiers="Début, milieu, fin", plans="Plans et coupes", visage="Le visage",
                sequences_sans_visage="Séquences sans visage", mouvements="Animations", mouvements_par_type="Animations par type", camera="Caméra virtuelle", entrees="Entrées d'éléments",
                voix="La voix", son="Le son", phrases="Phrases et image", controle_propose="Tolérances proposées pour le contrôle")
    for k, titre in noms.items():
        if k in M:
            section(titre, M[k])
    if "couleurs" in M:
        L.append("## Couleurs\n\nVoir `analyse/couleurs.json` et le nuancier `analyse/planches/couleurs.jpg`.\n")
    if notes:
        L.append("## À lire avec prudence\n")
        L += [f"- `{k}` : {v}" for k, v in notes.items()] + [""]
    (Path(a.dossier) / "MESURES.md").write_text("\n".join(L), encoding="utf-8")
    print(f"mesures.json et MESURES.md écrits ({len([k for k in noms if k in M])} sections).")
    for k in ("parts", "visage", "mouvements", "camera"):
        if k in M:
            print(f"  {k} : {json.dumps(M[k], ensure_ascii=False)[:260]}")


# ───────────────────────────── planche, empaqueter ─────────────────────────────

def cmd_planche(a):
    meta = lire_meta(a.dossier)
    A = dossier_analyse(a.dossier)
    W, H = taille_travail(meta)
    cap = ouvrir(a.dossier)
    tw = a.largeur
    th = int(round(tw * H / W / 2) * 2)
    vigs = [vignette(image_a(cap, min(meta["n_images"] - 1, round(t * meta["fps"]))), tw, th, tc(t)) for t in a.temps]
    sortie = A / "planches" / f"{a.nom}.jpg"
    sortie.parent.mkdir(exist_ok=True)
    cv2.imwrite(str(sortie), mosaique(vigs, a.colonnes), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(sortie)


def cmd_empaqueter(a):
    d = Path(a.dossier).resolve()
    skill = d / "SKILL.md"
    if not skill.exists():
        sys.exit("Pas de SKILL.md dans le dossier du style.")
    texte = skill.read_text(encoding="utf-8")
    reste = {}
    for p in d.rglob("*.md"):
        if "analyse" in p.relative_to(d).parts or p.name == "MESURES.md":
            continue
        trouves = set(re.findall(r"\{\{[^}]+\}\}", p.read_text(encoding="utf-8", errors="ignore")))
        if trouves:
            reste[str(p.relative_to(d))] = sorted(trouves)
    if reste:
        sys.exit("Il reste des emplacements à remplir :\n" + "\n".join(f"  {k} : {', '.join(v[:5])}{' …' if len(v) > 5 else ''}" for k, v in reste.items()))
    m = re.search(r'^name:\s*"?([a-z0-9-]+)"?\s*$', texte, re.M)
    if not m:
        sys.exit("SKILL.md : l'en-tête doit porter « name: » en minuscules, chiffres et tirets.")
    nom = m.group(1)
    exclus = {"analyse", "renders", "snapshots", "node_modules"}
    sortie = d.parent / f"{nom}.zip"
    n = 0
    with zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(d.rglob("*")):
            rel = f.relative_to(d)
            if f.is_dir() or any(p.startswith(".") or p in exclus for p in rel.parts) or rel.name == "MESURES.md" or rel.name.startswith("export-"):
                continue
            z.write(f, Path(nom) / rel)
            n += 1
    print(f"Paquet prêt : {sortie} ({n} fichiers, {sortie.stat().st_size // 1024} Ko). Aucune image de la vidéo d'origine dedans.")


# ───────────────────────────── ligne de commande ─────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="commande", required=True)

    def cmd(nom, fonction, *args):
        p = sp.add_parser(nom)
        for noms, kw in args:
            p.add_argument(*noms, **kw)
        p.add_argument("dossier", help="dossier du style")
        p.set_defaults(f=fonction)

    sp.add_parser("verifier").set_defaults(f=cmd_verifier)
    cmd("demarrer", cmd_demarrer)
    cmd("recuperer", cmd_recuperer, (["source"], dict(help="lien de la vidéo ou fichier local")),
        (["--de"], dict(help="début de l'extrait, en secondes")), (["--a"], dict(help="fin de l'extrait, en secondes")))
    cmd("plans", cmd_plans)
    cmd("signaux", cmd_signaux, (["--refaire"], dict(action="store_true", help="recalculer même si signaux.npz existe")))
    cmd("etiqueter", cmd_etiqueter)
    cmd("mouvements", cmd_mouvements)
    cmd("couleurs", cmd_couleurs)
    cmd("phrases", cmd_phrases)
    cmd("croiser", cmd_croiser, (["--ligne"], dict(default="nature")), (["--colonne"], dict(default="a_l_ecran")))
    cmd("mesures", cmd_mesures)
    cmd("planche", cmd_planche, (["--temps"], dict(type=float, nargs="+", required=True, help="instants en secondes")),
        (["--nom"], dict(default="verification")), (["--colonnes"], dict(type=int, default=4)), (["--largeur"], dict(type=int, default=480)))
    cmd("empaqueter", cmd_empaqueter)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
