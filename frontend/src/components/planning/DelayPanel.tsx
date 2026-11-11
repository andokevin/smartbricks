/** Panneau « Signaler un retard » — module D, niveau B : réparation par Min-Conflict (n°11).
 *
 * Le client (ou le chef de projet) indique qu'une tâche demandera plus d'heures. Le serveur répare le
 * planning en déplaçant le moins de tâches possible ; s'il réussit, le planning réparé devient le
 * planning réel, sinon rien n'est modifié et le diagnostic s'affiche.
 */
import { useState } from "react";

import { api } from "../../api/client";
import type { Repair, Schedule } from "../../api/types";
import { Button, Card, Icon } from "../ui";
import { formatDate } from "../../lib/format";

export function RepairSummary({ repair }: { repair: Repair }) {
  const ok = repair.status === "OK";
  return (
    <div className="flex flex-col gap-1 text-body-sm">
      <p className="text-body-md text-on-surface">
        Retard de <strong>{repair.delay_hours} h</strong> sur <strong className="text-primary">{repair.task_ref}</strong> {repair.task_title}
        {repair.delayed_end && <> : elle finit désormais le {formatDate(repair.delayed_end)}.</>}
      </p>
      {ok ? (
        <>
          <p className="text-on-surface">
            {repair.changed.length === 0
              ? "Aucune autre tâche n'a dû bouger."
              : `${repair.changed.length} tâche${repair.changed.length > 1 ? "s" : ""} déplacée${repair.changed.length > 1 ? "s" : ""} : ${repair.changed.join(", ")}.`}{" "}
            {repair.reassigned.length === 0
              ? "Aucun changement de freelance."
              : `Changement de freelance pour : ${repair.reassigned.join(", ")}.`}
          </p>
          {repair.previous_makespan_days !== null && repair.new_makespan_days !== null && (
            <p className="text-on-surface-variant">
              Durée : {repair.previous_makespan_days} → {repair.new_makespan_days} jours ouvrés · {repair.steps} étape{repair.steps > 1 ? "s" : ""} de
              Min-Conflict en {repair.elapsed_ms.toLocaleString("fr-FR")} ms.
            </p>
          )}
        </>
      ) : (
        <>
          {repair.diagnostics.map((d) => <p key={d} className="text-on-surface">{d}</p>)}
          <p className="text-on-surface-variant">Le planning n'a pas été modifié.</p>
        </>
      )}
      {repair.full_replan?.status === "OK" && repair.full_replan.makespan_days !== null && (
        <p className="text-on-surface-variant">
          À comparer : une replanification complète (CSP n°3) donnerait {repair.full_replan.makespan_days} jours ouvrés
          {repair.full_replan.end_date && <> (fin le {formatDate(repair.full_replan.end_date)})</>}, en déplaçant{" "}
          {repair.full_replan.changed_count} tâche(s).
          {ok && repair.new_makespan_days !== null && repair.full_replan.makespan_days < repair.new_makespan_days &&
            " Pour la privilégier, cliquez sur « Recalculer le planning »."}
        </p>
      )}
      {repair.full_replan && repair.full_replan.status !== "OK" && (
        <p className="text-on-surface-variant">Même une replanification complète ne tient pas la date limite avec ce retard.</p>
      )}
    </div>
  );
}

export function DelayPanel({ schedule, onRepaired }: { schedule: Schedule; onRepaired: (s: Schedule) => void }) {
  const [taskId, setTaskId] = useState<number>(schedule.assignments[0]?.task_id ?? 0);
  const [hoursText, setHoursText] = useState("8");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [last, setLast] = useState<Repair | null>(null);
  const hours = Number(hoursText);
  const valid = Number.isInteger(hours) && hours > 0 && hours <= 400;

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.propagateDelay(taskId, hours);
      setLast(r.repair);
      if (r.schedule) onRepaired(r.schedule);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="flex flex-col gap-space-sm p-space-lg">
      <span className="flex items-center gap-space-xs text-label-md uppercase tracking-wider text-on-surface">
        <Icon name="running_with_errors" className="text-[18px] text-tertiary" />
        Signaler un retard
        <span className="ml-auto rounded bg-surface-container-high px-1.5 py-0.5 text-label-sm normal-case tracking-normal text-on-surface-variant">Min-Conflict n°11</span>
      </span>
      <p className="text-body-sm text-on-surface-variant">
        Une tâche demandera plus d'heures que prévu ? Le planning est réparé en déplaçant le moins de tâches possible, en gardant si possible les mêmes freelances.
      </p>
      <label className="flex flex-col gap-1 text-label-md text-on-surface">
        Tâche en retard
        <select
          value={taskId}
          onChange={(e) => setTaskId(Number(e.target.value))}
          className="rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-body-md text-on-surface"
        >
          {schedule.assignments.map((a) => (
            <option key={a.task_id} value={a.task_id}>{a.ref} {a.title} ({a.freelancer})</option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-label-md text-on-surface">
        Heures supplémentaires
        <input
          type="number"
          min={1}
          max={400}
          value={hoursText}
          onChange={(e) => setHoursText(e.target.value)}
          className="w-32 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-body-md text-on-surface"
        />
      </label>
      <Button icon="build" disabled={busy || !valid} onClick={() => void submit()}>
        {busy ? "Réparation…" : "Réparer le planning"}
      </Button>
      {error && <p className="text-body-sm text-error">{error}</p>}
      {last && (
        <div className={last.status === "OK" ? "rounded-xl bg-secondary-container/40 p-space-sm" : "rounded-xl bg-tertiary-fixed/40 p-space-sm"}>
          <RepairSummary repair={last} />
        </div>
      )}
    </Card>
  );
}
