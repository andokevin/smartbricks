"""Génère docs/SmartBricks_presentation.pptx (16:9, 22 diapositives) avec python-pptx.

Lancement, depuis la racine du projet (python-pptx n'est pas une dépendance de l'API) :
    uv pip install --python backend/.venv/bin/python python-pptx
    backend/.venv/bin/python docs/build_slides.py

- Une diapositive par section « ## Diapositive N » de docs/07_PRESENTATION.md (le script de référence) ;
  les notes de l'orateur ne contiennent que 2 ou 3 mots-clés de secours (liste SLIDES).
- Animations écrites directement en XML (python-pptx ne les gère pas) : transition « Fondu » entre les
  diapositives (add_transition) et apparition en fondu au clic, dans l'ordre de lecture
  (click_groups + add_click_animations, qui ciblent les formes par leur identifiant réel spid).
- Aucun numéro d'algorithme n'est affiché ; le voyageur de commerce n'est plus présenté.
- Les schémas sont des formes natives PowerPoint (rectangles arrondis, flèches, connecteurs),
  modifiables dans PowerPoint ; aucune image.
- Tous les chiffres sont ceux mesurés sur le projet de démonstration (API) et dans
  docs/benchmark_resultats.json et pytest (voir l'en-tête de 07_PRESENTATION.md).

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
from pptx.util import Inches, Pt

DOCS = Path(__file__).resolve().parent
OUT = DOCS / "SmartBricks_presentation.pptx"
SCRIPT_MD = DOCS / "07_PRESENTATION.md"

# À compléter par l'auteur : affichés sur la couverture (une valeur vide n'est pas affichée).
AUTHOR = "Ando Kevin"
FORMATION = ""
DATE = "Novembre 2026"

# --------------------------------------------------------------------------- charte
BLUE = RGBColor(0x1E, 0x5A, 0xA8)
TERRA = RGBColor(0xC8, 0x61, 0x2D)
LIGHT = RGBColor(0xF6, 0xF4, 0xEF)
DARK = RGBColor(0x16, 0x21, 0x3A)
DARK_CARD = RGBColor(0x24, 0x31, 0x52)
TEXT = RGBColor(0x1B, 0x23, 0x33)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x5B, 0x64, 0x75)
GRID = RGBColor(0xC9, 0xC4, 0xB8)
BLUE_TINT = RGBColor(0xDC, 0xE7, 0xF5)
TERRA_TINT = RGBColor(0xF6, 0xE0, 0xD3)
SOFT_ON_DARK = RGBColor(0xC9, 0xD3, 0xE6)
FONT = "Calibri"

W, H = 13.333, 7.5  # pouces, 16:9

PART1 = "PARTIE 1 — LE PROJET ET LA PROBLÉMATIQUE"
PART2 = "PARTIE 2 — LES ALGORITHMES"
PART3 = "PARTIE 3 — LE SYSTÈME"
PART4 = "PARTIE 4 — DÉMONSTRATION ET BILAN"


# --------------------------------------------------------------------------- notes depuis le Markdown


def load_scripts() -> dict[int, str]:
    """{numéro de diapositive: script oral}, lu dans 07_PRESENTATION.md."""
    text = SCRIPT_MD.read_text(encoding="utf-8")
    scripts: dict[int, str] = {}
    for m in re.finditer(r"^## Diapositive (\d+)[^\n]*\n(.*?)(?=^---|^## |^# )", text, re.S | re.M):
        num, body = int(m.group(1)), m.group(2)
        part = body.split("**Script", 1)[1] if "**Script" in body else ""
        lines = []
        for line in part.splitlines()[1:]:
            line = line.strip()
            if line.startswith(">"):
                lines.append(line.lstrip("> ").replace("**", ""))
            elif line.startswith("*Plan B"):
                lines.append(line.strip("*").replace("`", ""))
        scripts[num] = "\n".join(lines).strip()
    return scripts


# --------------------------------------------------------------------------- typographie

NBSP = " "
_UNITS = r"(?:ms|s|h|j|jours?|km|Ar|%|M|nœuds|tests|villes|instances|semaines|agences|millions|\$)"


def nb(s: str) -> str:
    """Typographie française : espaces insécables dans « … », entre milliers et avant une unité."""
    s = s.replace("« ", "«" + NBSP).replace(" »", NBSP + "»")
    s = re.sub(r"(\d) (?=\d{3}\b)", r"\1" + NBSP, s)
    s = re.sub(r"(\d) (?=" + _UNITS + r"(?!\w))", r"\1" + NBSP, s)
    s = s.replace("M Ar", "M" + NBSP + "Ar").replace(" 1er", NBSP + "1er")
    # Traits d'union insécables : « Held-Karp » et « 2-opt » ne doivent jamais être coupés.
    s = s.replace("Held-Karp", "Held‑Karp").replace("2-opt", "2‑opt")
    return s


# --------------------------------------------------------------------------- briques de dessin


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
        line=None, radius=0.18, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, name=None, pad=0.08):
    """Forme pleine avec texte (rectangle arrondi par défaut)."""
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
    tf.margin_left = tf.margin_right = Inches(pad)
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


def arrow(slide, x1, y1, x2, y2, color=MUTED, width=2.25, head=True):
    """Connecteur droit, avec pointe de flèche à l'arrivée."""
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    if head:
        ln = c.line._get_or_add_ln()
        ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    return c


