/** Routes de l'application. Toutes les pages sauf la connexion exigent d'être connecté. */
import type { ReactElement } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { Spinner } from "./components/ui";
import { STEPS } from "./lib/steps";
import { CopilotPage } from "./pages/CopilotPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ProjectCopilotPage } from "./pages/ProjectCopilotPage";
import { PlanningPage } from "./pages/PlanningPage";
import { ScopePage } from "./pages/ScopePage";
import { TeamPage } from "./pages/TeamPage";
import { LoginPage } from "./pages/LoginPage";
import { ProjectPlaceholderPage, SimplePlaceholderPage } from "./pages/ProjectPlaceholderPage";

function RequireAuth({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Ouverture de la session…" />
      </div>
    );
  }
  if (!user) return <Navigate to="/connexion" replace state={{ from: location.pathname }} />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/connexion" element={<LoginPage />} />
      <Route path="/" element={<RequireAuth><DashboardPage /></RequireAuth>} />
      <Route path="/copilote" element={<RequireAuth><CopilotPage /></RequireAuth>} />
      <Route path="/projets/:projectId/copilote" element={<RequireAuth><ProjectCopilotPage /></RequireAuth>} />
      <Route path="/projets/:projectId/perimetre" element={<RequireAuth><ScopePage /></RequireAuth>} />
      <Route path="/projets/:projectId/equipe" element={<RequireAuth><TeamPage /></RequireAuth>} />
      <Route path="/projets/:projectId/planning" element={<RequireAuth><PlanningPage /></RequireAuth>} />
      {STEPS.filter((s) => !["copilote", "perimetre", "equipe", "planning"].includes(s.key)).map((s) => (
        <Route
          key={s.key}
          path={`/projets/:projectId/${s.key}`}
          element={<RequireAuth><ProjectPlaceholderPage step={s.key} /></RequireAuth>}
        />
      ))}
      <Route path="/admin/benchmark" element={<RequireAuth><SimplePlaceholderPage title="Comparaison des méthodes" /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
