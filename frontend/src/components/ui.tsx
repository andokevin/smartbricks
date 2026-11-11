/** Composants de base du système de design SmartBricks (DESIGN.md). */
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";

import type { ProjectStatus } from "../api/types";
import { STATUS_LABEL, STEPS, stepState } from "../lib/steps";

export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

/** Icône Material Symbols (police embarquée). */
export function Icon({ name, className, filled }: { name: string; className?: string; filled?: boolean }) {
  return (
    <span aria-hidden="true" className={cx("material-symbols-outlined", filled && "icon-filled", className)}>
      {name}
    </span>
  );
}

type Variant = "primary" | "secondary" | "outline" | "ghost" | "success";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-primary-container text-on-primary hover:bg-primary shadow-card",
  secondary: "bg-surface-container text-primary hover:bg-surface-container-high",
  outline: "bg-transparent border-[1.5px] border-outline-variant text-on-surface hover:bg-surface-container-low",
  ghost: "bg-transparent text-primary hover:bg-surface-container-low",
  success: "bg-secondary text-on-secondary hover:opacity-95 shadow-card",
};

const BUTTON_BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-label-md transition-all " +
  "active:translate-y-px disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none " +
  "focus-visible:ring-2 focus-visible:ring-primary-container/30 min-h-10";

export function Button({
  variant = "primary",
  icon,
  iconRight,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; icon?: string; iconRight?: string }) {
  return (
    <button className={cx(BUTTON_BASE, VARIANTS[variant], className)} {...rest}>
      {icon && <Icon name={icon} className="text-[18px]" />}
      {children}
      {iconRight && <Icon name={iconRight} className="text-[18px]" />}
    </button>
  );
}

export function ButtonLink({
  to,
  variant = "primary",
  icon,
  iconRight,
  className,
  children,
}: {
  to: string;
  variant?: Variant;
  icon?: string;
  iconRight?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link to={to} className={cx(BUTTON_BASE, VARIANTS[variant], className)}>
      {icon && <Icon name={icon} className="text-[18px]" />}
      {children}
      {iconRight && <Icon name={iconRight} className="text-[18px]" />}
    </Link>
  );
}

/** Carte « brique » : fond blanc, coins de 12 px, ombre douce. */
export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cx("rounded-xl bg-surface-container-lowest shadow-card", className)}>{children}</div>;
}

const STATUS_STYLE: Record<ProjectStatus, string> = {
  DRAFT: "bg-surface-container-high text-on-surface-variant border-outline-variant",
  SCOPED: "bg-[#FEF3C7] text-[#B45309] border-[#FDE68A]",
  TEAM_SELECTED: "bg-[#E0F2FE] text-[#0369A1] border-[#BAE6FD]",
  PLANNED: "bg-[#D1FAE5] text-[#047857] border-[#A7F3D0]",
};

export function StatusBadge({ status }: { status: ProjectStatus }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-label-sm uppercase tracking-wide",
        STATUS_STYLE[status],
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {STATUS_LABEL[status]}
    </span>
  );
}

/** Progression « brique par brique » : 6 segments, un par étape du parcours. */
export function BrickProgress({ status, className }: { status: ProjectStatus; className?: string }) {
  return (
    <div className={cx("flex gap-1", className)} aria-label={`Progression : ${STATUS_LABEL[status]}`}>
      {STEPS.map((s, i) => {
        const state = stepState(status, i);
        return (
          <div
            key={s.key}
            title={s.label}
            className={cx(
              "h-2 flex-1 rounded-full",
              state === "done" && "bg-secondary",
              state === "current" && "bg-primary-container",
              state === "todo" && "bg-surface-container-highest",
            )}
          />
        );
      })}
    </div>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-start gap-3 rounded-xl bg-error-container p-space-md text-on-error-container">
      <Icon name="error" className="mt-0.5" />
      <p className="flex-1 text-body-md">{message}</p>
      {onRetry && (
        <button className="text-label-md underline" onClick={onRetry}>
          Réessayer
        </button>
      )}
    </div>
  );
}

export function Spinner({ label = "Chargement…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-space-xl text-on-surface-variant" role="status">
      <Icon name="progress_activity" className="animate-spin" />
      <span className="text-body-md">{label}</span>
    </div>
  );
}

/** Petite étiquette d'algorithme : rappelle au jury le numéro dans la liste du cours. */
export function AlgoTag({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-primary-fixed px-2.5 py-0.5 text-label-sm uppercase text-on-primary-fixed">
      <Icon name="function" className="text-[14px]" />
      {children}
    </span>
  );
}