def background(slide, color: RGBColor) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def title(slide, label: str, dark: bool = False, width: float = 10.4, part: str | None = None) -> None:
    if part:
        text(slide, 0.6, 0.2, 10.4, 0.3, part, size=12, bold=True, color=SOFT_ON_DARK if dark else TERRA,
             name="Partie")
    text(slide, 0.6, 0.48, width, 0.85, label, size=34, bold=True, color=WHITE if dark else TEXT,
         anchor=MSO_ANCHOR.MIDDLE, name="Titre")


def badge(slide, label: str) -> None:
    """Ancienne pastille « numéro du cours » : plus affichée (aucun numéro d'algorithme sur les diapositives)."""
    return None


# --------------------------------------------------------------------------- animations (XML direct)
# python-pptx ne gère pas les animations : on écrit nous-mêmes <p:transition> et <p:timing>.

STATIC_NAMES = {"Titre", "Partie", "Numéro de diapositive"}


def _is_connector(shape) -> bool:
    return shape.element.tag == qn("p:cxnSp")


def click_groups(slide) -> list[list]:
    """Regroupe les formes en « clics », dans l'ordre de création (= ordre de lecture) :
    - le titre, la mention de partie et le numéro restent visibles dès l'arrivée ;
    - une flèche apparaît avec la forme qui la suit (l'étape qu'elle relie à la précédente) ;
    - des formes consécutives alignées sur la même ligne (cellules d'un tableau) forment un seul clic."""
    groups: list[list] = []
    pending: list = []
    last_top = None
    tol = Inches(0.05)

    def inside(a, b) -> bool:  # les rectangles de a et b se recouvrent (carte et son texte)
        return (a.left < b.left + b.width - tol and b.left < a.left + a.width - tol
                and a.top < b.top + b.height - tol and b.top < a.top + a.height - tol)

    for shp in slide.shapes:
        if shp.name in STATIC_NAMES:
            continue
        if _is_connector(shp):
            pending.append(shp)
            continue
        current = [g for g in (groups[-1] if groups else []) if not _is_connector(g)]
        same_row = last_top is not None and abs(shp.top - last_top) < tol
        same_tag = shp.name.startswith("g:") and current and current[-1].name == shp.name
        overlaps = any(inside(shp, g) for g in current)
        if groups and not pending and (same_row or same_tag or overlaps):
            groups[-1].append(shp)
        else:
            groups.append(pending + [shp])
        pending = []
        last_top = shp.top
    if pending:
        groups.append(pending)
    return groups


def add_transition(slide) -> None:
    """Transition « Fondu » à l'arrivée de la diapositive."""
    sld = slide.element
    tr = sld.makeelement(qn("p:transition"), {"spd": "med"})
    tr.append(tr.makeelement(qn("p:fade"), {}))
    clr = sld.find(qn("p:clrMapOvr"))
    (clr if clr is not None else sld.find(qn("p:cSld"))).addnext(tr)


def add_click_animations(slide, groups: list[list], effect: str = "fade") -> int:
    """Effet d'entrée « Fondu » au clic : un clic par groupe, les formes d'un groupe apparaissent ensemble.

    Écrit l'arbre <p:timing> attendu par PowerPoint (séquence principale, un <p:par> par clic) ;
    chaque cible est désignée par l'identifiant réel de la forme (spid). Renvoie le nombre de clics."""
    if not groups:
        return 0
    ids = iter(range(3, 100_000))
    clicks = []
    for group in groups:
        effects = []
        for k, shp in enumerate(group):
            spid = shp.shape_id
            node = "clickEffect" if k == 0 else "withEffect"
            effects.append(
                f'<p:par><p:cTn id="{next(ids)}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" '
                f'grpId="0" nodeType="{node}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                f'<p:set><p:cBhvr><p:cTn id="{next(ids)}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/>'
                f'</p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst>'
                f'<p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/>'
                f'</p:to></p:set><p:animEffect transition="in" filter="{effect}"><p:cBhvr><p:cTn id="{next(ids)}" '
                f'dur="500"/><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>'
                f'</p:childTnLst></p:cTn></p:par>'
            )
        clicks.append(
            f'<p:par><p:cTn id="{next(ids)}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>'
            f'<p:childTnLst><p:par><p:cTn id="{next(ids)}" fill="hold"><p:stCondLst><p:cond delay="0"/>'
            f'</p:stCondLst><p:childTnLst>{"".join(effects)}</p:childTnLst></p:cTn></p:par></p:childTnLst>'
            f'</p:cTn></p:par>'
        )
    builds = "".join(f'<p:bldP spid="{shp.shape_id}" grpId="0" animBg="1"/>'
                     for group in groups for shp in group if not _is_connector(shp))
    xml = (
        '<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
        '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        + "".join(clicks) +
        '</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl>'
        '</p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl>'
        '</p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>'
        f'<p:bldLst>{builds}</p:bldLst></p:timing>'
    )
    from lxml import etree

    timing = etree.fromstring(xml)
    sld = slide.element
    anchor = sld.find(qn("p:transition"))
    if anchor is None:
        anchor = sld.find(qn("p:clrMapOvr"))
    anchor.addnext(timing)
    return len(groups)


def slide_number(slide, n: int, dark: bool = False) -> None:
    text(slide, 12.2, 6.95, 0.75, 0.35, str(n), size=14, color=SOFT_ON_DARK if dark else MUTED,
         align=PP_ALIGN.RIGHT, name="Numéro de diapositive")


def bricks(slide, x, y, colors, size=0.42, gap=0.1) -> None:
    """Motif visuel : une rangée de briques (le « Bricks » de SmartBricks)."""
    for k, c in enumerate(colors):
        box(slide, x + k * (size + gap), y, size, size * 0.62, c, radius=0.25)


