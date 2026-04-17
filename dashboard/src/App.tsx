import * as React from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { useAuth } from "@/hooks/useAuth";
import LoginPage from "@/pages/auth/LoginPage";
import SignupPage from "@/pages/auth/SignupPage";
import FlagEditorPage from "@/pages/flags/FlagEditorPage";
import FlagsListPage from "@/pages/flags/FlagsListPage";
import SettingsPage from "@/pages/settings/SettingsPage";

// Agent H pages — lazy-loaded so missing files don't break the build.
const NLChatPage = React.lazy(() => import("@/pages/chat/NLChatPage"));
const AnalyticsOverviewPage = React.lazy(
  () => import("@/pages/analytics/AnalyticsOverviewPage")
);
const FlagAnalyticsPage = React.lazy(
  () => import("@/pages/analytics/FlagAnalyticsPage")
);
const AuditLogPage = React.lazy(() => import("@/pages/audit/AuditLogPage"));

function RootRedirect() {
  const { token } = useAuth();
  return <Navigate to={token ? "/flags" : "/login"} replace />;
}

function LazyPage({ children }: { children: React.ReactNode }) {
  return (
    <React.Suspense
      fallback={
        <div className="p-8 text-center text-sm text-muted-foreground">
          Loading…
        </div>
      }
    >
      <LazyErrorBoundary>{children}</LazyErrorBoundary>
    </React.Suspense>
  );
}

interface LazyErrorBoundaryState {
  error: Error | null;
}

class LazyErrorBoundary extends React.Component<
  { children: React.ReactNode },
  LazyErrorBoundaryState
> {
  state: LazyErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): LazyErrorBoundaryState {
    return { error };
  }

  render(): React.ReactNode {
    if (this.state.error) {
      return (
        <div className="p-8 text-center text-sm text-muted-foreground">
          This page isn&apos;t available yet.
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/flags" element={<FlagsListPage />} />
        <Route path="/flags/new" element={<FlagEditorPage />} />
        <Route path="/flags/:id" element={<FlagEditorPage />} />
        <Route
          path="/flags/:id/analytics"
          element={
            <LazyPage>
              <FlagAnalyticsPage />
            </LazyPage>
          }
        />
        <Route
          path="/chat"
          element={
            <LazyPage>
              <NLChatPage />
            </LazyPage>
          }
        />
        <Route
          path="/analytics"
          element={
            <LazyPage>
              <AnalyticsOverviewPage />
            </LazyPage>
          }
        />
        <Route
          path="/audit"
          element={
            <LazyPage>
              <AuditLogPage />
            </LazyPage>
          }
        />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route
        path="*"
        element={
          <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">
            Not found.
          </div>
        }
      />
    </Routes>
  );
}
