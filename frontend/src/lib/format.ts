/** Mise en forme française : montants en Ariary, dates, pourcentages. */

const integer = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const longDate = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" });
const shortDate = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" });

/** 6000000 → « 6 000 000 Ar » (espaces insécables : le montant ne se coupe jamais). */
export function formatAr(amount: number): string {
  return `${integer.format(Math.round(amount))} Ar`;
}

export function formatInt(n: number): string {
  return integer.format(Math.round(n));
}

/** Date ISO « 2027-01-08 » → « 8 janvier 2027 » (sans décalage de fuseau). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return longDate.format(new Date(y ?? 1970, (m ?? 1) - 1, d ?? 1));
}

export function formatShortDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return shortDate.format(new Date(y ?? 1970, (m ?? 1) - 1, d ?? 1));
}

/** 0.923 → « 92 % » */
export function formatPct(ratio: number): string {
  return `${Math.round(ratio * 100)} %`;
}

export function firstName(fullName: string): string {
  return fullName.split(" ")[0] ?? fullName;
}
