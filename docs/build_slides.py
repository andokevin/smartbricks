"""Génère docs/SmartBricks_presentation.pptx (16:9) avec python-pptx.

Lancement, depuis la racine du projet (python-pptx n'est pas une dépendance de l'API) :
    uv pip install --python backend/.venv/bin/python python-pptx
    backend/.venv/bin/python docs/build_slides.py

- Une diapositive par section de docs/07_PRESENTATION.md ; le script oral de chaque section
  est copié dans les NOTES de l'orateur (une seule source de vérité : le fichier Markdown).
- Les schémas (enchaînement, sac à dos, Pareto, planning, tournée, architecture) sont dessinés
  avec des formes natives PowerPoint (rectangles arrondis, flèches, connecteurs), pas des images.
- Tous les chiffres sont ceux mesurés sur le projet de démonstration (voir 02_PLAN_DE_TEST.md
  et benchmark_resultats.json).

Vérification visuelle : convertir en PDF (LibreOffice : soffice --headless --convert-to pdf,
ou export PDF de PowerPoint), puis en images, et contrôler chaque diapositive.
"""

from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

DOCS = Path(__file__).resolve().parent
OUT = DOCS / "SmartBricks_presentation.pptx"
SCRIPT_MD = DOCS / "07_PRESENTATION.md"

# --------------------------------------------------------------------------- charte
BLUE = RGBColor(0x1E, 0x5A, 0xA8)
TERRA = RGBColor(0xC8, 0x61, 0x2D)
LIGHT = RGBColor(0xF6, 0xF4, 0xEF)
DARK = RGBColor(0x16, 0x21, 0x3A)
TEXT = RGBColor(0x1B, 0x23, 0x33)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x5B, 0x64, 0x75)  # texte secondaire sur fond clair
GRID = RGBColor(0xC9, 0xC4, 0xB8)  # axes et traits discrets
BLUE_TINT = RGBColor(0xDC, 0xE7, 0xF5)
TERRA_TINT = RGBColor(0xF6, 0xE0, 0xD3)
SOFT_ON_DARK = RGBColor(0xC9, 0xD3, 0xE6)
FONT = "Calibri"

W, H = 13.333, 7.5  # pouces, 16:9


# --------------------------------------------------------------------------- notes depuis le Markdown


def load_scripts() -> dict[int, str]:
    """{numéro de diapositive: script oral}, lu dans 07_PRESENTATION.md."""
    text = SCRIPT_MD.read_text(encoding="utf-8")
    scripts: dict[int, str] = {}
    for m in re.finditer(r"^## Diapositive (\d+)[^\n]*\n(.*?)(?=^---|^## )", text, re.S | re.M):
        num, body = int(m.group(1)), m.group(2)
        part = body.split("**Script", 1)[1] if "**Script" in body else ""
        lines = []
        for line in part.splitlines()[1:]:
            line = line.strip()
            if line.startswith(">"):
                lines.append(line.lstrip("> ").replace("**", ""))
            elif line.startswith("*Plan B"):
                lines.append(line.strip("*"))
        scripts[num] = "\n".join(lines).strip()
    return scripts


# --------------------------------------------------------------------------- briques de dessin


NBSP = " "
_UNITS = r"(?:ms|s|h|j|jours?|km|Ar|%|M|nœuds|tests|villes|instances|semaines|agences|millions)"


def nb(s: str) -> str:
    """Typographie française : espaces insécables dans « … », entre milliers et avant une unité,
    pour qu'aucun nombre ne soit séparé de son unité en fin de ligne."""
    s = s.replace("« ", "«" + NBSP).replace(" »", NBSP + "»")
    s = re.sub(r"(\d) (?=\d{3}\b)", r"\1" + NBSP, s)
    s = re.sub(r"(\d) (?=" + _UNITS + r"\b)", r"\1" + NBSP, s)
    return s


def _font(run, size: float, color: RGBColor, bold: bool = False, italic: bool = False) -> None:
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color