def table_rows(slide, x, y, widths, rows, row_h=0.6, gap=0.07, size=16, first_fill=None) -> None:
    """Tableau en formes natives : ligne d'en-tête bleue, puis lignes blanches."""
    for r, row in enumerate(rows):
        cx = x
        for c, (cell, w) in enumerate(zip(row, widths)):
            head = r == 0
            if head:
                fill, color, bold = BLUE, WHITE, True
            elif c == 0 and first_fill is not None:
                fill, color, bold = first_fill, WHITE, True
            else:
                fill, color, bold = WHITE, TEXT, False
            box(slide, cx, y + r * (row_h + gap), w - 0.06, row_h, fill, cell, size=size, color=color, bold=bold,
                line=None if (head or fill != WHITE) else GRID, radius=0.12,
                align=PP_ALIGN.CENTER if (c == 0 and first_fill is not None) else PP_ALIGN.LEFT, pad=0.12)
            cx += w


def why_how(s, why: str, steps: list[tuple[str, str]], footer: str) -> None:
    """Diapositive « Pourquoi et comment » : la raison, 4 étapes reliées par des flèches, une phrase de conclusion."""
    why_box = box(s, 0.6, 1.5, 12.13, 1.0, BLUE_TINT, align=PP_ALIGN.LEFT, pad=0.25, label=[
        [("Pourquoi ? ", {"bold": True, "color": BLUE}), (why, {"bold": False, "color": TEXT})]], size=20)
    why_box.name = "Pourquoi"
    text(s, 0.6, 2.75, 6, 0.4, "Comment ?", size=20, bold=True, color=TERRA)
    bw, gap = 2.78, 0.33
    for k, (head, detail) in enumerate(steps):
        x = 0.6 + k * (bw + gap)
        box(s, x, 3.25, bw, 1.85, BLUE if k % 2 == 0 else DARK, anchor=MSO_ANCHOR.TOP, pad=0.15, label=[
            [(f"{k + 1}  ", {"size": 22, "color": RGBColor(0xF0, 0xB4, 0x95)}), (head, {"size": 22})],
            [(detail, {"size": 17, "bold": False})]], align=PP_ALIGN.LEFT)
        if k < len(steps) - 1:
            arrow(s, x + bw + 0.03, 4.17, x + bw + gap - 0.03, 4.17, color=MUTED, width=2.5)
    box(s, 0.6, 5.45, 12.13, 0.85, TERRA_TINT, footer, size=19, color=TEXT, bold=False, align=PP_ALIGN.LEFT, pad=0.25)


# --------------------------------------------------------------------------- partie 1


def s01_cover(s):
    background(s, DARK)
    bricks(s, 0.9, 1.35, [BLUE, TERRA, BLUE, BLUE, TERRA, BLUE], size=0.55)
    text(s, 0.9, 1.95, 11, 1.3, "SmartBricks", size=60, bold=True, color=WHITE)
    text(s, 0.9, 3.25, 11, 0.7, "Du besoin flou au projet informatique réaliste", size=30, color=WHITE)
    text(s, 0.9, 4.05, 11, 0.6, "Copilote IA + algorithmes d'optimisation", size=24, color=TERRA, bold=True)
    credit = " — ".join(v for v in (AUTHOR, FORMATION, DATE) if v)
    text(s, 0.9, 5.7, 11, 0.5, credit, size=20, color=SOFT_ON_DARK)


def s02_why(s):
    background(s, DARK)
    title(s, "Pourquoi ce projet", dark=True, part=PART1)
    text(s, 0.9, 1.65, 11.6, 1.3,
         [[("« Oser rêver, réaliser son imagination ", {}), ("pour améliorer le quotidien. »", {"color": TERRA})]],
         size=32, bold=True, color=WHITE)
    cards = [("Commerçants et PME", "des idées, pas d'équipe technique"),
             ("Freelances", "des compétences dispersées, des missions incertaines"),
             ("Agences en région", "Tana, Antsirabe, Toamasina, Fianarantsoa")]
    for k, (head, detail) in enumerate(cards):
        x = 0.9 + k * 3.95
        box(s, x, 3.55, 3.7, 2.1, DARK_CARD, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT, pad=0.22, label=[
            [(head, {"size": 22, "color": WHITE})], [(detail, {"size": 19, "bold": False, "color": SOFT_ON_DARK})]])
    bricks(s, 0.9, 6.25, [BLUE, TERRA, BLUE, TERRA, BLUE, TERRA], size=0.4)


def s03_project(s):
    background(s, LIGHT)
    title(s, "Présentation du projet", part=PART1)
    text(s, 0.6, 1.5, 12.1, 1.0,
         "SmartBricks transforme une idée en projet réalisable : un périmètre chiffré, une équipe et un planning garanti.",
         size=24, bold=True, color=TEXT)
    actors = [("Le client", "décrit son besoin et décide", WHITE, TEXT),
              ("Le copilote IA", "comprend et explique", TERRA, WHITE),
              ("Les algorithmes", "calculent et garantissent", BLUE, WHITE)]
    for k, (head, role, fill, color) in enumerate(actors):
        x = 0.6 + k * 4.2
        box(s, x, 3.0, 3.55, 2.3, fill, line=GRID if fill == WHITE else None, color=color, label=[
            [(head, {"size": 26})], [(role, {"size": 20, "bold": False})]])
        if k < 2:
            arrow(s, x + 3.6, 4.15, x + 4.15, 4.15, color=MUTED, width=2.5)
    text(s, 0.6, 5.75, 12.1, 0.5, "L'IA ne calcule jamais un budget ni un planning : ce sont les algorithmes qui décident.",
         size=20, color=MUTED, italic=True)


