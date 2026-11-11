/** Espace freelance (niveau B).
 *
 * Le freelance voit les tâches qui lui sont confiées par le planning (CSP n°3), les fait avancer,
 * signale un retard (réparation par Min-Conflict n°11) et déclare ses indisponibilités, que le
 * matching et le planning utilisent. Une indisponibilité qui tombe sur une tâche déjà planifiée
 * ne modifie rien en silence : elle est signalée ici et sur l'écran Planning du client.
 */
import { useState, type FormEvent } from "react";

import { api } from "../api/client";
import type { MyProfile, MyTask, Repair, TaskStatus } from "../api/types";
import { AppShell } from "../components/AppShell";
import { RepairSummary } from "../components/planning/DelayPanel";
import { Button, Card, cx, ErrorBanner, Icon, Spinner } from "../components/ui";
import { formatAr, formatDate, formatShortDate } from "../lib/format";
import { useAsync } from "../lib/useAsync";

const STATUS_LABEL: Record<TaskStatus, string> = {
  BACKLOG: "Non planifiée",
  TODO: "À faire",
  IN_PROGRESS: "En cours",
  REVIEW: "En relecture",
  DONE: "Terminée",
  OVERDUE: "En retard",
};
const EDITABLE: TaskStatus[] = ["TODO", "IN_PROGRESS", "REVIEW", "DONE"];
const STATUS_TONE: Record<TaskStatus, string> = {
  BACKLOG: "bg-surface-container-high text-on-surface-variant",
  TODO: "bg-surface-container-high text-on-surface",
  IN_PROGRESS: "bg-primary-container text-on-primary",
  REVIEW: "bg-tertiary-fixed text-tertiary",
  DONE: "bg-secondary-container text-on-secondary-container",
  OVERDUE: "bg-error-container text-on-error-container",
};

const field = "rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-body-md text-on-surface";