def text(slide, x, y, w, h, lines, size=20, color=TEXT, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, italic=False, space_after=6, name=None):
    """Zone de texte. `lines` : chaîne, ou liste de chaînes / listes de (texte, options) par paragraphe."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    if isinstance(lines, str):
        lines = [lines]
    for k, line in enumerate(lines):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        runs = line if isinstance(line, list) else [(line, {})]
        for content, opts in runs:
            r = p.add_run()
            r.text = nb(content)
            _font(r, opts.get("size", size), opts.get("color", color), opts.get("bold", bold),
                  opts.get("italic", italic))
    return box


def box(slide, x, y, w, h, fill, label="", size=20, color=WHITE, bold=True, shape=MSO_SHAPE.ROUNDED_RECTANGLE,
        line=None, radius=0.18, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, name=None):
    """Forme pleine avec texte centré (rectangle arrondi par défaut)."""
    shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        shp.name = name
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        shp.adjustments[0] = radius
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1.5)
    shp.shadow.inherit = False
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = Inches(0.04)
    tf.vertical_anchor = anchor
    labels = label if isinstance(label, list) else [label]
    for k, item in enumerate(labels):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = align
        runs = item if isinstance(item, list) else [(item, {})]
        for content, opts in runs:
            r = p.add_run()
            r.text = nb(content)
            _font(r, opts.get("size", size), opts.get("color", color), opts.get("bold", bold))
    return shp


def arrow(slide, x1, y1, x2, y2, color=MUTED, width=2.25, head=True, dash=False):
    """Connecteur droit, avec pointe de flèche à l'arrivée."""
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    ln = c.line._get_or_add_ln()
    if dash:
        prst = ln.makeelement(qn("a:prstDash"), {"val": "dash"})
        ln.append(prst)
    if head:
        tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
        ln.append(tail)
    return c


def background(slide, color: RGBColor) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def title(slide, label: str, dark: bool = False, width: float = 10.4) -> None:
    text(slide, 0.6, 0.42, width, 0.85, label, size=36, bold=True, color=WHITE if dark else TEXT,
         anchor=MSO_ANCHOR.MIDDLE, name="Titre")


def badge(slide, label: str) -> None:
    """Pastille « numéro du cours » en haut à droite des diapositives d'algorithme."""
    box(slide, 11.15, 0.5, 1.6, 0.7, TERRA, label, size=22, name="Numéro du cours")


def slide_number(slide, n: int, dark: bool = False) -> None:
    text(slide, 12.2, 6.95, 0.75, 0.35, str(n), size=14, color=SOFT_ON_DARK if dark else MUTED,
         align=PP_ALIGN.RIGHT, name="Numéro de diapositive")


def bricks(slide, x, y, colors, size=0.42, gap=0.1) -> None:
    """Motif visuel : une rangée de briques (le « Bricks » de SmartBricks)."""
    for k, c in enumerate(colors):
        box(slide, x + k * (size + gap), y, size, size * 0.62, c, radius=0.25)


# --------------------------------------------------------------------------- diapositives


def s01_cover(s):
    background(s, DARK)
    bricks(s, 0.9, 1.35, [BLUE, TERRA, BLUE, BLUE, TERRA, BLUE], size=0.55)
    text(s, 0.9, 1.95, 11, 1.3, "SmartBricks", size=60, bold=True, color=WHITE)
    text(s, 0.9, 3.25, 11, 0.7, "Du besoin flou au projet informatique réaliste", size=30, color=WHITE)
    text(s, 0.9, 4.05, 11, 0.6, "Copilote IA + algorithmes d'optimisation", size=24, color=TERRA, bold=True)
    text(s, 0.9, 5.7, 11, 0.5, "Soutenance de projet — novembre 2026", size=20, color=SOFT_ON_DARK)


def s02_vision(s):
    background(s, DARK)
    title(s, "Vision", dark=True)
    text(s, 0.9, 1.9, 11.5, 1.6,
         [[("« Oser rêver, réaliser son imagination ", {}),
           ("pour améliorer le quotidien. »", {"color": TERRA})]],
         size=38, bold=True, color=WHITE)
    text(s, 0.9, 3.9, 11, 1.4,
         ["La technologie au service de l'humain.",
          "Un commerçant doit pouvoir lancer son projet numérique sans être informaticien."],
         size=24, color=SOFT_ON_DARK, space_after=12)
    bricks(s, 0.9, 6.1, [BLUE, TERRA, BLUE, TERRA, BLUE, TERRA], size=0.45)


