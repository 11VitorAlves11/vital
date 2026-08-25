import { Suspense, lazy } from "react";
import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { ErrorState } from "./components/ui/ErrorState";
import { Skeleton } from "./components/ui/Skeleton";
import { useSession } from "./lib/session";
import { Body } from "./pages/Body";
import { Dashboard } from "./pages/Dashboard";
import { Interventions } from "./pages/Interventions";
import { Login } from "./pages/Login";
import { Photos } from "./pages/Photos";
import { Profile } from "./pages/Profile";
import { ReportDetail } from "./pages/ReportDetail";
import { Reports } from "./pages/Reports";

// Recharts is by far the heaviest dependency and only these two routes need it,
// so it stays out of the bundle the dashboard loads on a phone.
const BiomarkerDetail = lazy(() =>
  import("./pages/BiomarkerDetail").then((module) => ({ default: module.BiomarkerDetail })),
);
const BodyMetricDetail = lazy(() =>
  import("./pages/BodyMetricDetail").then((module) => ({ default: module.BodyMetricDetail })),
);

function RequireSession({ children }: { children: ReactNode }) {
  const { user, loading, error, refresh } = useSession();
  const location = useLocation();

  if (loading) return <Skeleton className="p-8" lines={6} />;
  // A session we could not check is not a session that does not exist: bouncing
  // to the login screen on a network blip reads as being signed out.
  if (error && !user) {
    return (
      <div className="p-8">
        <ErrorState onRetry={() => void refresh()} />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return (
    <AppShell>
      <Suspense fallback={<Skeleton lines={6} />}>{children}</Suspense>
    </AppShell>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireSession>
            <Dashboard />
          </RequireSession>
        }
      />
      <Route
        path="/biomarkers/:id"
        element={
          <RequireSession>
            <BiomarkerDetail />
          </RequireSession>
        }
      />
      <Route
        path="/reports"
        element={
          <RequireSession>
            <Reports />
          </RequireSession>
        }
      />
      <Route
        path="/reports/:id"
        element={
          <RequireSession>
            <ReportDetail />
          </RequireSession>
        }
      />
      <Route
        path="/interventions"
        element={
          <RequireSession>
            <Interventions />
          </RequireSession>
        }
      />
      <Route
        path="/body"
        element={
          <RequireSession>
            <Body />
          </RequireSession>
        }
      />
      <Route
        path="/body/:id"
        element={
          <RequireSession>
            <BodyMetricDetail />
          </RequireSession>
        }
      />
      <Route
        path="/photos"
        element={
          <RequireSession>
            <Photos />
          </RequireSession>
        }
      />
      <Route
        path="/profile"
        element={
          <RequireSession>
            <Profile />
          </RequireSession>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
