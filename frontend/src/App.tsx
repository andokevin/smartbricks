import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";

/** Réponse de GET /api/v1/health. */
interface Health {
  status: string;
  database: string;
  llm_provider: string;
}

type EtatApi =
  | { etat: "chargement" }
  | { etat: "ok"; donnees: Health }
  | { etat: "erreur"; message: string };

/** Page d'accueil provisoire (phase 1) : vérifie que l'API et la base répondent. */
function Accueil() {
  const [api, setApi] = useState<EtatApi>({ etat: "chargement" });

  useEffect(() => {
    fetch("/api/v1/health")
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        setApi({ etat: "ok", donnees: (await r.json()) as Health });
      })
      .catch((e: unknown) =>
        setApi({ etat: "erreur", message: e instanceof Error ? e.message : String(e) }),
      );
  }, []);

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-3xl font-bold text-blue-800">SmartBricks</h1>
      <p className="mt-2 text-slate-600">
        Du besoin flou du client au projet informatique réaliste.
      </p>

      <section className="mt-8 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-semibold text-slate-800">État du système</h2>
        {api.etat === "chargement" && <p className="mt-2 text-slate-500">Vérification…</p>}
        {api.etat === "ok" && (
          <ul className="mt-2 space-y-1 text-sm text-slate-700">
            <li>API : {api.donnees.status}</li>
            <li>Base de données : {api.donnees.database}</li>
            <li>Fournisseur LLM : {api.donnees.llm_provider}</li>
          </ul>
        )}
        {api.etat === "erreur" && (
          <p className="mt-2 text-sm text-red-700">API injoignable ({api.message}).</p>
        )}
      </section>
    </main>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Routes>
        <Route path="/" element={<Accueil />} />
      </Routes>
    </div>
  );
}
