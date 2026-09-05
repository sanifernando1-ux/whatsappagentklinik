import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, LogIn, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      await login(username, password);
      nav("/");
    } catch (e) {
      setErr(e.response?.data?.detail || "Gagal masuk. Periksa kembali kredensial Anda.");
    } finally { setLoading(false); }
  };

  return (
    <div className="flex min-h-screen">
      <div className="hidden w-1/2 flex-col justify-between bg-kf-blue p-12 text-white lg:flex">
        <div className="flex items-center gap-3">
          <div className="relative grid h-11 w-11 place-items-center rounded-xl bg-white/15">
            <Plus size={22} strokeWidth={3} />
          </div>
          <div>
            <p className="font-extrabold">Klinik Kimia Farma Sepinggan</p>
            <p className="text-sm text-white/70">Balikpapan, Kalimantan Timur</p>
          </div>
        </div>
        <div>
          <h2 className="text-4xl font-extrabold leading-tight">WhatsApp<br />AI Agent</h2>
          <p className="mt-4 max-w-md text-white/80">
            Asisten digital empatik untuk menjawab pertanyaan pasien, menjadwalkan janji temu,
            dan mengeskalasi ke staf klinik secara otomatis 24/7.
          </p>
          <div className="mt-8 flex items-center gap-2 text-sm text-white/70">
            <ShieldCheck size={18} /> Data pasien terenkripsi & sesuai UU PDP
          </div>
        </div>
        <p className="text-xs text-white/50">© 2026 Tim Digital & IT KF Sepinggan</p>
      </div>

      <div className="flex w-full items-center justify-center bg-white p-6 lg:w-1/2">
        <form onSubmit={submit} className="w-full max-w-sm" data-testid="login-form">
          <div className="mb-8 lg:hidden">
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-kf-blue text-white"><Plus size={24} strokeWidth={3} /></div>
          </div>
          <h1 className="text-2xl font-extrabold text-kf-ink">Masuk ke Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Silakan masuk untuk mengelola agen AI klinik.</p>

          {err && <div className="mt-5 rounded-lg bg-red-50 px-4 py-3 text-sm font-medium text-red-600" data-testid="login-error">{err}</div>}

          <div className="mt-6">
            <label className="label">Username</label>
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} data-testid="login-username" autoFocus />
          </div>
          <div className="mt-4">
            <label className="label">Password</label>
            <input type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password" placeholder="••••••••" />
          </div>
          <button type="submit" disabled={loading} className="btn-primary mt-6 w-full" data-testid="login-submit">
            <LogIn size={18} /> {loading ? "Memproses…" : "Masuk"}
          </button>
        </form>
      </div>
    </div>
  );
}
