import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Connection from "./pages/Connection";
import Conversations from "./pages/Conversations";
import Appointments from "./pages/Appointments";
import Knowledge from "./pages/Knowledge";
import Workflow from "./pages/Workflow";
import Settings from "./pages/Settings";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">Memuat…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/*"
            element={
              <Protected>
                <Layout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/koneksi" element={<Connection />} />
                    <Route path="/percakapan" element={<Conversations />} />
                    <Route path="/janji-temu" element={<Appointments />} />
                    <Route path="/knowledge" element={<Knowledge />} />
                    <Route path="/workflow" element={<Workflow />} />
                    <Route path="/pengaturan" element={<Settings />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Layout>
              </Protected>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
