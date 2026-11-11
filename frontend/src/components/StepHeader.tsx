/** En-tête commun des étapes d'un projet : numéro d'étape, titre, sous-titre et actions. */
import type { ReactNode } from "react";

import { AlgoTag } from "./ui";

export function StepHeader({
  step,
  title,
  subtitle,
  algorithm,
  actions,
}: {
  step: string;
  title: string;
  subtitle: string;
  algorithm?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col justify-between gap-space-md md:flex-row md:items-end">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-label-md text-primary">{step}</span>
          {algorithm && <AlgoTag>{algorithm}</AlgoTag>}
        </div>
        <h2 className="mt-1 text-headline-lg-mobile tracking-tight text-on-surface md:text-headline-lg">{title}</h2>
        <p className="mt-1 max-w-3xl text-body-md text-on-surface-variant">{subtitle}</p>
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-space-sm">{actions}</div>}
    </div>
  );
}