def s04_problem(s):
    background(s, LIGHT)
    title(s, "La problématique", part=PART1)
    q = box(s, 0.9, 1.75, 11.5, 3.9, BLUE, anchor=MSO_ANCHOR.MIDDLE, pad=0.6, radius=0.06, label=[[(
        "« Comment transformer l'idée d'un client non technique en projet réalisable, en garantissant le respect "
        "de son budget, de ses délais et des contraintes de l'équipe ? »", {"size": 32})]])
    q.name = "Question centrale"
    text(s, 0.9, 6.0, 11.5, 0.5, "Garantir, et pas seulement estimer : chaque résultat est prouvé ou vérifié.",
         size=20, color=MUTED, italic=True, align=PP_ALIGN.CENTER)


def s05_difficulties(s):
    background(s, LIGHT)
    title(s, "Les difficultés concrètes", part=PART1)
    text(s, 0.6, 1.55, 6.0, 0.5, "Côté client", size=24, bold=True, color=TERRA)
    text(s, 6.95, 1.55, 6.0, 0.5, "Côté freelance", size=24, bold=True, color=BLUE)
    left = ["Ne sait pas découper ni chiffrer son idée", "Budget limité, délai fixé",
            "Ne sait pas qui recruter"]
    right = ["Disponibilités et compétences ignorées", "Planning irréaliste, retards mal absorbés"]
    for k, item in enumerate(left):
        box(s, 0.6, 2.25 + k * 1.15, 5.95, 0.9, TERRA_TINT, item, size=20, color=TEXT, bold=False,
            align=PP_ALIGN.LEFT, pad=0.25)
    for k, item in enumerate(right):
        box(s, 6.95, 2.25 + k * 1.15, 5.8, 0.9, BLUE_TINT, item, size=20, color=TEXT, bold=False,
            align=PP_ALIGN.LEFT, pad=0.25)
    text(s, 6.95, 4.75, 5.8, 1.2, [[("Boutique Soa : ", {"bold": True}),
                                    ("14 fonctionnalités rêvées = 15,2 M Ar, pour 6 M Ar de budget.", {})]],
         size=20, color=TEXT)


# --------------------------------------------------------------------------- partie 2


def s06_overview(s):
    background(s, LIGHT)
    title(s, "Les algorithmes utilisés", part=PART2)
    rows = [("Algorithme", "À quoi il sert", "Fonctionnalité"),
            ("Satisfaction de contraintes (CSP)", "Décider qui fait chaque tâche, et quand", "Planning"),
            ("Min-Conflict", "Réparer le planning après un retard", "Planning"),
            ("Optimisation de Pareto", "Montrer les meilleurs compromis", "Équipe"),
            ("Agrégation pondérée", "Classer selon les priorités du client", "Équipe"),
            ("Sac à dos multidimensionnel", "Choisir quoi livrer sous budget et heures", "Périmètre"),
            ("Copilote LLM + sélecteur", "Comprendre, choisir la méthode, expliquer", "Copilote, synthèse")]
    table_rows(s, 0.6, 1.5, (4.4, 5.25, 2.5), rows, row_h=0.66, gap=0.08, size=18, first_fill=TERRA)


def s07_flow(s):
    background(s, LIGHT)
    title(s, "L'enchaînement", part=PART2)
    steps = [("Copilote", "LLM"), ("Périmètre", "sac à dos"), ("Équipe", "pondération, Pareto"),
             ("Planning", "CSP"), ("Explication", "LLM vérifié")]
    bw, gap, y = 2.1, 0.41, 2.6
    for k, (name, num) in enumerate(steps):
        x = 0.6 + k * (bw + gap)
        fill = TERRA if k in (0, 4) else BLUE
        box(s, x, y, bw, 1.5, fill, [[(name, {"size": 22})], [(num, {"size": 20, "bold": False})]])
        text(s, x, y - 0.6, bw, 0.45, str(k + 1), size=24, bold=True, color=fill, align=PP_ALIGN.CENTER)
        if k < len(steps) - 1:
            arrow(s, x + bw + 0.02, y + 0.75, x + bw + gap - 0.02, y + 0.75, color=MUTED, width=2.5)
    box(s, 0.6, 4.7, 4.0, 0.6, TERRA_TINT, "IA : comprendre, expliquer", size=20, color=TEXT, bold=False)
    box(s, 4.85, 4.7, 4.6, 0.6, BLUE_TINT, "Algorithmes : décider, prouver", size=20, color=TEXT, bold=False)
    text(s, 0.6, 5.7, 12, 0.6, "Chaque étape consomme le résultat de la précédente.", size=22, bold=True, color=TEXT)


def s08_copilot_how(s):
    background(s, LIGHT)
    title(s, "Copilote et sélecteur : pourquoi, comment", part=PART2, width=10.3)
    badge(s, "n°33")
    why_how(s, "Seul un modèle de langage comprend le français courant ; mais il calcule mal, donc il ne décide rien.",
            [("Dialogue", "une question à la fois"), ("Extraction", "JSON au schéma imposé"),
             ("Contrôles", "compétences, villes, cycles (Kahn), sans IA"), ("Explication", "chaque chiffre vérifié")],
            "Sélecteur de méthode : exact si la taille le permet, sinon approché — et il dit pourquoi.")