def s03_probleme(s):
    background(s, LIGHT)
    title(s, "Le problème : trop de rêves, peu de moyens")
    card = box(s, 0.6, 1.6, 6.3, 3.2, WHITE, line=GRID, radius=0.06, anchor=MSO_ANCHOR.MIDDLE,
               align=PP_ALIGN.LEFT,
               label=[[("« Un site avec paiement MVola, une appli de suivi, le réseau dans mes 4 agences. "
                        "6 millions d'Ariary, 8 semaines. »", {"size": 24, "color": TEXT, "bold": False})]])
    card.text_frame.margin_left = card.text_frame.margin_right = Inches(0.35)
    text(s, 0.6, 5.05, 6.3, 0.5, "Boutique Soa, cliente de démonstration", size=20, color=MUTED, italic=True)
    stats = [("15,2 M Ar", "de fonctionnalités rêvées (14)", TERRA),
             ("6 M Ar", "de budget", BLUE),
             ("25 · 4", "freelances · agences à visiter", BLUE)]
    for k, (big, small, col) in enumerate(stats):
        y = 1.6 + k * 1.3
        text(s, 7.5, y, 5.3, 0.7, big, size=40, bold=True, color=col)
        text(s, 7.5, y + 0.68, 5.3, 0.45, small, size=20, color=TEXT)


def s04_questions(s):
    background(s, LIGHT)
    title(s, "Cinq questions, cinq problèmes du cours")
    rows = [("Que veut-il vraiment ?", "Dialogue et extraction (IA)", "33"),
            ("Que livrer d'abord ?", "Sac à dos multidimensionnel", "29"),
            ("Avec qui ?", "Agrégation pondérée + Pareto", "22·21"),
            ("Quand ?", "Satisfaction de contraintes", "3"),
            ("Dans quel ordre visiter ?", "Voyageur de commerce", "30")]
    for k, (q, p, n) in enumerate(rows):
        y = 1.55 + k * 1.05
        box(s, 0.6, y, 4.9, 0.8, WHITE, q, size=22, color=TEXT, bold=False, line=GRID, align=PP_ALIGN.LEFT)
        arrow(s, 5.6, y + 0.4, 6.35, y + 0.4, color=MUTED)
        box(s, 6.45, y, 4.9, 0.8, BLUE, p, size=22, align=PP_ALIGN.LEFT)
        box(s, 11.55, y + 0.05, 1.2, 0.7, TERRA, f"n°{n}", size=20)


def s05_flow(s):
    background(s, LIGHT)
    title(s, "La solution : six étapes enchaînées")
    steps = [("Copilote", "n°33"), ("Périmètre", "n°29"), ("Équipe", "n°22 · 21"),
             ("Planning", "n°3"), ("Tournée", "n°30"), ("Explication", "n°33")]
    bw, gap, y = 1.75, 0.31, 2.6
    for k, (name, num) in enumerate(steps):
        x = 0.6 + k * (bw + gap)
        fill = TERRA if k in (0, 5) else BLUE
        box(s, x, y, bw, 1.5, fill, [[(name, {"size": 22})], [(num, {"size": 20, "bold": False})]])
        text(s, x, y - 0.6, bw, 0.45, str(k + 1), size=24, bold=True, color=fill, align=PP_ALIGN.CENTER)
        if k < len(steps) - 1:
            arrow(s, x + bw + 0.02, y + 0.75, x + bw + gap - 0.02, y + 0.75, color=MUTED, width=2.5)
    box(s, 0.6, 4.7, 4.0, 0.6, TERRA_TINT, "IA : comprendre, expliquer", size=20, color=TEXT, bold=False)
    box(s, 4.85, 4.7, 4.6, 0.6, BLUE_TINT, "Algorithmes : décider, prouver", size=20, color=TEXT, bold=False)
    text(s, 0.6, 5.7, 12, 0.6, "Le LLM ne calcule jamais un budget, un planning ou une tournée.",
         size=24, bold=True, color=TEXT)


