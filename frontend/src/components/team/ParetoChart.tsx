/** Nuage de Pareto (n°21) : coût × rapidité, taille = qualité.
 *
 * Bleu = premier front (non dominé) ; gris = fronts suivants ; étoile + étiquette = meilleur
 * compromis ; anneau foncé = freelance retenu. La couleur n'est jamais le seul indice.
 */
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
  type TooltipProps,
} from "recharts";

import type { MatchingRow } from "../../api/types";
import { formatAr } from "../../lib/format";
import { Icon } from "../ui";

interface Point {
  id: number;
  name: string;
  x: number;
  y: number;
  z: number;
  front: number;
  best: boolean;
  selected: boolean;
}

const FRONT_COLOR = "#1e5aa8";
const OTHER_COLOR = "#c2c6d3";
const RING = "#121c2a";

function compactAr(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)} k`;
  return String(n);
}

function Dot(props: { cx?: number; cy?: number; payload?: Point; size?: number }) {
  const { cx = 0, cy = 0, payload, size = 64 } = props;
  if (!payload) return null;
  const r = Math.max(5, Math.sqrt(size / Math.PI) * 1.4);
  const fill = payload.front === 1 ? FRONT_COLOR : OTHER_COLOR;
  if (payload.best) {
    const s = r * 1.6;
    const pts = Array.from({ length: 10 }, (_, i) => {
      const a = (Math.PI / 5) * i - Math.PI / 2;
      const rr = i % 2 === 0 ? s : s * 0.45;
      return `${cx + rr * Math.cos(a)},${cy + rr * Math.sin(a)}`;
    }).join(" ");
    return (
      <g>
        <polygon points={pts} fill={FRONT_COLOR} stroke="#ffffff" strokeWidth={2} />
        {payload.selected && <circle cx={cx} cy={cy} r={s + 4} fill="none" stroke={RING} strokeWidth={2} />}
        <text x={cx} y={cy - s - 8} textAnchor="middle" fontSize={11} fontWeight={700} fill="#121c2a">
          Meilleur compromis
        </text>
      </g>
    );
  }
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={fill} fillOpacity={payload.front === 1 ? 0.9 : 0.8} stroke="#ffffff" strokeWidth={2} />
      {payload.selected && <circle cx={cx} cy={cy} r={r + 3.5} fill="none" stroke={RING} strokeWidth={2} />}
    </g>
  );
}

function Tip({ active, payload }: TooltipProps<number, string>) {
  const p = payload?.[0]?.payload as Point | undefined;
  if (!active || !p) return null;
  return (
    <div className="rounded-lg bg-inverse-surface px-3 py-2 text-body-sm text-inverse-on-surface shadow-overlay">
      <div className="text-label-md">{p.name}</div>
      <div>Coût : {formatAr(p.x)}</div>
      <div>Rapidité : {p.y.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} jours</div>
      <div>Qualité : {p.z.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} / 5</div>
      <div>Front n°{p.front}{p.best ? " · meilleur compromis" : ""}{p.selected ? " · retenu" : ""}</div>
    </div>
  );
}

export function ParetoChart({ rows, selected }: { rows: MatchingRow[]; selected: Set<number> }) {
  const points: Point[] = rows
    .filter((r) => r.criteria.speed !== null)
    .map((r) => ({
      id: r.id,
      name: r.name,
      x: r.criteria.cost,
      y: r.criteria.speed as number,
      z: r.criteria.quality,
      front: r.front,
      best: r.best_compromise,
      selected: selected.has(r.id),
    }));
  // Les points du front 1 sont dessinés en dernier, par-dessus les autres.
  const others = points.filter((p) => p.front !== 1);
  const front = points.filter((p) => p.front === 1 && !p.best);
  const best = points.filter((p) => p.best);

  return (
    <div className="flex flex-col gap-2">
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 24, right: 16, bottom: 28, left: 8 }}>
            <CartesianGrid stroke="#dee9fc" strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x"
              name="Coût"
              scale="log"
              domain={["auto", "auto"]}
              tickFormatter={compactAr}
              tick={{ fontSize: 11, fill: "#424751" }}
              stroke="#c2c6d3"
              label={{ value: "Coût (Ar, échelle log.) → moins cher à gauche", position: "insideBottom", offset: -16, fontSize: 11, fill: "#424751" }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Rapidité"
              tick={{ fontSize: 11, fill: "#424751" }}
              stroke="#c2c6d3"
              width={40}
              label={{ value: "Jours", angle: -90, position: "insideLeft", fontSize: 11, fill: "#424751" }}
            />
            <ZAxis type="number" dataKey="z" range={[40, 260]} name="Qualité" />
            <Tooltip content={<Tip />} cursor={{ strokeDasharray: "3 3" }} />
            <Scatter data={others} shape={<Dot />} isAnimationActive={false} />
            <Scatter data={front} shape={<Dot />} isAnimationActive={false} />
            <Scatter data={best} shape={<Dot />} isAnimationActive={false} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-label-sm text-on-surface-variant">
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full" style={{ background: FRONT_COLOR }} /> Front 1 (non dominés)</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full" style={{ background: OTHER_COLOR }} /> Fronts suivants</span>
        <span className="flex items-center gap-1.5"><Icon name="star" filled className="text-[16px] text-primary-container" /> Meilleur compromis</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full border-2" style={{ borderColor: RING }} /> Retenu</span>
        <span>Taille du point = qualité</span>
      </div>
    </div>
  );
}