function TaskCard({ task, onChanged }: { task: MyTask; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [delayOpen, setDelayOpen] = useState(false);
  const [hoursText, setHoursText] = useState("4");
  const [repair, setRepair] = useState<Repair | null>(null);

  async function setStatus(status: TaskStatus) {
    setBusy(true);
    setError(null);
    try {
      await api.setMyTaskStatus(task.id, status);
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function reportDelay() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.propagateDelay(task.id, Number(hoursText));
      setRepair(r.repair);
      if (r.repair.status === "OK") onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const waiting = task.depends_on.filter((d) => d.status !== "DONE");
  return (
    <Card className="flex flex-col gap-space-sm p-space-md sm:p-space-lg">
      <div className="flex flex-wrap items-start justify-between gap-space-sm">
        <div className="min-w-0">
          <span className="text-body-sm text-on-surface-variant">
            {task.project.title.startsWith(task.project.client) ? task.project.title : `${task.project.client} · ${task.project.title}`}
          </span>
          <h3 className="text-title-md font-bold text-on-surface">
            <span className="text-primary">{task.ref}</span> {task.title}
          </h3>
        </div>
        <label className="flex items-center gap-1.5 text-label-md text-on-surface-variant">
          <span className="sr-only">Statut</span>
          <select
            value={task.status}
            disabled={busy}
            onChange={(e) => void setStatus(e.target.value as TaskStatus)}
            className={cx("rounded-lg px-2 py-1 text-label-md", STATUS_TONE[task.status])}
          >
            {!EDITABLE.includes(task.status) && <option value={task.status}>{STATUS_LABEL[task.status]}</option>}
            {EDITABLE.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-x-space-md gap-y-1 text-body-sm text-on-surface-variant">
        <span className="flex items-center gap-1"><Icon name="event" className="text-[16px]" />
          {task.start && task.end ? `${formatShortDate(task.start)} → ${formatDate(task.end)}` : "Non planifiée"}
        </span>
        <span className="flex items-center gap-1"><Icon name="schedule" className="text-[16px]" />{task.hours} h</span>
        <span className="flex items-center gap-1"><Icon name="code" className="text-[16px]" />{task.skill} (niveau {task.min_level})</span>
        {task.on_site_city && (
          <span className="flex items-center gap-1 font-medium text-on-surface"><Icon name="pin_drop" className="text-[16px]" />Sur site : {task.on_site_city}</span>
        )}
      </div>

      {task.depends_on.length > 0 && (
        <p className="text-body-sm text-on-surface">
          {waiting.length === 0 ? (
            <span className="text-secondary">Prête à démarrer : les tâches préalables sont terminées.</span>
          ) : (
            <>
              En attente de :{" "}
              {waiting.map((d, i) => (
                <span key={d.ref}>
                  {i > 0 && ", "}
                  <strong>{d.ref}</strong> {d.title}
                  {d.freelancer && ` (${d.freelancer}`}
                  {d.end && `, fin prévue le ${formatShortDate(d.end)}`}
                  {d.freelancer && ")"}
                </span>
              ))}
            </>
          )}
        </p>
      )}

      {task.alerts.map((a) => (
        <p key={a} className="flex items-start gap-1.5 rounded-lg bg-tertiary-fixed/40 p-space-xs text-body-sm text-on-surface">
          <Icon name="event_busy" className="mt-0.5 text-[16px] text-tertiary" />{a}
        </p>
      ))}

      {task.status !== "DONE" && task.start && (
        <div className="flex flex-col gap-space-xs">
          {!delayOpen ? (
            <button onClick={() => setDelayOpen(true)} className="self-start text-label-md text-primary hover:underline">
              Signaler un retard sur cette tâche
            </button>
          ) : (
            <div className="flex flex-wrap items-end gap-space-sm rounded-xl bg-surface-container-low p-space-sm">
              <label className="flex flex-col gap-1 text-label-md text-on-surface">
                Heures supplémentaires
                <input type="number" min={1} max={400} value={hoursText} onChange={(e) => setHoursText(e.target.value)} className={cx(field, "w-28")} />
              </label>
              <Button icon="build" disabled={busy || !(Number(hoursText) > 0)} onClick={() => void reportDelay()}>
                {busy ? "Réparation…" : "Réparer le planning"}
              </Button>
              <Button variant="ghost" onClick={() => setDelayOpen(false)}>Annuler</Button>
            </div>
          )}
          {repair && (
            <div className={repair.status === "OK" ? "rounded-xl bg-secondary-container/40 p-space-sm" : "rounded-xl bg-tertiary-fixed/40 p-space-sm"}>
              <RepairSummary repair={repair} />
            </div>
          )}
        </div>
      )}
      {error && <p className="text-body-sm text-error">{error}</p>}
    </Card>
  );
}

function Unavailabilities({ profile, onChanged }: { profile: MyProfile; onChanged: () => void }) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [affected, setAffected] = useState<string[] | null>(null);

  async function add(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api.addUnavailability({ start, end: end || start, reason: reason.trim() || null });
      setAffected(r.affected_tasks);
      setStart("");
      setEnd("");
      setReason("");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    setBusy(true);
    try {
      await api.deleteUnavailability(id);
      setAffected(null);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="flex flex-col gap-space-sm p-space-lg">
      <span className="flex items-center gap-space-xs text-label-md uppercase tracking-wider text-on-surface">
        <Icon name="event_busy" className="text-[18px] text-primary" />
        Mes indisponibilités
      </span>
      <p className="text-body-sm text-on-surface-variant">
        Congés, autres missions… Le matching et le planning n'affectent jamais de travail sur ces jours.
      </p>
      {profile.unavailability.length === 0 ? (
        <p className="text-body-sm text-outline">Aucune indisponibilité déclarée.</p>
      ) : (
        <ul className="flex flex-col gap-space-xs">
          {profile.unavailability.map((u) => (
            <li key={u.id} className="flex items-center justify-between gap-2 rounded-lg bg-surface-container-low px-space-sm py-space-xs">
              <span className="text-body-sm text-on-surface">
                {u.start === u.end ? formatDate(u.start) : `${formatShortDate(u.start)} → ${formatDate(u.end)}`}
                {u.reason && <span className="text-on-surface-variant"> · {u.reason}</span>}
              </span>
              <button
                onClick={() => void remove(u.id)}
                disabled={busy}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-on-surface-variant hover:bg-surface-container"
                aria-label="Supprimer cette indisponibilité"
                title="Supprimer"
              >
                <Icon name="delete" className="text-[18px]" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={(e) => void add(e)} className="flex flex-col gap-space-xs border-t border-surface-container-high pt-space-sm">
        <div className="grid grid-cols-2 gap-space-xs">
          <label className="flex flex-col gap-1 text-label-md text-on-surface">
            Du
            <input type="date" required value={start} onChange={(e) => setStart(e.target.value)} className={field} />
          </label>
          <label className="flex flex-col gap-1 text-label-md text-on-surface">
            Au (inclus)
            <input type="date" value={end} min={start || undefined} onChange={(e) => setEnd(e.target.value)} className={field} />
          </label>
        </div>
        <label className="flex flex-col gap-1 text-label-md text-on-surface">
          Motif (facultatif)
          <input type="text" maxLength={200} value={reason} onChange={(e) => setReason(e.target.value)} className={field} placeholder="Congé, formation…" />
        </label>
        <Button type="submit" icon="add" disabled={busy || !start}>Déclarer</Button>
      </form>
      {affected && (
        <p className={cx("rounded-lg p-space-xs text-body-sm", affected.length ? "bg-tertiary-fixed/40 text-on-surface" : "bg-secondary-container/40 text-on-surface")}>
          {affected.length
            ? `Attention : cette indisponibilité tombe sur ${affected.join(", ")}. Le client est prévenu sur son écran Planning et doit le recalculer.`
            : "Enregistrée : aucune tâche déjà planifiée n'est touchée."}
        </p>
      )}
      {error && <p className="text-body-sm text-error">{error}</p>}
    </Card>
  );
}

export function FreelancerPage() {
  const data = useAsync(async () => {
    const [profile, tasks] = await Promise.all([api.myProfile(), api.myTasks()]);
    return { profile, tasks };
  }, []);
  const profile = data.data?.profile;
  const tasks = data.data?.tasks ?? [];
  const open = tasks.filter((t) => t.status !== "DONE");
  const done = tasks.filter((t) => t.status === "DONE");
  const [showDone, setShowDone] = useState(false);

  return (
    <AppShell crumbs={[{ label: "Espace freelance" }]}>
      {data.error && <ErrorBanner message={data.error} onRetry={data.reload} />}
      {data.loading && !data.data && <Spinner />}
      {profile && (
        <div className="flex flex-col gap-space-lg">
          <div>
            <span className="text-label-md text-primary">Espace freelance</span>
            <h2 className="text-headline-lg-mobile text-on-surface md:text-headline-md">Bonjour {profile.name.split(" ")[0]}</h2>
            <p className="text-body-md text-on-surface-variant">
              {open.length === 0 ? "Aucune tâche en cours." : `${open.length} tâche${open.length > 1 ? "s" : ""} à réaliser`}
              {done.length > 0 && `, ${done.length} terminée${done.length > 1 ? "s" : ""}`}.
            </p>
          </div>

          <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
            <section className="flex flex-col gap-space-md lg:col-span-8">
              {open.length === 0 && (
                <Card className="flex flex-col items-center gap-space-sm p-space-xl text-center">
                  <Icon name="task_alt" className="text-[40px] text-primary" />
                  <p className="text-title-md text-on-surface">Aucune tâche planifiée pour vous pour le moment</p>
                  <p className="text-body-md text-on-surface-variant">Vos tâches apparaîtront ici dès qu'un client vous aura retenu dans son planning.</p>
                </Card>
              )}
              {open.map((t) => <TaskCard key={t.id} task={t} onChanged={data.reload} />)}
              {done.length > 0 && (
                <button onClick={() => setShowDone((v) => !v)} className="self-start text-label-md text-primary hover:underline">
                  {showDone ? "Masquer" : "Afficher"} les tâches terminées ({done.length})
                </button>
              )}
              {showDone && done.map((t) => <TaskCard key={t.id} task={t} onChanged={data.reload} />)}
            </section>

            <aside className="flex flex-col gap-space-md lg:col-span-4">
              <Card className="flex flex-col gap-space-sm p-space-lg">
                <span className="flex items-center gap-space-xs text-label-md uppercase tracking-wider text-on-surface">
                  <Icon name="badge" className="text-[18px] text-primary" />
                  Mon profil
                </span>
                <dl className="grid grid-cols-2 gap-y-1 text-body-sm">
                  <dt className="text-on-surface-variant">Ville</dt><dd className="text-on-surface">{profile.city}</dd>
                  <dt className="text-on-surface-variant">Taux horaire</dt><dd className="text-on-surface">{formatAr(profile.hourly_rate_mga)}</dd>
                  <dt className="text-on-surface-variant">Rythme</dt><dd className="text-on-surface">{profile.hours_per_day} h par jour</dd>
                  <dt className="text-on-surface-variant">Note</dt><dd className="text-on-surface">{profile.rating.toLocaleString("fr-FR")} / 5</dd>
                </dl>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(profile.skills).map(([s, lvl]) => (
                    <span key={s} className="rounded bg-surface-container-high px-1.5 py-0.5 text-label-sm text-on-surface">{s} · niv. {lvl}</span>
                  ))}
                </div>
              </Card>
              <Unavailabilities profile={profile} onChanged={data.reload} />
            </aside>
          </div>
        </div>
      )}
    </AppShell>
  );
}
