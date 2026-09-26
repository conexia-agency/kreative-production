#!/usr/bin/env python3
"""atelier.py : galerie visuelle type Cowork pour une commande.

Produit commandes/<ardoise>/atelier.html : planches banque, refs absorbees,
captures site, masters. La session et l'humain jugent dessus. Ce n'est pas
de l'OCR : Claude lit les images (outil Read) ; l'atelier sert a voir en grand.

    python3 pipeline/atelier.py <ardoise>
    python3 pipeline/atelier.py <ardoise> --ouvrir
    python3 kreative.py atelier <ardoise>

Cible Python 3.9+. Aucune dependance externe.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

from etat import Commande  # noqa: E402
import banque as module_banque  # noqa: E402


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _rel(path: Path, base: Path, depot: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        try:
            return Path("../..") / path.resolve().relative_to(depot.resolve())
        except ValueError:
            return path.resolve().as_uri()


def _card(src: str, caption: str, note: str = "") -> str:
    note_html = f'<p class="note">{_esc(note)}</p>' if note else ""
    return (
        f'<figure class="card" data-src="{_esc(src)}">'
        f'<button type="button" class="thumb" aria-label="Agrandir {_esc(caption)}">'
        f'<img loading="lazy" src="{_esc(src)}" alt="{_esc(caption)}">'
        f"</button>"
        f"<figcaption><strong>{_esc(caption)}</strong>{note_html}</figcaption>"
        f"</figure>"
    )


def collecter(commande: Commande) -> Dict[str, object]:
    dossier = commande.dossier
    depot = ICI.parent
    try:
        racine_banque = module_banque._racine_banque()
    except FileNotFoundError:
        racine_banque = None

    planches: List[Path] = []
    if racine_banque is not None:
        planches_dir = racine_banque / "_PLANCHES"
        if planches_dir.is_dir():
            planches = sorted(planches_dir.glob("PLANCHE_*.jpg")) + sorted(
                planches_dir.glob("PLANCHE_*.png")
            )

    etat = {}
    banque_json = dossier / "session" / "banque.json"
    if banque_json.exists():
        try:
            etat = json.loads(banque_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            etat = {}

    attendues = set(etat.get("planches_attendues") or [])
    if attendues and planches:
        planches = [
            p
            for p in planches
            if p.stem.replace("PLANCHE_", "") in attendues
            or p.stem in attendues
        ] or planches

    refs_dir = dossier / "session" / "references"
    refs = sorted(refs_dir.glob("*.jpg")) + sorted(refs_dir.glob("*.png")) if refs_dir.is_dir() else []
    absorbees = etat.get("references_absorbees") or {}
    if not isinstance(absorbees, dict):
        absorbees = {}

    captures_dir = dossier / "marque" / "captures"
    captures = []
    if captures_dir.is_dir():
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            captures.extend(captures_dir.glob(ext))
        captures = sorted(captures)

    masters_dir = dossier / "masters"
    masters = []
    if masters_dir.is_dir():
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            masters.extend(masters_dir.glob(ext))
        masters = sorted(masters)

    assets_dir = dossier / "assets"
    assets = []
    if assets_dir.is_dir():
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            assets.extend(assets_dir.glob(ext))
        assets = sorted(assets)

    return {
        "ardoise": dossier.name,
        "marque": commande.donnees.get("marque") or dossier.name,
        "depot": depot,
        "dossier": dossier,
        "planches": planches,
        "refs": refs,
        "absorbees": absorbees,
        "captures": captures,
        "masters": masters,
        "assets": assets,
    }


def rendre(inv: Dict[str, object]) -> str:
    dossier: Path = inv["dossier"]  # type: ignore
    depot: Path = inv["depot"]  # type: ignore
    ardoise = inv["ardoise"]
    marque = inv["marque"]

    def cards(paths: List[Path], notes: Optional[Dict[str, str]] = None) -> str:
        notes = notes or {}
        bits = []
        for p in paths:
            src = _rel(p, dossier, depot)
            if isinstance(src, Path):
                src = src.as_posix()
            bits.append(_card(str(src), p.stem, str(notes.get(p.stem, "") or "")))
        return "\n".join(bits) if bits else '<p class="meta">Rien ici pour le moment.</p>'

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Atelier {_esc(str(marque))}</title>
<style>
  :root {{
    --bg: #0f1216; --panel: #1a1f26; --ink: #f3f0ea; --muted: #9aa3ad;
    --line: rgba(255,255,255,.12); --accent: #e8c547;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--ink); }}
  header {{ position: sticky; top: 0; z-index: 5; backdrop-filter: blur(10px);
    background: rgba(15,18,22,.94); border-bottom: 1px solid var(--line);
    padding: 14px 20px; display: flex; gap: 16px; flex-wrap: wrap;
    align-items: center; justify-content: space-between; }}
  header h1 {{ margin: 0; font-size: 16px; font-weight: 600; }}
  header p {{ margin: 4px 0 0; color: var(--muted); font-size: 13px; }}
  nav {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  nav a {{ color: var(--ink); text-decoration: none; font-size: 12px;
    border: 1px solid var(--line); padding: 6px 10px; border-radius: 999px; }}
  nav a:hover {{ border-color: var(--accent); }}
  main {{ padding: 20px; max-width: 1400px; margin: 0 auto; }}
  .banner {{ border: 1px solid var(--line); background: var(--panel);
    border-radius: 12px; padding: 12px 14px; margin-bottom: 22px; font-size: 13px;
    color: var(--muted); line-height: 1.45; }}
  .banner strong {{ color: var(--ink); }}
  section {{ margin-bottom: 36px; }}
  section h2 {{ margin: 0 0 8px; font-size: 13px; text-transform: uppercase;
    letter-spacing: .08em; color: var(--muted); }}
  .meta {{ color: var(--muted); font-size: 12px; margin: 0 0 12px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }}
  .card {{ margin: 0; background: var(--panel); border: 1px solid var(--line);
    border-radius: 12px; overflow: hidden; }}
  .thumb {{ display: block; width: 100%; padding: 0; border: 0; background: #0a0d11; cursor: zoom-in; }}
  .thumb img {{ display: block; width: 100%; aspect-ratio: 1; object-fit: cover; }}
  figcaption {{ padding: 10px 12px 12px; font-size: 12px; }}
  figcaption strong {{ display: block; margin-bottom: 4px; }}
  .note {{ margin: 0; color: var(--muted); line-height: 1.35; }}
  dialog {{ border: 1px solid var(--line); border-radius: 14px; padding: 0;
    background: #0a0d11; color: var(--ink); max-width: min(96vw, 1100px); width: 96vw; }}
  dialog::backdrop {{ background: rgba(0,0,0,.75); }}
  dialog .frame {{ padding: 12px; }}
  dialog img {{ width: 100%; height: auto; display: block; border-radius: 8px; }}
  dialog .bar {{ display: flex; justify-content: space-between; align-items: center;
    gap: 12px; padding: 10px 14px; border-top: 1px solid var(--line); font-size: 13px; }}
  dialog button {{ background: transparent; color: var(--ink); border: 1px solid var(--line);
    border-radius: 999px; padding: 6px 12px; cursor: pointer; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>Atelier {_esc(str(marque))}</h1>
    <p>Mode Cowork local · {_esc(str(ardoise))} · Claude lit (Read), toi tu tranches</p>
  </div>
  <nav>
    <a href="#planches">Planches ({len(inv['planches'])})</a>
    <a href="#refs">Refs ({len(inv['refs'])})</a>
    <a href="#captures">Captures ({len(inv['captures'])})</a>
    <a href="#assets">Assets ({len(inv['assets'])})</a>
    <a href="#masters">Masters ({len(inv['masters'])})</a>
  </nav>
</header>
<main>
  <div class="banner">
    <strong>Systeme type Cowork.</strong>
    La session doit ouvrir chaque image utile avec l'outil Read avant d'ecrire
    un plan ou de generer. Cet atelier sert a voir en grand (toi + relecture).
    Ce n'est pas de l'OCR. Relancer :
    <code>python3 pipeline/atelier.py {_esc(str(ardoise))} --ouvrir</code>
  </div>

  <section id="planches">
    <h2>Planches banque</h2>
    <p class="meta">CREAS INSPI DELIVERY / _PLANCHES</p>
    <div class="grid">{cards(inv['planches'])}</div>
  </section>

  <section id="refs">
    <h2>References absorbees</h2>
    <p class="meta">session/references + phrases --vu</p>
    <div class="grid">{cards(inv['refs'], inv['absorbees'])}</div>
  </section>

  <section id="captures">
    <h2>Captures site</h2>
    <p class="meta">marque/captures</p>
    <div class="grid">{cards(inv['captures'])}</div>
  </section>

  <section id="assets">
    <h2>Assets client</h2>
    <p class="meta">assets/ (PJ numerotes)</p>
    <div class="grid">{cards(inv['assets'])}</div>
  </section>

  <section id="masters">
    <h2>Masters generes</h2>
    <p class="meta">masters/</p>
    <div class="grid">{cards(inv['masters'])}</div>
  </section>
</main>
<dialog id="lightbox">
  <div class="frame"><img alt=""></div>
  <div class="bar"><span id="lb-caption"></span><button type="button" id="lb-close">Fermer</button></div>
</dialog>
<script>
const dlg = document.getElementById('lightbox');
const img = dlg.querySelector('img');
const cap = document.getElementById('lb-caption');
document.querySelectorAll('.card').forEach(card => {{
  card.querySelector('.thumb').addEventListener('click', () => {{
    img.src = card.dataset.src;
    img.alt = card.querySelector('strong').textContent;
    cap.textContent = card.querySelector('strong').textContent;
    dlg.showModal();
  }});
}});
document.getElementById('lb-close').onclick = () => dlg.close();
dlg.addEventListener('click', e => {{ if (e.target === dlg) dlg.close(); }});
</script>
</body>
</html>
"""
    return html


def ecrire(commande: Commande, ouvrir: bool = False) -> Path:
    inv = collecter(commande)
    cible = commande.dossier / "atelier.html"
    cible.write_text(rendre(inv), encoding="utf-8")
    if ouvrir:
        try:
            subprocess.run(["open", str(cible)], check=False)
        except OSError:
            pass
    return cible


def main() -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("ardoise")
    parseur.add_argument("--ouvrir", action="store_true", help="ouvrir dans le navigateur")
    a = parseur.parse_args()
    try:
        commande = Commande.charger(a.ardoise)
    except FileNotFoundError as err:
        print(f"Erreur : {err}", file=sys.stderr)
        return 1
    chemin = ecrire(commande, a.ouvrir)
    inv = collecter(commande)
    print(f"Atelier : {chemin}")
    print(
        f"  planches {len(inv['planches'])} · refs {len(inv['refs'])} · "
        f"captures {len(inv['captures'])} · assets {len(inv['assets'])} · "
        f"masters {len(inv['masters'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