def s06_copilot(s):
    background(s, LIGHT)
    title(s, "Copilote et sélecteur de méthode")
    badge(s, "n°33")
    chain = ["Une question à la fois", "Brouillon JSON validé", "Contrôles sans IA (Kahn)",
             "Explication : chiffres vérifiés"]
    for k, label in enumerate(chain):
        y = 1.6 + k * 1.2
        box(s, 0.6, y, 5.6, 0.85, TERRA if k in (0, 3) else BLUE, label, size=22)
        if k < len(chain) - 1:
            arrow(s, 3.4, y + 0.87, 3.4, y + 1.18, color=MUTED)
    text(s, 7.0, 1.6, 5.8, 0.5, "Sélecteur (hyper-heuristique)", size=24, bold=True, color=TEXT)
    rules = [("Sac à dos ≤ 40", "exact"), ("Tournée ≤ 12 sites", "Held-Karp"), ("Planning", "3 s max")]
    for k, (cond, meth) in enumerate(rules):
        y = 2.3 + k * 1.0
        box(s, 7.0, y, 3.4, 0.75, WHITE, cond, size=20, color=TEXT, bold=False, line=GRID)
        arrow(s, 10.45, y + 0.375, 10.95, y + 0.375, color=MUTED)
        box(s, 11.0, y, 1.8, 0.75, BLUE, meth, size=20)
    text(s, 7.0, 5.4, 5.8, 0.9, "Démo sans clé ni réseau : fournisseur simulé.", size=20, color=MUTED, italic=True)


def s07_knapsack(s):
    background(s, LIGHT)
    title(s, "Sac à dos : que livrer au sprint 1 ?")
    badge(s, "n°29")
    rows = [("Catalogue", "obligatoire", True), ("Panier", "retenu", True), ("Comptes", "obligatoire", True),
            ("Réseau agences", "obligatoire", True), ("Paiement MVola", "manque 464 000 Ar", False)]
    text(s, 0.6, 1.5, 6.0, 0.45, "Fonctionnalités (4 retenues sur 14)", size=20, bold=True, color=MUTED)
    for k, (name, status, ok) in enumerate(rows):
        y = 2.05 + k * 0.78
        box(s, 0.6, y, 3.2, 0.62, BLUE if ok else WHITE, name, size=20, color=WHITE if ok else TEXT,
            bold=ok, line=None if ok else GRID, align=PP_ALIGN.LEFT)
        box(s, 3.9, y, 2.7, 0.62, BLUE_TINT if ok else TERRA_TINT, ("✓ " if ok else "✗ ") + status,
            size=20 if ok else 18, color=TEXT, bold=False, align=PP_ALIGN.LEFT)
    # Jauges
    gauges = [("Budget", "5 541 000 / 6 000 000 Ar", 0.9235), ("Heures", "136 / 200 h", 0.68)]
    for k, (name, val, ratio) in enumerate(gauges):
        y = 1.55 + k * 1.35
        text(s, 7.1, y, 5.6, 0.45, [[(f"{name}  ", {"bold": True}), (val, {})]], size=20)
        box(s, 7.1, y + 0.55, 5.6, 0.42, WHITE, line=GRID, radius=0.5)
        box(s, 7.1, y + 0.55, 5.6 * ratio, 0.42, BLUE, f"{round(ratio * 100)} %", size=18, radius=0.5)
    et_si = box(s, 7.1, 4.4, 5.6, 1.35, TERRA, align=PP_ALIGN.LEFT, label=[
        [("Et si ? ", {"size": 22}), ("+600 000 Ar (+10 %)", {"size": 22, "bold": False})],
        [("⇒ + Paiement MVola (valeur +80)", {"size": 22})]])
    et_si.text_frame.margin_left = Inches(0.25)
    text(s, 0.6, 6.3, 12, 0.5, "Séparation et évaluation : 18 nœuds au lieu de 16 384 — optimum prouvé",
         size=20, color=TEXT, bold=True)