def s09_copilot_app(s):
    background(s, LIGHT)
    title(s, "Copilote et sélecteur : dans SmartBricks", part=PART2, width=10.3)
    badge(s, "n°33")
    box(s, 0.6, 1.55, 6.2, 1.55, WHITE, line=GRID, radius=0.06, align=PP_ALIGN.LEFT, pad=0.25, label=[
        [("Reçoit : ", {"bold": True, "color": BLUE, "size": 18}),
         ("« Boutique Soa veut un site e-commerce… 6 000 000 Ar, 8 semaines. »", {"bold": False, "color": TEXT, "size": 18})]])
    arrow(s, 3.7, 3.15, 3.7, 3.55, color=MUTED)
    box(s, 0.6, 3.6, 6.2, 1.15, BLUE, align=PP_ALIGN.LEFT, pad=0.25, label=[
        [("Brouillon : ", {"size": 20}), ("14 fonctionnalités · 30 tâches (mode simulé)", {"size": 20, "bold": False})]])
    box(s, 0.6, 5.0, 6.2, 1.15, TERRA_TINT, align=PP_ALIGN.LEFT, pad=0.25, color=TEXT, label=[
        [("Avec Claude (essai réel) : ", {"size": 18}),
         ("2 échanges, 8 fonctionnalités, 18 tâches, ≈ 0,002 $", {"size": 18, "bold": False})]])
    text(s, 7.3, 1.55, 5.5, 0.5, "Sélecteur de méthode", size=22, bold=True, color=TEXT)
    rules = [("Sac à dos ≤ 40", "exact"), ("Planning", "3 s max"), ("Après un retard", "réparer")]
    for k, (cond, meth) in enumerate(rules):
        y = 2.2 + k * 0.95
        box(s, 7.3, y, 3.2, 0.72, WHITE, cond, size=19, color=TEXT, bold=False, line=GRID)
        arrow(s, 10.55, y + 0.36, 10.95, y + 0.36, color=MUTED)
        box(s, 11.0, y, 1.75, 0.72, BLUE, meth, size=19)
    text(s, 7.3, 5.15, 5.45, 1.0, "Boutique Soa : 14 fonctionnalités → méthode exacte choisie.",
         size=18, color=MUTED, italic=True)


def s10_knapsack_how(s):
    background(s, LIGHT)
    title(s, "Sac à dos multidimensionnel : pourquoi, comment", part=PART2, width=10.3)
    badge(s, "n°29")
    why_how(s, "Choisir des fonctionnalités sous deux limites (Ariary et heures), avec obligatoires et dépendances.",
            [("Trier", "par densité : valeur / ressources"), ("Brancher", "inclure ou exclure, avec les dépendances"),
             ("Borner", "minimum des deux sacs fractionnaires"), ("Élaguer", "si la borne ne bat pas le meilleur")],
            "Plutôt que la programmation dynamique : 6 000 000 Ar × 200 h, plus de 10 milliards de cases.")


def s11_knapsack_app(s):
    background(s, LIGHT)
    title(s, "Sac à dos : dans SmartBricks", part=PART2)
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


def s12_matching_how(s):
    background(s, LIGHT)
    title(s, "Score pondéré et Pareto : pourquoi, comment", part=PART2, width=10.3)
    badge(s, "n°22 · 21")
    why_how(s, "Le moins cher n'est ni le plus rapide ni le mieux noté : il faut arbitrer entre critères.",
            [("Mesurer", "5 critères : coût, rapidité, qualité, disponibilité, couverture"),
             ("Normaliser", "chaque critère entre 0 et 1"),
             ("Pondérer", "score = Σ poids × critère"),
             ("Comparer", "fronts de Pareto, sans poids")],
            "Le score suit les priorités du client ; Pareto montre tous les bons compromis.")


def s13_matching_app(s):
    background(s, LIGHT)
    title(s, "Matching : dans SmartBricks", part=PART2)
    badge(s, "n°22 · 21")
    # Repère : x = coût (0 à 4,5 M Ar), y = durée (0 à 22 jours ouvrés)
    ox, oy, pw, ph = 1.35, 5.75, 5.9, 3.9
    arrow(s, ox, oy, ox + pw + 0.2, oy, color=MUTED, width=1.5)
    arrow(s, ox, oy, ox, oy - ph - 0.2, color=MUTED, width=1.5)
    text(s, ox + pw - 3.0, oy + 0.5, 3.2, 0.4, "Coût (M Ar) →", size=18, color=MUTED, align=PP_ALIGN.RIGHT)
    text(s, ox + 0.15, oy - ph - 0.3, 2.4, 0.4, "↑ Durée (jours)", size=18, color=MUTED)
    padx, pady = 0.6, 0.35

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
        r = 0.04 + 0.025 * q  # taille du point liée à la qualité
        if name == "Toky":
            box(s, x - r * 1.5, y - r * 1.5, r * 3, r * 3, TERRA, shape=MSO_SHAPE.STAR_5_POINT, name="Meilleur compromis")
        else:
            box(s, x - r, y - r, 2 * r, 2 * r, BLUE if f == 1 else GRID, shape=MSO_SHAPE.OVAL)
        dx, dy = labels[name]
        text(s, x + dx, y + dy, 1.4, 0.4, name, size=18, bold=True, color=TERRA if name == "Toky" else TEXT,
             align=PP_ALIGN.RIGHT if name == "Rado" else PP_ALIGN.LEFT)
    lines = [
        [("23 candidats", {"bold": True}), (", dont 9 sur le front 1", {})],
        [("Économique", {"bold": True}), (" → Rado 1er ; ", {}), ("Rapide", {"bold": True}), (" → Nirina 1er", {})],
        [("★ Toky", {"bold": True, "color": TERRA}), (" : le plus proche de l'idéal", {})],
        [("Rivo", {"bold": True}), (" : 4,3 M Ar, 21 j, note 2,7 → dominé (front 5)", {})],
    ]
    text(s, 7.75, 1.7, 5.1, 3.6, lines, size=20, space_after=16)
    text(s, 7.75, 5.35, 5.1, 0.8, "Taille du point = qualité. Front calculé sur coût, rapidité, qualité.",
         size=18, color=MUTED, italic=True)


