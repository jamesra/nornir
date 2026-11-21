"""Before/now/fixed seam review page for one section.

usage: review_page.py <spec.json>
spec: {"section": 11, "out": "/storage4/MosaicRecovery/RC2/11/review_fix", "title": "...", "intro": "...",
       "layouts": [{"label": "2015", "mosaic": "<path>", "png": "<ds16 png>"}, ...],
       "pairs": [{"a": 29, "b": 46, "note": "..."}], "links": [["label", "href"]]}
Crops are centred on the midpoint of the two tiles' centres in each layout (ds16, 240 px -> 480 px)."""
import html
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

import place_tiles as pt

Image.MAX_IMAGE_PIXELS = None
R = 150


def centre(ts: dict, t: int) -> np.ndarray:
    """Tile centre (Y, X) in full-res px."""
    b = ts[t].TargetSpaceBoundingBox
    return np.array([(b.MinY + b.MaxY) / 2, (b.MinX + b.MaxX) / 2])


def crop(img: np.ndarray, c: np.ndarray, marks: list[np.ndarray]) -> Image.Image:
    """2R x 2R crop of img around c (ds16 px), zero-padded, with tile-centre marks, scaled 2x."""
    r, cc = int(c[0]), int(c[1])
    out = np.zeros((2 * R, 2 * R), np.uint8)
    r0, c0 = r - R, cc - R
    rs, cs = max(r0, 0), max(c0, 0)
    re_, ce = min(r0 + 2 * R, img.shape[0]), min(c0 + 2 * R, img.shape[1])
    if re_ > rs and ce > cs:
        out[rs - r0:re_ - r0, cs - c0:ce - c0] = img[rs:re_, cs:ce]
    im = Image.fromarray(out).convert("RGB").resize((4 * R, 4 * R), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for m in marks:
        y, x = (m[0] - r0) * 2, (m[1] - c0) * 2
        d.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(255, 60, 60), width=3)
    return im


def main() -> None:
    """Write crops and index.html."""
    spec = json.load(open(sys.argv[1]))
    out = spec["out"]
    os.makedirs(out, exist_ok=True)
    lays = []
    for L in spec["layouts"]:
        ts = pt.tiles_of(L["mosaic"])
        b = ts.TargetBoundingBox
        img = np.asarray(Image.open(L["png"]).convert("L"))
        lays.append((L["label"], ts, np.array([b.MinY, b.MinX]), img))
    cards = []
    for p in spec["pairs"]:
        a, b = p["a"], p["b"]
        figs = []
        for label, ts, origin, img in lays:
            if a not in ts or b not in ts:
                figs.append(f"<figure><div class='na'>tile missing</div><figcaption>{html.escape(label)}</figcaption></figure>")
                continue
            ca, cb = (centre(ts, a) - origin) / 16, (centre(ts, b) - origin) / 16
            name = f"{a}_{b}_{label.split()[0]}.jpg".replace("/", "_")
            crop(img, (ca + cb) / 2, [ca, cb]).save(os.path.join(out, name), quality=85)
            figs.append(f"<figure><a href='{name}'><img src='{name}' loading='lazy'></a><figcaption>{html.escape(label)}</figcaption></figure>")
        ref = lays[-1]
        c = ((centre(ref[1], a) + centre(ref[1], b)) / 2 - ref[2]) / 16 if a in ref[1] and b in ref[1] else None
        where = f"ds16 x {int(c[1])}, y {int(c[0])}" if c is not None else ""
        cards.append(f"<section><h2>{a} &amp; {b} <small>{where}</small></h2><p class='m'>{html.escape(p.get('note', ''))}</p>"
                     f"<div class='row' style='grid-template-columns:repeat({len(lays)},1fr)'>{''.join(figs)}</div></section>")
    links = " · ".join(f"<a href='{h}'>{html.escape(t)}</a>" for t, h in spec.get("links", []))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(spec['title'])}</title><style>
:root{{--bg:#f4f5f3;--ink:#1d2124;--muted:#5f676d;--card:#fff;color-scheme:light dark}}
@media(prefers-color-scheme:dark){{:root{{--bg:#15191b;--ink:#e5e9e7;--muted:#9aa4a8;--card:#1e2427}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif;padding:20px 16px 48px}}
main{{max-width:1200px;margin:auto;display:grid;gap:22px}}h1{{margin:0;font-size:1.45rem}}
h2{{margin:0 0 4px;font-size:1rem;font-family:ui-monospace,monospace;font-weight:600}}small,figcaption,.m{{color:var(--muted)}}
section{{background:var(--card);border-radius:10px;padding:14px}}.row{{display:grid;gap:10px}}
figure{{margin:0}}img{{width:100%;height:auto;display:block;border-radius:6px}}.na{{aspect-ratio:1;display:grid;place-items:center;background:#0003;border-radius:6px}}
@media(max-width:700px){{.row{{grid-template-columns:1fr!important}}}}</style></head><body><main>
<h1>{html.escape(spec['title'])}</h1><p>{spec.get('intro', '')}</p><p>{links}</p>{''.join(cards)}</main></body></html>"""
    open(os.path.join(out, "index.html"), "w").write(page)
    print(out, len(cards), "pairs")


if __name__ == "__main__":
    main()
