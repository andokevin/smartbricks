"""Export PDF du cahier des charges généré (niveau B).

Le document rassemble ce que la plateforme a produit pour le projet, à partir des données enregistrées
(aucun recalcul, aucun texte du LLM) : le projet, les exigences (fonctionnalités) avec la décision du
sac à dos (n°29), les tâches, l'équipe (n°22/21), le planning vérifié (n°3) et la tournée (n°30).
Les sections pas encore calculées sont signalées comme telles, jamais inventées.

Mise en page avec fpdf2 ; police DejaVu Sans (fournie dans app/assets/fonts, licence libre) pour
les accents et les caractères typographiques (—, →, œ).
"""

from datetime import date
from pathlib import Path
from typing import Any

from fpdf import FPDF
from fpdf.fonts import FontFace
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.formatting import format_ar, format_date_fr
from app.errors import AppError
from app.models import Project, User
from app.services import projects_view, scheduling, scoping, touring
from app.services.matching_service import get_team
from app.services.project_data import skills_of

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
BLUE = (30, 90, 168)
HEAD_FILL = (220, 231, 245)
MUTED = (91, 100, 117)
TEXT = (27, 35, 51)
REQ_TYPE = {"FUNCTIONAL": "Fonctionnelle", "TECHNICAL": "Technique", "SECURITY": "Sécurité", "COMPLIANCE": "Conformité"}