def s14_csp_how(s):
    background(s, LIGHT)
    title(s, "Satisfaction de contraintes : pourquoi, comment", part=PART2, width=10.3)
    badge(s, "n°3")
    why_how(s, "Un planning, ce sont des règles qui doivent toutes être vraies : dépendances, compétences, congés, "
               "une tâche à la fois, date limite.",
            [("Propager", "chemin critique : borne et impossibilités"), ("Choisir", "la tâche la plus contrainte (MRV)"),
             ("Anticiper", "vérifier les tâches suivantes"), ("Améliorer", "chercher plus court, 3 s au plus")],
            "Puis une vérification indépendante du solveur revérifie tout le planning (8 contrôles).")


def s15_csp_app(s):
    background(s, LIGHT)
    title(s, "Planning : dans SmartBricks", part=PART2)
    badge(s, "n°3 · 11")
    text(s, 0.6, 1.4, 8.0, 0.5, [[("12 tâches", {"bold": True}), (" · 4 freelances · ", {}),
                                  ("8/8 contraintes", {"bold": True}), (" vérifiées", {})]], size=20)
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
                                   (" · fin le 9 décembre · optimum prouvé", {})]], size=22)
    diag = box(s, 8.85, 1.95, 3.95, 2.75, DARK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, radius=0.06, label=[
        [("Scénario 3 semaines", {"size": 21, "color": TERRA})],
        [("Hasina : 84 h à 6 h/jour = 16 jours pour 15", {"size": 19, "bold": False})],
        [("→ impossible, sans aucune recherche", {"size": 19})]])
    tf = diag.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = Inches(0.22)
    for p in tf.paragraphs:
        p.space_after = Pt(10)
    mc = box(s, 8.85, 4.9, 3.95, 1.35, TERRA_TINT, align=PP_ALIGN.LEFT, color=TEXT, anchor=MSO_ANCHOR.MIDDLE, label=[
        [("Retard de 8 h sur T2", {"size": 19})],
        [("Min-Conflict : 2 tâches déplacées", {"size": 18, "bold": False})]])
    mc.text_frame.margin_left = Inches(0.22)


def s16_tsp_how(s):
    background(s, LIGHT)
    title(s, "Voyageur de commerce : pourquoi, comment", part=PART2, width=10.3)
    badge(s, "n°30")
    why_how(s, "Visiter les agences une fois chacune, en parcourant le moins de kilomètres.",
            [("Mesurer", "haversine × 1,35 (facteur routier)"),
             ("Mémoriser", "le meilleur chemin par (villes visitées, dernière ville)"),
             ("Reconstruire", "l'ordre optimal (Held-Karp)"), ("Au-delà de 12", "plus proche voisin + 2-opt")],
            "12 sites : 39 916 800 ordres possibles ; Held-Karp ≈ 590 000 opérations.")


def s17_tsp_app(s):
    background(s, LIGHT)
    title(s, "Tournée : dans SmartBricks", part=PART2)
    badge(s, "n°30")
    # Villes placées d'après leurs coordonnées réelles (cos(20°) en longitude)
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
    name_off = {"Antananarivo": (-2.25, -0.2, PP_ALIGN.RIGHT), "Toamasina": (-0.2, 0.35, PP_ALIGN.LEFT),
                "Antsirabe": (-2.25, -0.2, PP_ALIGN.RIGHT), "Fianarantsoa": (0.35, -0.2, PP_ALIGN.LEFT)}
    for k, name in enumerate(order):
        x, y = xy(name)
        box(s, x - 0.27, y - 0.27, 0.54, 0.54, BLUE, str(k + 1), size=20, shape=MSO_SHAPE.OVAL)
        dx, dy, al = name_off[name]
        text(s, x + dx, y + dy, 1.9, 0.4, name, size=20, bold=True, color=TEXT, align=al)
    stats = [("1 286 km", "Held-Karp, tournée exacte"), ("1 542 777 Ar", "à 1 200 Ar/km, 32,1 h de route"),
             ("−18 %", "285 km de moins que l'ordre saisi")]
    for k, (big, small) in enumerate(stats):
        y = 1.65 + k * 1.25
        text(s, 7.6, y, 5.2, 0.65, big, size=36, bold=True, color=TERRA if k == 2 else BLUE)
        text(s, 7.6, y + 0.62, 5.2, 0.45, small, size=20, color=TEXT)
    box(s, 7.6, 5.55, 5.2, 0.85, DARK, "Le planning suit cet ordre, 1 jour de trajet entre 2 villes", size=18)


# --------------------------------------------------------------------------- partie 3


