/** Jours ouvrés côté interface (affichage du Gantt uniquement ; le calcul est fait par l'API). */

function parse(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1));
}

function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** Jours du lundi au vendredi entre deux dates incluses, au format AAAA-MM-JJ. */
export function workingDays(startIso: string, endIso: string): string[] {
  const out: string[] = [];
  const d = parse(startIso);
  const end = parse(endIso);
  while (d <= end) {
    const wd = d.getUTCDay();
    if (wd !== 0 && wd !== 6) out.push(iso(d));
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}

/** Toutes les dates d'une période (incluses). */
export function datesBetween(startIso: string, endIso: string): string[] {
  const out: string[] = [];
  const d = parse(startIso);
  const end = parse(endIso);
  while (d <= end) {
    out.push(iso(d));
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}

export function isMonday(isoDate: string): boolean {
  return parse(isoDate).getUTCDay() === 1;
}

export function maxIso(a: string, b: string | null): string {
  return b && b > a ? b : a;
}