def s08_matching(s):
    background(s, LIGHT)
    title(s, "Matching : score pondéré et front de Pareto")
    badge(s, "n°22 · 21")
    # Repère : x = coût (0 à 4,5 M Ar), y = durée (0 à 22 jours ouvrés)
    ox, oy, pw, ph = 1.35, 5.75, 5.9, 3.9
    arrow(s, ox, oy, ox + pw + 0.2, oy, color=MUTED, width=1.5)
    arrow(s, ox, oy, ox, oy - ph - 0.2, color=MUTED, width=1.5)
    text(s, ox + pw - 3.0, oy + 0.5, 3.2, 0.4, "Coût (M Ar) →", size=18, color=MUTED, align=PP_ALIGN.RIGHT)
    text(s, ox + 0.15, oy - ph - 0.3, 2.4, 0.4, "↑ Durée (jours)", size=18, color=MUTED)
    padx, pady = 0.6, 0.35  # marge entre les axes et les données, pour que rien ne touche un axe

    def pt(cost, days):
        return ox + padx + (pw - padx) * cost / 4_500_000, oy - pady - (ph - pady) * days / 22

    for v in (0, 1, 2, 3, 4):
        text(s, pt(v * 1e6, 0)[0] - 0.3, oy + 0.12, 0.6, 0.35, str(v), size=16, color=MUTED, align=PP_ALIGN.CENTER)
    for v in (0, 10, 20):
        text(s, ox - 0.65, pt(0, v)[1] - 0.18, 0.5, 0.35, str(v), size=16, color=MUTED, align=PP_ALIGN.RIGHT)

    people = [  # données réelles (préréglage Équilibré) : coût, jours, qualité, front
        ("Rado", 188_000, 2.0, 3.571, 1), ("Nirina", 528_000, 2.0, 4.005, 1),
        ("Toky", 1_584_000, 4.812, 4.825, 1), ("Rivo", 4_324_000, 21.029, 2.704, 5)]
    front = [pt(c, d) for _, c, d, _, f in people if f == 1]
    for (x1, y1), (x2, y2) in zip(front, front[1:]):
        arrow(s, x1, y1, x2, y2, color=BLUE, width=2.5, head=False)
    labels = {"Rado": (-1.45, -0.6), "Nirina": (0.05, -0.6), "Toky": (0.3, -0.62), "Rivo": (-1.0, -0.65)}
    for name, c, d, q, f in people:
        x, y = pt(c, d)
        r = 0.04 + 0.025 * q  # taille du point liée à la qualité (0,11 à 0,16 pouce)
        if name == "Toky":
            box(s, x - r * 1.5, y - r * 1.5, r * 3, r * 3, TERRA, shape=MSO_SHAPE.STAR_5_POINT, name="Meilleur compromis")
        else:
            box(s, x - r, y - r, 2 * r, 2 * r, BLUE if f == 1 else GRID, shape=MSO_SHAPE.OVAL)
        dx, dy = labels[name]
        text(s, x + dx, y + dy, 1.4, 0.4, name, size=18, bold=True, color=TERRA if name == "Toky" else TEXT,
             align=PP_ALIGN.RIGHT if name == "Rado" else PP_ALIGN.LEFT)
    lines = [
        [("Score", {"bold": True}), (" = Σ poids × critère normalisé", {})],
        [("Front 1", {"bold": True, "color": BLUE}), (" : personne ne fait mieux partout", {})],
        [("★ Toky", {"bold": True, "color": TERRA}), (" : le plus proche de l'idéal", {})],
        [("Rivo", {"bold": True}), (" : 4,3 M Ar, 21 j, note 2,7 → dominé", {})],
    ]
    text(s, 7.75, 1.7, 5.1, 3.6, lines, size=20, space_after=16)
    text(s, 7.75, 5.35, 5.1, 0.8, "Taille du point = qualité. Front calculé sur coût, rapidité, qualité.",
         size=18, color=MUTED, italic=True)