def s18_archi(s):
    background(s, LIGHT)
    title(s, "Architecture du système", part=PART3)
    box(s, 0.6, 1.55, 3.4, 1.05, BLUE, [[("React + TypeScript", {"size": 22})], [("Vite, Tailwind", {"size": 18, "bold": False})]])
    box(s, 4.95, 1.55, 3.4, 1.05, BLUE, [[("API FastAPI", {"size": 22})], [("asynchrone, /api/v1", {"size": 18, "bold": False})]])
    box(s, 9.3, 1.55, 3.4, 1.05, BLUE, [[("Services", {"size": 22})], [("base ↔ algorithmes ↔ IA", {"size": 18, "bold": False})]])
    arrow(s, 4.05, 2.07, 4.9, 2.07)
    arrow(s, 8.4, 2.07, 9.25, 2.07)
    box(s, 9.3, 3.45, 3.4, 1.05, TERRA, [[("Algorithmes", {"size": 22})], [("Python pur, testés seuls", {"size": 18, "bold": False})]])
    box(s, 4.95, 3.45, 3.4, 1.05, DARK, [[("Copilote LLM", {"size": 22})], [("Claude · Gemini · simulé", {"size": 18, "bold": False})]])
    box(s, 0.6, 3.45, 3.4, 1.05, DARK, [[("PostgreSQL 17", {"size": 22})], [("SQLAlchemy asynchrone", {"size": 18, "bold": False})]])
    arrow(s, 11.0, 2.65, 11.0, 3.4)
    arrow(s, 9.85, 2.65, 7.4, 3.4)
    arrow(s, 9.4, 2.55, 2.9, 3.4)
    docker = box(s, 0.6, 4.95, 12.1, 1.45, BLUE_TINT, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, color=TEXT,
                 pad=0.3, radius=0.08, label=[
                     [("Déploiement avec Docker", {"size": 21, "color": BLUE})],
                     [("PostgreSQL dans un conteneur (docker compose, port 5435) : installation identique "
                       "partout ; Alembic gère les migrations.", {"size": 19, "bold": False})]])
    docker.name = "Docker"


def s19_tech(s):
    background(s, LIGHT)
    title(s, "Les technologies", part=PART3)
    rows = [("Couche", "Technologie", "Rôle"),
            ("Frontend", "React 18, TypeScript, Vite, Tailwind, Recharts", "Les écrans"),
            ("API", "FastAPI, Pydantic v2, SQLAlchemy 2 asynchrone", "Routes, validation"),
            ("Algorithmes", "Python pur", "Les décisions chiffrées"),
            ("LLM", "Claude (claude-haiku-5-5), Gemini, simulé", "Dialogue, explication"),
            ("Base de données", "PostgreSQL 17 + Alembic", "Données, migrations"),
            ("Docker", "docker compose", "Base identique partout"),
            ("Tests", "pytest + httpx", "Algorithmes et parcours API")]
    table_rows(s, 0.6, 1.4, (2.55, 6.2, 3.4), rows, row_h=0.6, gap=0.07, size=17)


