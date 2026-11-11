/** Connexion. Les comptes de démonstration sont proposés en un clic (fournis par le seed). */
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Button, ErrorBanner, Icon } from "../components/ui";

const DEMO_ACCOUNTS = [
  { label: "Cliente — Soa (Boutique Soa)", email: "client@smartbricks.mg", password: "demo1234", icon: "storefront" },
  { label: "Administrateur", email: "admin@smartbricks.mg", password: "admin1234", icon: "admin_panel_settings" },
];

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={from} replace />;

  async function submit(e?: FormEvent, account?: { email: string; password: string }) {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(account?.email ?? email, account?.password ?? password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const input =
    "w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2.5 text-body-md " +
    "focus:outline-none focus:ring-2 focus:ring-primary-container/20";

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4 py-space-xl">
      <div className="grid w-full max-w-4xl overflow-hidden rounded-xl bg-surface-container-lowest shadow-overlay md:grid-cols-2">
        {/* Présentation */}
        <div className="flex flex-col justify-between gap-space-lg bg-primary p-space-xl text-on-primary">
          <div className="flex items-center gap-space-sm">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-container">
              <Icon name="view_in_ar" />
            </span>
            <div>
              <div className="text-headline-sm font-bold">SmartBricks</div>
              <div className="text-label-sm uppercase tracking-wider text-primary-fixed">Cadrage agile</div>
            </div>
          </div>
          <div>
            <h1 className="text-headline-lg-mobile md:text-headline-lg">Du besoin flou au projet réaliste.</h1>
            <p className="mt-space-sm text-body-md text-primary-fixed">
              Décrivez votre idée au copilote : des algorithmes choisissent le périmètre, l'équipe, le planning et
              la tournée, en respectant votre budget en Ariary.
            </p>
          </div>
          <div className="flex gap-1" aria-hidden="true">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <span key={i} className={i < 4 ? "h-2 flex-1 rounded-full bg-secondary-fixed" : "h-2 flex-1 rounded-full bg-primary-container"} />
            ))}
          </div>
        </div>

        {/* Formulaire */}
        <div className="flex flex-col gap-space-lg p-space-xl">
          <div>
            <h2 className="text-headline-sm text-on-surface">Connexion</h2>
            <p className="text-body-md text-on-surface-variant">Accédez à vos projets.</p>
          </div>
          {error && <ErrorBanner message={error} />}
          <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-space-md">
            <label className="flex flex-col gap-1 text-label-md text-on-surface">
              Email
              <input className={input} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-label-md text-on-surface">
              Mot de passe
              <input
                className={input}
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <Button type="submit" disabled={busy} iconRight="arrow_forward">
              Se connecter
            </Button>
          </form>
          <div className="flex flex-col gap-space-sm">
            <span className="text-label-sm uppercase tracking-wider text-outline">Comptes de démonstration</span>
            {DEMO_ACCOUNTS.map((a) => (
              <button
                key={a.email}
                disabled={busy}
                onClick={() => void submit(undefined, a)}
                className="flex items-center gap-space-sm rounded-lg bg-surface-container-low px-space-md py-space-sm text-left hover:bg-surface-container disabled:opacity-50"
              >
                <Icon name={a.icon} className="text-primary" />
                <span className="flex-1">
                  <span className="block text-label-md text-on-surface">{a.label}</span>
                  <span className="block text-body-sm text-on-surface-variant">{a.email}</span>
                </span>
                <Icon name="login" className="text-outline" />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