class _Doc(FPDF):
    def __init__(self, title: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.doc_title = title
        self.add_font("DejaVu", "", str(FONTS / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(FONTS / "DejaVuSans-Bold.ttf"))
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_title(f"Cahier des charges — {title}")
        self.set_creator("SmartBricks")

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"SmartBricks — Cahier des charges — {self.doc_title}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"Page {self.page_no()} / {{nb}}", align="R")

    # ------------------------------------------------------------------ briques de mise en page
    def h1(self, text: str) -> None:
        self.ln(3)
        self.set_font("DejaVu", "B", 14)
        self.set_text_color(*BLUE)
        self.multi_cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def para(self, text: str, size: float = 10, color: tuple[int, int, int] = TEXT, bold: bool = False) -> None:
        self.set_font("DejaVu", "B" if bold else "", size)
        self.set_text_color(*color)
        self.multi_cell(0, size * 0.5, text, new_x="LMARGIN", new_y="NEXT", align="L")
        self.ln(1)

    def facts(self, rows: list[tuple[str, str]]) -> None:
        """Liste « libellé : valeur » sur deux colonnes."""
        for label, value in rows:
            self.set_font("DejaVu", "B", 9.5)
            self.set_text_color(*MUTED)
            self.cell(56, 5.5, label)
            self.set_font("DejaVu", "", 9.5)
            self.set_text_color(*TEXT)
            self.multi_cell(0, 5.5, value, new_x="LMARGIN", new_y="NEXT", align="L")

    def grid(self, headings: list[str], rows: list[list[str]], widths: tuple[float, ...], size: float = 8) -> None:
        self.set_font("DejaVu", "", size)
        self.set_text_color(*TEXT)
        with self.table(
            col_widths=widths,
            line_height=size * 0.55,
            headings_style=FontFace(emphasis="BOLD", fill_color=HEAD_FILL, color=TEXT),
            borders_layout="HORIZONTAL_LINES",
            padding=1,
            text_align="LEFT",  # pas de justification : elle étire les mots dans les colonnes étroites
        ) as table:
            head = table.row()
            for h in headings:
                head.cell(h)
            for r in rows:
                row = table.row()
                for c in r:
                    row.cell(c)
        self.ln(2)


async def _optional(coro: Any) -> Any:
    """Section facultative : None si elle n'a pas encore été calculée (404)."""
    try:
        return await coro
    except AppError as e:
        if e.status_code == 404:
            return None
        raise


async def build_spec_pdf(session: AsyncSession, project: Project) -> bytes:
    detail = await projects_view.project_detail(session, project)
    client = await session.get(User, project.client_id)
    scope = await _optional_sync(lambda: scoping.stored_scope(project))
    schedule = await _optional(scheduling.latest_schedule(session, project))
    tour = await _optional(touring.latest_tour_run(session, project))
    team = await get_team(session, project)

    pdf = _Doc(project.title)
    pdf.alias_nb_pages()
    pdf.add_page()

    # ------------------------------------------------------------------ page de titre
    pdf.set_font("DejaVu", "B", 9)
    pdf.set_text_color(*BLUE)
    pdf.cell(0, 6, "SMARTBRICKS — CAHIER DES CHARGES GÉNÉRÉ", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(*TEXT)
    pdf.multi_cell(0, 9, project.title, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(2)
    pdf.para(f"Document établi le {format_date_fr(date.today())}. Tous les chiffres viennent des algorithmes de la "
             "plateforme (sac à dos n°29, matching n°22 et n°21, planning n°3, tournée n°30) et des estimations "
             "validées par le client ; aucun n'a été rédigé par l'IA.", size=8.5, color=MUTED)

    # ------------------------------------------------------------------ 1. projet
    pdf.h1("1. Le projet")
    pdf.facts([
        ("Client", (client.organization_name or client.name) if client else "—"),
        ("Budget du sprint 1", format_ar(project.budget_mga)),
        ("Heures du sprint 1", f"{project.budget_hours} h"),
        ("Début", format_date_fr(project.start_date)),
        ("Date limite", format_date_fr(project.target_deadline)),
        ("Ville de base", detail.base_city or "—"),
        ("Interventions sur site", ", ".join(detail.sites) or "aucune"),
    ])
    if detail.description:
        pdf.ln(1)
        pdf.para(detail.description, size=9.5)

    # ------------------------------------------------------------------ 2. exigences
    pdf.h1("2. Exigences (fonctionnalités)")
    total_cost = sum(f.estimated_cost_mga for f in detail.features)
    total_hours = sum(f.estimated_hours for f in detail.features)
    pdf.para(f"{len(detail.features)} fonctionnalités, {total_hours} h et {format_ar(total_cost)} estimés au total. "
             "Valeur métier de 1 à 100, fixée avec le client.", size=9)
    selected = {f.ref: f.selected for f in scope.features} if scope else {}
    pdf.grid(
        ["Réf.", "Fonctionnalité", "Type", "Valeur", "Heures", "Coût", "Oblig.", "Dépend de", "Sprint 1"],
        [[f.ref, f.title, REQ_TYPE.get(f.req_type, f.req_type), str(f.business_value), f"{f.estimated_hours} h",
          format_ar(f.estimated_cost_mga), "oui" if f.is_mandatory else "", ", ".join(f.depends_on) or "—",
          ("retenue" if selected.get(f.ref) else "reportée") if scope else "—"]
         for f in detail.features],
        widths=(9, 44, 20, 12, 13, 24, 11, 18, 17),
    )
    if scope:
        reasons = [(f.ref, f.title, f.reason) for f in scope.features if not f.selected and f.reason]
        if reasons:
            pdf.para("Pourquoi ces fonctionnalités sont reportées :", size=9.5, bold=True)
            for ref, title, reason in reasons:
                pdf.para(f"{ref} {title} — {reason}", size=8.5)

    # ------------------------------------------------------------------ 3. périmètre
    pdf.h1("3. Périmètre du sprint 1 (sac à dos, n°29)")
    if scope is None:
        pdf.para("Le périmètre n'a pas encore été calculé.", color=MUTED)
    elif not scope.feasible:
        pdf.para(scope.message)
    else:
        pdf.facts([
            ("Méthode", f"{scope.method.method} — {'optimum prouvé' if scope.optimal else 'solution approchée'}"),
            ("Valeur métier livrée", str(scope.total_value)),
            ("Coût", f"{format_ar(scope.total_cost_mga)} sur {format_ar(scope.budget_mga)} "
                     f"({round(scope.budget_usage * 100)} %)"),
            ("Heures", f"{scope.total_hours} h sur {scope.budget_hours} h ({round(scope.hours_usage * 100)} %)"),
        ])
        for w in scope.what_if:
            pdf.para(f"Et si ? {w.message}", size=9)

    # ------------------------------------------------------------------ 4. tâches
    pdf.h1("4. Tâches")
    retained = {f.ref for f in detail.features if f.selected_for_sprint}
    pdf.para("Découpage technique de chaque fonctionnalité. La colonne « Sprint 1 » indique les tâches des "
             "fonctionnalités retenues, les seules planifiées.", size=9)
    pdf.grid(
        ["Réf.", "Fonct.", "Tâche", "Compétence", "Heures", "Après", "Sur site", "Sprint 1"],
        [[t.ref, t.feature_ref, t.title, f"{t.required_skill} (niv. {t.min_level})", f"{t.estimated_hours} h",
          ", ".join(t.depends_on) or "—", t.on_site_city or "—", "oui" if t.feature_ref in retained else ""]
         for t in detail.tasks],
        widths=(10, 12, 52, 30, 13, 20, 24, 15),
    )

    # ------------------------------------------------------------------ 5. équipe
    pdf.h1("5. Équipe (matching, n°22 et n°21)")
    if not team:
        pdf.para("L'équipe n'a pas encore été choisie.", color=MUTED)
    else:
        pdf.grid(
            ["Freelance", "Ville", "Taux horaire", "Rythme", "Compétences"],
            [[p.user.name, p.city.name, format_ar(p.hourly_rate_mga), f"{p.hours_per_day} h/jour",
              ", ".join(f"{s} ({lvl})" for s, lvl in sorted(skills_of(p).items(), key=lambda x: -x[1]))]
             for p in team],
            widths=(42, 28, 26, 22, 62),
            size=8.5,
        )

    # ------------------------------------------------------------------ 6. planning
    pdf.h1("6. Planning (satisfaction de contraintes, n°3)")
    if schedule is None:
        pdf.para("Le planning n'a pas encore été calculé.", color=MUTED)
    else:
        checks = schedule.get("verification") or {"checks": []}
        passed = sum(1 for c in checks["checks"] if c["passed"])
        facts = [
            ("Durée", f"{schedule['makespan_days']} jours ouvrés (borne du chemin critique : "
                      f"{schedule['lower_bound_days']} j)"),
            ("Fin des travaux", format_date_fr(schedule["end_date"])),
            ("Méthode", schedule["method"]["method"] + (" — optimum prouvé" if schedule.get("optimal") else "")),
            ("Vérification indépendante", f"{passed}/{len(checks['checks'])} contraintes respectées"),
        ]
        if schedule.get("site_order"):
            facts.append(("Ordre des visites", " → ".join(schedule["site_order"]["cities"])))
        if schedule.get("repair"):
            r = schedule["repair"]
            facts.append(("Dernière réparation", f"retard de {r['delay_hours']} h sur {r['task_ref']} "
                                                 f"(Min-Conflict n°11, {len(r['changed'])} tâche(s) déplacée(s))"))
        pdf.facts(facts)
        pdf.ln(1)
        pdf.grid(
            ["Réf.", "Tâche", "Freelance", "Début", "Fin", "Jours"],
            [[a["ref"], a["title"] + (f" (sur site : {a['on_site_city']})" if a.get("on_site_city") else ""),
              a["freelancer"], _short(a["start"]), _short(a["end"]), str(a["days"])]
             for a in schedule["assignments"]],
            widths=(10, 74, 40, 21, 21, 14),
        )
        for alert in schedule.get("alerts") or []:
            pdf.para(f"Alerte : {alert}", size=8.5, color=(150, 60, 20))

    # ------------------------------------------------------------------ 7. tournée
    pdf.h1("7. Tournée sur site (voyageur de commerce, n°30)")
    if tour is None:
        pdf.para("Aucune tournée validée." if detail.sites else "Pas d'intervention sur site.", color=MUTED)
    else:
        rows = [
            ("Ordre", " → ".join(tour["order"])),
            ("Distance", f"{round(tour['distance_km']):,} km (estimation : vol d'oiseau × 1,35)".replace(",", " ")),
            ("Coût du trajet", format_ar(tour["cost_mga"])),
            ("Méthode", tour["method"]),
        ]
        if tour.get("technician"):
            rows.insert(0, ("Technicien", f"{tour['technician']['name']} (départ de {tour['technician']['city']})"))
        pdf.facts(rows)

    return bytes(pdf.output())


def _short(iso: str) -> str:
    """« 2026-11-16 » → « 16/11/2026 » (colonnes étroites)."""
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


async def _optional_sync(fn: Any) -> Any:
    try:
        return fn()
    except AppError as e:
        if e.status_code == 404:
            return None
        raise