def s20_quality(s):
    background(s, LIGHT)
    title(s, "Qualité et fiabilité", part=PART3)
    cards = [("153 tests", "pytest, dont 93 sur les algorithmes", BLUE),
             ("Vérification", "verify_selection, verify_schedule (8 contrôles)", BLUE),
             ("= force brute", "sac à dos identique sur 200 instances aléatoires", TERRA),
             ("Mode simulé", "démo sans réseau ; plafond de 4 $ pour le LLM", TERRA)]
    for k, (big, small, col) in enumerate(cards):
        x, y = 0.6 + (k % 2) * 6.2, 1.6 + (k // 2) * 2.35
        box(s, x, y, 5.95, 2.05, WHITE, line=GRID, radius=0.08)
        text(s, x + 0.35, y + 0.25, 5.3, 0.8, big, size=38, bold=True, color=col)
        text(s, x + 0.35, y + 1.15, 5.3, 0.75, small, size=20, color=TEXT)
    text(s, 0.6, 6.4, 12.2, 0.45, "Un planning ou un périmètre faux n'est jamais renvoyé : il est refusé avant.",
         size=18, color=MUTED, italic=True)


# --------------------------------------------------------------------------- partie 4


def s21_demo(s):
    background(s, LIGHT)
    title(s, "Démonstration (4 minutes)", part=PART4)
    marks = [("0:00", "Connexion, inscription"), ("0:30", "Copilote (Claude)"), ("1:30", "Périmètre, et si ?"),
             ("2:00", "Équipe, Pareto"), ("2:45", "Planning, retard"), ("3:30", "Synthèse, explication, PDF")]
    x0, step, y = 1.1, 2.2, 2.9
    arrow(s, 0.6, y, 12.8, y, color=GRID, width=3, head=False)
    for k, (t, label) in enumerate(marks):
        x = x0 + k * step
        tag = f"g:jalon{k}"  # le numéro, l'heure et l'étiquette d'un jalon apparaissent ensemble
        box(s, x - 0.42, y - 0.42, 0.84, 0.84, TERRA if k == 4 else BLUE, str(k + 1), size=22, shape=MSO_SHAPE.OVAL,
            name=tag)
        text(s, x - 0.9, y - 1.15, 1.8, 0.45, t, size=20, bold=True, color=MUTED, align=PP_ALIGN.CENTER, name=tag)
        text(s, x - 1.05, y + 0.6, 2.1, 1.0, label, size=20, color=TEXT, align=PP_ALIGN.CENTER, name=tag)
    box(s, 0.6, 5.1, 12.2, 0.95, BLUE_TINT, "Plan B sans réseau : copilote simulé, mêmes résultats calculés",
        size=20, color=TEXT, bold=False)


def s22_results(s):
    background(s, LIGHT)
    title(s, "Résultats mesurés", part=PART4)
    cards = [("18 nœuds", "sac à dos Boutique Soa, optimum prouvé", BLUE),
             ("≤ 28,4 ms", "40 fonctionnalités, au pire (2 106 nœuds)", BLUE),
             ("13 nœuds", "1re solution du planning, puis optimum prouvé", BLUE),
             ("0 nœud", "planning impossible (3 semaines) prouvé sans recherche", TERRA),
             ("5,3 %", "écart moyen du glouton seul (40 fonctionnalités)", TERRA),
             ("153 tests", "passés (pytest)", TERRA)]
    for k, (big, small, col) in enumerate(cards):
        x, y = 0.6 + (k % 3) * 4.1, 1.55 + (k // 3) * 2.3
        box(s, x, y, 3.85, 2.05, WHITE, line=GRID, radius=0.08)
        text(s, x + 0.28, y + 0.22, 3.35, 0.75, big, size=34, bold=True, color=col)
        text(s, x + 0.28, y + 1.0, 3.35, 0.95, small, size=18, color=TEXT)
    text(s, 0.6, 6.3, 12.2, 0.45, "Mesures recalculées en direct sur la page « Comparaison des méthodes ».",
         size=18, color=MUTED, italic=True)


def s23_limits(s):
    background(s, LIGHT)
    title(s, "Limites et perspectives", part=PART4)
    text(s, 0.6, 1.55, 6.0, 0.5, "Limites assumées", size=24, bold=True, color=TERRA)
    text(s, 6.95, 1.55, 6.0, 0.5, "Perspectives", size=24, bold=True, color=BLUE)
    left = ["Coûts estimés par des taux moyens", "Jours fériés non gérés", "Messages de validation en anglais"]
    right = ["Paiement Mobile Money réel (MVola, Orange Money)", "Min-Conflict étendu aux absences imprévues"]
    for k, item in enumerate(left):
        box(s, 0.6, 2.25 + k * 1.15, 5.9, 0.9, TERRA_TINT, item, size=20, color=TEXT, bold=False,
            align=PP_ALIGN.LEFT, pad=0.25)
    for k, item in enumerate(right):
        box(s, 6.95, 2.25 + k * 1.15, 5.85, 0.9, BLUE_TINT, item, size=20, color=TEXT, bold=False,
            align=PP_ALIGN.LEFT, pad=0.25)


def s24_conclusion(s):
    background(s, DARK)
    title(s, "Conclusion", dark=True)
    q = box(s, 0.9, 1.85, 11.5, 2.4, DARK_CARD, anchor=MSO_ANCHOR.MIDDLE, pad=0.5, radius=0.06, label=[[
        ("« Le copilote comprend et explique ; ", {"size": 32, "color": WHITE}),
        ("les algorithmes décident et garantissent. »", {"size": 32, "color": TERRA})]])
    q.name = "Message final"
    bricks(s, 0.9, 4.75, [BLUE, TERRA, BLUE, TERRA, BLUE, TERRA], size=0.45)
    text(s, 0.9, 5.4, 11, 0.8, "Merci — vos questions", size=36, bold=True, color=WHITE)


# (fonction de dessin, fond sombre, animée au clic, mots-clés de secours pour les notes)
SLIDES = [
    (s01_cover, True, False, "SmartBricks · copilote + algorithmes"),
    (s02_why, True, True, "vision · Madagascar · 3 publics"),
    (s03_project, False, True, "client décide · IA explique · algorithmes calculent"),
    (s04_problem, False, True, "garantir, pas estimer"),
    (s05_difficulties, False, True, "Boutique Soa · 15,2 M Ar pour 6 M"),
    (s06_overview, False, True, "6 lignes · qui sert à quoi"),
    (s07_flow, False, True, "copilote → sprint → équipe → planning → explication"),
    (s08_copilot_how, False, True, "dialogue · JSON · contrôles · vérifié"),
    (s09_copilot_app, False, True, "14 fonctionnalités · exact choisi"),
    (s10_knapsack_how, False, True, "densité · borne min des 2 · élagage"),
    (s11_knapsack_app, False, True, "4/14 · 92 % · 18 nœuds · +MVola"),
    (s12_matching_how, False, True, "5 critères · normaliser · Pareto sans poids"),
    (s13_matching_app, False, True, "Toky compromis · Rivo dominé"),
    (s14_csp_how, False, True, "chemin critique · MRV · anticiper · 3 s"),
    (s15_csp_app, False, True, "18 jours · borne 11 · Hasina 16 > 15"),
    (s18_archi, False, True, "React → FastAPI → services → algorithmes"),
    (s19_tech, False, True, "Docker · Alembic · pytest"),
    (s20_quality, False, True, "153 tests · vérifications indépendantes"),
    (s21_demo, False, True, "reset-demo d'abord · plan B simulé"),
    (s22_results, False, True, "18 nœuds · 0 nœud · 153 tests"),
    (s23_limits, False, True, "taux moyens · fériés · Mobile Money"),
    (s24_conclusion, True, False, "comprend/explique · décide/garantit"),
]


def main() -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    prs.core_properties.title = "SmartBricks — soutenance"
    blank = prs.slide_layouts[6]
    report = []
    for n, (draw, dark, animated, keywords) in enumerate(SLIDES, start=1):
        slide = prs.slides.add_slide(blank)
        draw(slide)
        slide_number(slide, n, dark)
        slide.notes_slide.notes_text_frame.text = keywords
        add_transition(slide)
        clicks = add_click_animations(slide, click_groups(slide)) if animated else 0
        report.append((n, draw.__name__, clicks))
    prs.save(OUT)
    print(f"{OUT.name} : {len(SLIDES)} diapositives, transitions en fondu, apparitions au clic.")
    for n, name, clicks in report:
        print(f"  {n:>2}  {name:<20} {clicks} clic(s)")


if __name__ == "__main__":
    main()
