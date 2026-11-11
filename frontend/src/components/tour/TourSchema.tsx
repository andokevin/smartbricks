/** Schéma SVG de secours (sans internet) : villes placées d'après leurs coordonnées.
 *
 * Projection équirectangulaire simple (longitude corrigée par cos 19°) sur le cadre de Madagascar.
 * Le contour de l'île est une approximation à ~25 points, seulement pour situer les villes.
 */
import type { City, Tour } from "../../api/types";

const LAT_MIN = -26;
const LAT_MAX = -11.4;
const LON_MIN = 42.8;
const LON_MAX = 51;
const K = Math.cos((19 * Math.PI) / 180);
const H = 640;
const W = Math.round((H * (LON_MAX - LON_MIN) * K) / (LAT_MAX - LAT_MIN));

function xy(lat: number, lon: number): [number, number] {
  return [((lon - LON_MIN) / (LON_MAX - LON_MIN)) * W, ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * H];
}

// Contour simplifié de Madagascar (latitude, longitude), sens horaire depuis le cap d'Ambre.
const COAST: [number, number][] = [
  [-11.95, 49.26], [-12.9, 49.85], [-14.3, 50.2], [-15.5, 50.45], [-16.2, 49.85], [-17.1, 49.45],
  [-18.15, 49.4], [-19.6, 48.85], [-21.2, 48.35], [-22.15, 48.0], [-23.6, 47.6], [-25.05, 47.0],
  [-25.6, 45.15], [-25.0, 44.0], [-23.4, 43.6], [-21.9, 43.3], [-20.3, 44.25], [-18.8, 44.2],
  [-17.0, 44.0], [-16.2, 44.5], [-15.75, 46.3], [-15.2, 47.2], [-14.4, 47.9], [-13.4, 48.3], [-12.5, 49.0],
];

export function TourSchema({ tour, cities }: { tour: Tour; cities: City[] }) {
  const coast = COAST.map(([la, lo]) => xy(la, lo).join(",")).join(" ");
  const stops = tour.order.map((s) => ({ ...s, p: xy(s.latitude, s.longitude) }));
  const first = stops[0];
  const route = [...stops, ...(tour.closed && first ? [first] : [])].map((s) => s.p.join(",")).join(" ");
  const visited = new Set(tour.order.map((s) => s.name));

  // Cadrage sur les villes de la tournée (marge pour les étiquettes), au moins 220 unités de côté.
  const xs = stops.map((s) => s.p[0]);
  const ys = stops.map((s) => s.p[1]);
  const pad = 60;
  let x0 = Math.min(...xs) - pad;
  let x1 = Math.max(...xs) + pad + 110; // place pour les étiquettes à droite
  let y0 = Math.min(...ys) - pad;
  let y1 = Math.max(...ys) + pad;
  const grow = (a: number, b: number) => Math.max(0, 220 - (b - a)) / 2;
  const gx = grow(x0, x1);
  const gy = grow(y0, y1);
  x0 -= gx; x1 += gx; y0 -= gy; y1 += gy;

  return (
    <svg viewBox={`${x0} ${y0} ${x1 - x0} ${y1 - y0}`} className="h-full w-full" role="img" aria-label="Schéma de la tournée sur la carte de Madagascar">
      <polygon points={coast} fill="#dee9fc" stroke="#c2c6d3" strokeWidth={1.5} strokeLinejoin="round" />
      {cities
        .filter((c) => !visited.has(c.name))
        .map((c) => {
          const [x, y] = xy(c.latitude, c.longitude);
          return (
            <g key={c.id}>
              <circle cx={x} cy={y} r={3} fill="#737782" />
              <text x={x + 6} y={y + 3} fontSize={10} fill="#737782">{c.name}</text>
            </g>
          );
        })}
      <polyline points={route} fill="none" stroke="#1e5aa8" strokeWidth={4} strokeLinejoin="round" strokeLinecap="round" />
      {stops.map((s, i) => (
        <g key={s.name}>
          <circle cx={s.p[0]} cy={s.p[1]} r={13} fill={i === 0 ? "#004287" : "#ffffff"} stroke="#004287" strokeWidth={3} />
          <text x={s.p[0]} y={s.p[1] + 4} textAnchor="middle" fontSize={11} fontWeight={800} fill={i === 0 ? "#ffffff" : "#004287"}>
            {s.step}
          </text>
          <rect x={s.p[0] + 17} y={s.p[1] - 10} width={s.name.length * 6.6 + 12} height={20} rx={4} fill="#121c2a" fillOpacity={0.88} />
          <text x={s.p[0] + 23} y={s.p[1] + 4} fontSize={11} fontWeight={700} fill="#ffffff">{s.name}</text>
        </g>
      ))}
    </svg>
  );
}
