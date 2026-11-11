/** Diagramme de Gantt : une ligne par freelance, l'axe en jours OUVRÉS (week-ends retirés).
 *
 * - Barres : tâches planifiées par le CSP (n°3), couleur = freelance (ordre fixe, palette vérifiée).
 * - Hachures : indisponibilités du freelance (la tâche est mise en pause, jamais planifiée dessus).
 * - Contour foncé : tâches du chemin critique. Trait rouge pointillé : date limite.
 */
import type { Assignment, FreelancerInfo, Schedule } from "../../api/types";
import { datesBetween, isMonday, maxIso, workingDays } from "../../lib/calendar";
import { formatShortDate } from "../../lib/format";
import { cx, Icon } from "../ui";

const DAY = 28; // largeur d'un jour ouvré, en pixels
// Colonne des noms : plus étroite sur téléphone.
const LABEL = typeof window !== "undefined" && window.innerWidth < 640 ? 130 : 190;

// Palette catégorielle (ordre fixe), avec la couleur de texte lisible sur chaque teinte.
const PALETTE: { bg: string; text: string }[] = [
  { bg: "#1e5aa8", text: "#ffffff" },
  { bg: "#eb6834", text: "#121c2a" },
  { bg: "#1baf7a", text: "#121c2a" },
  { bg: "#eda100", text: "#121c2a" },
  { bg: "#e87ba4", text: "#121c2a" },
  { bg: "#6250d6", text: "#ffffff" },
  { bg: "#008300", text: "#ffffff" },
  { bg: "#e34948", text: "#ffffff" },
];

export function colorFor(index: number) {
  return PALETTE[index % PALETTE.length] as { bg: string; text: string };
}

export function Gantt({ schedule, freelancers }: { schedule: Schedule; freelancers: Map<number, FreelancerInfo> }) {
  const days = workingDays(schedule.start_date, maxIso(schedule.deadline, schedule.end_date));
  const index = new Map(days.map((d, i) => [d, i]));
  const critical = new Set(schedule.critical_path);
  let deadlineIdx = -1; // dernier jour ouvré ≤ date limite
  days.forEach((d, i) => {
    if (d <= schedule.deadline) deadlineIdx = i;
  });
  const width = days.length * DAY;

  // Semaines : début à chaque lundi (ou au premier jour affiché).
  const weeks: { start: number; label: string }[] = [];
  days.forEach((d, i) => {
    if (i === 0 || isMonday(d)) weeks.push({ start: i, label: formatShortDate(d) });
  });

  const rows = schedule.team.map((member, i) => {
    const off = new Set(
      (freelancers.get(member.id)?.unavailability ?? []).flatMap((u) => datesBetween(u.start, u.end)),
    );
    const tasks = schedule.assignments.filter((a) => a.freelancer_id === member.id);
    return { member, color: colorFor(i), off, tasks, hours: tasks.reduce((s, t) => s + t.hours, 0) };
  });

  function bar(a: Assignment, color: { bg: string; text: string }) {
    const s = index.get(a.start) ?? 0;
    const e = index.get(a.end) ?? s;
    const tip = `${a.ref} · ${a.title}\n${a.skill} · ${a.hours} h · ${a.days} jour(s) de travail\n${formatShortDate(a.start)} → ${formatShortDate(a.end)}${a.depends_on.length ? `\nAprès : ${a.depends_on.join(", ")}` : ""}${a.on_site_city ? `\nSur site : ${a.on_site_city}` : ""}`;
    return (
      <div
        key={a.task_id}
        title={tip}
        className={cx(
          "absolute top-1.5 flex h-8 items-center gap-1 overflow-hidden rounded-md px-1.5 text-label-sm shadow-card",
          critical.has(a.ref) && "outline outline-2 outline-offset-1 outline-inverse-surface",
        )}
        style={{ left: s * DAY + 1, width: (e - s + 1) * DAY - 2, background: color.bg, color: color.text }}
      >
        {a.on_site_city && <Icon name="pin_drop" className="text-[14px]" />}
        <span className="shrink-0 rounded bg-black/15 px-1">{a.ref}</span>
        <span className="truncate">{a.title}</span>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto pb-2">
      <div style={{ width: width + LABEL }} className="relative select-none">
        {/* En-tête : semaines puis jours */}
        <div className="flex border-b border-surface-container-high">
          <div className="sticky left-0 z-20 shrink-0 bg-surface-container-lowest" style={{ width: LABEL }} />
          <div className="relative h-12" style={{ width }}>
            {weeks.map((w, i) => (
              <div
                key={w.start}
                className="absolute top-0 h-6 border-l border-surface-container-high pl-1 text-label-sm text-on-surface"
                style={{ left: w.start * DAY, width: ((weeks[i + 1]?.start ?? days.length) - w.start) * DAY }}
              >
                Sem. {i + 1} <span className="font-normal text-on-surface-variant">· {w.label}</span>
              </div>
            ))}
            {days.map((d, i) => (
              <div key={d} className="absolute top-6 flex h-6 items-center justify-center text-[10px] text-outline" style={{ left: i * DAY, width: DAY }}>
                {Number(d.slice(8))}
              </div>
            ))}
          </div>
        </div>

        {/* Lignes */}
        {rows.map(({ member, color, off, tasks, hours }) => (
          <div key={member.id} className="flex border-b border-surface-container-high/60">
            <div className="sticky left-0 z-20 flex shrink-0 flex-col justify-center bg-surface-container-lowest py-1 pr-2" style={{ width: LABEL }}>
              <span className="flex items-center gap-1.5 truncate text-label-md text-on-surface">
                <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: color.bg }} />
                {member.name}
              </span>
              <span className="text-body-sm text-on-surface-variant">
                {tasks.length} tâche(s) · {hours} h · {member.hours_per_day} h/j
              </span>
            </div>
            <div className="relative h-11" style={{ width }}>
              {days.map((d, i) => (
                <div
                  key={d}
                  className={cx("absolute inset-y-0", isMonday(d) && "border-l border-surface-container-high")}
                  style={{
                    left: i * DAY,
                    width: DAY,
                    backgroundImage: off.has(d)
                      ? "repeating-linear-gradient(135deg, rgba(115,119,130,.28) 0 3px, transparent 3px 7px)"
                      : undefined,
                  }}
                  title={off.has(d) ? `${member.name} indisponible le ${formatShortDate(d)}` : undefined}
                />
              ))}
              {tasks.map((a) => bar(a, color))}
            </div>
          </div>
        ))}

        {/* Date limite */}
        {deadlineIdx >= 0 && (
          <div className="pointer-events-none absolute bottom-0 top-0 z-10" style={{ left: LABEL + (deadlineIdx + 1) * DAY - 1 }}>
            <div className="h-full border-l-2 border-dashed border-error" />
            <span className="absolute -top-0.5 left-1 whitespace-nowrap rounded bg-error px-1.5 py-0.5 text-[10px] font-bold text-white">
              Date limite
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