def s09_csp(s):
    background(s, LIGHT)
    title(s, "Planning : satisfaction de contraintes")
    badge(s, "n°3")
    text(s, 0.6, 1.4, 12.2, 0.5,
         [[("Variables", {"bold": True}), (" (freelance, début) — ", {}), ("Domaines", {"bold": True}),
           (" compétents × jours ouvrés", {})]], size=20)
    # Mini-Gantt réel : indices de jours ouvrés depuis le lundi 16 novembre 2026
    gx, gy, day, rh = 3.55, 2.35, 0.36, 0.62
    tasks = [("Maquettes (Nirina)", 0, 1, False), ("Base de données (Fanja)", 0, 1, True),
             ("API produits (Hasina)", 2, 4, True), ("Pages catalogue (Hasina)", 10, 13, True)]
    for d in range(0, 15, 5):
        text(s, gx + d * day - 0.3, gy - 0.48, 0.6, 0.35, f"j{d}", size=16, color=MUTED, align=PP_ALIGN.CENTER)
    pos = {}
    for k, (name, a, b, crit) in enumerate(tasks):
        y = gy + k * (rh + 0.2)
        text(s, 0.6, y + 0.1, 2.85, 0.45, name, size=18, color=TEXT, align=PP_ALIGN.RIGHT)
        x1, x2 = gx + a * day, gx + (b + 1) * day
        box(s, x1, y, x2 - x1, rh, TERRA if crit else BLUE, radius=0.2)
        pos[k] = (x1, x2, y + rh / 2)
    for a_, b_ in ((1, 2), (2, 3), (0, 3)):
        _, end, ya = pos[a_]
        start, _, yb = pos[b_]
        arrow(s, end + 0.03, ya, start - 0.03, yb, color=TEXT, width=1.5)
    leg = 2.35 + 4 * (rh + 0.2)
    box(s, 3.55, leg, 0.3, 0.3, TERRA, radius=0.2)
    text(s, 3.95, leg - 0.04, 4.5, 0.4, "chemin critique : borne de 11 jours", size=18, color=TEXT)
    text(s, 0.6, 6.15, 7.9, 0.5, [[("18 jours ouvrés", {"bold": True}),
                                   (" · optimum prouvé · 7/7 contraintes", {})]], size=22)
    diag = box(s, 8.85, 2.0, 3.95, 3.0, DARK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, radius=0.06, label=[
        [("Scénario 3 semaines", {"size": 22, "color": TERRA})],
        [("Hasina : 84 h à 6 h/jour = 16 jours pour 15 disponibles", {"size": 20, "bold": False})],
        [("→ repousser d'1 jour ou ajouter un renfort", {"size": 20})]])
    tf = diag.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = Inches(0.25)
    for p in tf.paragraphs:
        p.space_after = Pt(12)


def s10_tsp(s):
    background(s, LIGHT)
    title(s, "Tournée sur site : voyageur de commerce")
    badge(s, "n°30")
    # Villes placées d'après leurs coordonnées réelles (échelle 1,5 pouce par degré, cos(20°) en longitude)
    cities = {"Antananarivo": (-18.8792, 47.5079), "Toamasina": (-18.1443, 49.3958),
              "Antsirabe": (-19.8659, 47.0333), "Fianarantsoa": (-21.4527, 47.0857)}
    sc, lon0, lat0, mx, my = 1.3, 46.6, -17.95, 2.4, 1.65

    def xy(name):
        lat, lon = cities[name]
        return mx + (lon - lon0) * sc * 0.94, my + (lat0 - lat) * sc

    order = ["Fianarantsoa", "Toamasina", "Antananarivo", "Antsirabe"]
    legs_km = ["594 km", "291 km", "163 km", "238 km"]
    for k, a in enumerate(order):
        b = order[(k + 1) % 4]
        (x1, y1), (x2, y2) = xy(a), xy(b)
        arrow(s, x1 + (x2 - x1) * 0.12, y1 + (y2 - y1) * 0.12, x2 - (x2 - x1) * 0.12, y2 - (y2 - y1) * 0.12,
              color=TERRA, width=3)
        mxp, myp = (x1 + x2) / 2, (y1 + y2) / 2
        off = {0: (0.2, 0.0), 1: (-0.4, 0.15), 2: (-1.25, -0.25), 3: (-1.3, -0.2)}[k]
        text(s, mxp + off[0], myp + off[1], 1.1, 0.4, legs_km[k], size=18, color=MUTED, bold=True)
    # (décalage x, décalage y, alignement) de chaque nom de ville par rapport à son point
    name_off = {"Antananarivo": (-2.25, -0.2, PP_ALIGN.RIGHT), "Toamasina": (-0.2, 0.35, PP_ALIGN.LEFT),
                "Antsirabe": (-2.25, -0.2, PP_ALIGN.RIGHT), "Fianarantsoa": (0.35, -0.2, PP_ALIGN.LEFT)}
    for k, name in enumerate(order):
        x, y = xy(name)
        box(s, x - 0.27, y - 0.27, 0.54, 0.54, BLUE, str(k + 1), size=20, shape=MSO_SHAPE.OVAL)
        dx, dy, al = name_off[name]
        text(s, x + dx, y + dy, 1.9, 0.4, name, size=20, bold=True, color=TEXT, align=al)
    stats = [("1 286 km", "Held-Karp, tournée exacte"), ("1 542 777 Ar", "à 1 200 Ar/km, 32,1 h de route"),
             ("−18 %", "par rapport à l'ordre saisi")]
    for k, (big, small) in enumerate(stats):
        y = 1.65 + k * 1.25
        text(s, 7.6, y, 5.2, 0.65, big, size=36, bold=True, color=TERRA if k == 2 else BLUE)
        text(s, 7.6, y + 0.62, 5.2, 0.45, small, size=20, color=TEXT)
    box(s, 7.6, 5.55, 5.2, 0.85, DARK, "Puis le copilote explique, chiffres vérifiés", size=20)


