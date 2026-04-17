import { Navigate, Route, Routes } from "react-router-dom";

function Placeholder({ title }: { title: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Phase 2 agents will implement this page.
        </p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/flags" replace />} />
      <Route path="/login" element={<Placeholder title="Login" />} />
      <Route path="/signup" element={<Placeholder title="Signup" />} />
      <Route path="/flags" element={<Placeholder title="Flags" />} />
      <Route path="/flags/:id" element={<Placeholder title="Flag Detail" />} />
      <Route path="/chat" element={<Placeholder title="NL Chat" />} />
      <Route path="/analytics" element={<Placeholder title="Analytics" />} />
      <Route path="/audit" element={<Placeholder title="Audit" />} />
      <Route path="*" element={<Placeholder title="Not Found" />} />
    </Routes>
  );
}