def s11_archi(s):
    background(s, LIGHT)
    title(s, "Architecture")
    box(s, 0.6, 1.8, 3.4, 1.1, BLUE, [[("React + TypeScript", {"size": 22})], [("Vite, Tailwind", {"size": 18, "bold": False})]])
    box(s, 4.95, 1.8, 3.4, 1.1, BLUE, [[("API FastAPI", {"size": 22})], [("asynchrone, /api/v1", {"size": 18, "bold": False})]])
    box(s, 9.3, 1.8, 3.4, 1.1, BLUE, [[("Services", {"size": 22})], [("base ↔ algorithmes ↔ IA", {"size": 18, "bold": False})]])
    arrow(s, 4.05, 2.35, 4.9, 2.35)
    arrow(s, 8.4, 2.35, 9.25, 2.35)
    box(s, 9.3, 4.0, 3.4, 1.1, TERRA, [[("Algorithmes purs", {"size": 22})], [("n°29, 22, 21, 3, 30, 33", {"size": 18, "bold": False})]])
    box(s, 4.95, 4.0, 3.4, 1.1, DARK, [[("Copilote LLM", {"size": 22})], [("simulé · Claude · Gemini", {"size": 18, "bold": False})]])
    box(s, 0.6, 4.0, 3.4, 1.1, DARK, [[("PostgreSQL 17", {"size": 22})], [("SQLAlchemy async, Alembic", {"size": 18, "bold": False})]])
    arrow(s, 11.0, 2.95, 11.0, 3.95)
    arrow(s, 9.85, 2.95, 7.4, 3.95)
    arrow(s, 9.4, 2.85, 2.9, 3.95)
    text(s, 0.6, 5.7, 12.2, 1.0,
         ["Algorithmes sans web, sans base, sans IA : testés seuls (pytest).",
          "Authentification JWT + argon2 ; suivi du coût de chaque appel à l'IA."], size=20, color=TEXT)


def s12_demo(s):
    background(s, LIGHT)
    title(s, "Démonstration (4 minutes)")
    marks = [("0:00", "Connexion"), ("0:30", "Copilote, brouillon"), ("1:15", "Périmètre, et si ?"),
             ("2:00", "Équipe, Pareto"), ("2:45", "Planning, impossible"), ("3:30", "Tournée, synthèse")]
    x0, step, y = 1.1, 2.2, 2.9
    arrow(s, 0.6, y, 12.8, y, color=GRID, width=3, head=False)
    for k, (t, label) in enumerate(marks):
        x = x0 + k * step
        box(s, x - 0.42, y - 0.42, 0.84, 0.84, TERRA if k == 4 else BLUE, str(k + 1), size=22, shape=MSO_SHAPE.OVAL)
        text(s, x - 0.9, y - 1.15, 1.8, 0.45, t, size=20, bold=True, color=MUTED, align=PP_ALIGN.CENTER)
        text(s, x - 1.0, y + 0.6, 2.0, 1.0, label, size=20, color=TEXT, align=PP_ALIGN.CENTER)
    box(s, 0.6, 5.1, 12.2, 0.95, BLUE_TINT, "Sans réseau ni clé : fournisseur simulé, carte hors ligne en secours",
        size=20, color=TEXT, bold=False)


def s13_results(s):
    background(s, LIGHT)
    title(s, "Résultats mesurés")
    cards = [("124 tests", "passent, en 20 s ; parcours API 45/45", BLUE),
             ("= force brute", "sac à dos, 200 instances ; ≤ 10 ms à 40", BLUE),
             ("0,38 s", "planning optimal prouvé ; 1re en 1,7 ms", TERRA),
             ("14 ms", "tournée exacte de 12 villes ; voisin seul +18 %", TERRA)]
    for k, (big, small, col) in enumerate(cards):
        x, y = 0.6 + (k % 2) * 6.2, 1.65 + (k // 2) * 2.35
        card = box(s, x, y, 5.95, 2.05, WHITE, line=GRID, radius=0.08)
        text(s, x + 0.35, y + 0.25, 5.3, 0.8, big, size=40, bold=True, color=col)
        text(s, x + 0.35, y + 1.15, 5.3, 0.75, small, size=20, color=TEXT)
    text(s, 0.6, 6.45, 12.2, 0.45, "Mesures recalculées en direct sur la page « Comparaison des méthodes ».",
         size=18, color=MUTED, italic=True)


def s14_limits(s):
    background(s, LIGHT)
    title(s, "Limites et perspectives")
    text(s, 0.6, 1.55, 6.0, 0.5, "Limites assumées", size=24, bold=True, color=TERRA)
    text(s, 6.95, 1.55, 6.0, 0.5, "Niveau B", size=24, bold=True, color=BLUE)
    left = ["Tournée hors sac à dos : total 6,76 M Ar", "Distances estimées, jours fériés ignorés",
            "Claude : pas de test avec vraie clé"]
    right = ["Min-Conflict (n°11) après un retard", "Sur site relié à la tournée, espace freelance"]
    for k, item in enumerate(left):
        box(s, 0.6, 2.25 + k * 1.15, 5.9, 0.9, TERRA_TINT, item, size=20, color=TEXT, bold=False, align=PP_ALIGN.LEFT)
    for k, item in enumerate(right):
        box(s, 6.95, 2.25 + k * 1.15, 5.85, 0.9, BLUE_TINT, item, size=20, color=TEXT, bold=False, align=PP_ALIGN.LEFT)


def s15_conclusion(s):
    background(s, DARK)
    title(s, "Conclusion", dark=True)
    items = [("Une IA", " pour comprendre et expliquer"), ("Des algorithmes prouvés", " pour décider"),
             ("Des résultats vérifiés", ", expliqués et chiffrés")]
    for k, (a, b) in enumerate(items):
        y = 1.8 + k * 1.05
        box(s, 0.9, y + 0.12, 0.5, 0.32, TERRA if k == 1 else BLUE, radius=0.25)
        text(s, 1.65, y, 11, 0.6, [[(a, {"bold": True, "color": WHITE}), (b, {"color": SOFT_ON_DARK})]], size=28)
    text(s, 0.9, 5.3, 11, 0.8, "Merci — vos questions ?", size=36, bold=True, color=TERRA)


SLIDES = [
    (s01_cover, True), (s02_vision, True), (s03_probleme, False), (s04_questions, False), (s05_flow, False),
    (s06_copilot, False), (s07_knapsack, False), (s08_matching, False), (s09_csp, False), (s10_tsp, False),
    (s11_archi, False), (s12_demo, False), (s13_results, False), (s14_limits, False), (s15_conclusion, True),
]


def main() -> None:
    scripts = load_scripts()
    if len(scripts) != len(SLIDES):
        raise SystemExit(f"{len(scripts)} scripts trouvés dans 07_PRESENTATION.md pour {len(SLIDES)} diapositives.")
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    prs.core_properties.title = "SmartBricks — soutenance"
    blank = prs.slide_layouts[6]
    for n, (draw, dark) in enumerate(SLIDES, start=1):
        slide = prs.slides.add_slide(blank)
        draw(slide)
        slide_number(slide, n, dark)
        slide.notes_slide.notes_text_frame.text = scripts[n]
    prs.save(OUT)
    print(f"{OUT.name} : {len(SLIDES)} diapositives, notes de l'orateur incluses.")


if __name__ == "__main__":
    main()
