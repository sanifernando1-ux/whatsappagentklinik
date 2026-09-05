import React, { useEffect, useState } from "react";
import {
  MessagesSquare, CalendarCheck, Bot, Activity, TrendingUp,
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
  BarChart, Bar,
} from "recharts";
import api from "../lib/api";

function Stat({ icon: Icon, label, value, sub, tone }) {
  const tones = {
    blue: "bg-kf-blueLight text-kf-blueDark",
    orange: "bg-orange-50 text-kf-orangeDark",
    green: "bg-emerald-50 text-emerald-600",
    slate: "bg-slate-100 text-slate-600",
  };
  return (
    <div className="card p-5" data-testid={`stat-${label}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-extrabold text-kf-ink">{value}</p>
          {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
        </div>
        <div className={`grid h-12 w-12 place-items-center rounded-xl ${tones[tone]}`}>
          <Icon size={22} />
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [s, setS] = useState(null);

  useEffect(() => {
    const load = () => api.get("/dashboard/stats").then((r) => setS(r.data)).catch(() => {});
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  if (!s) return <div className="text-slate-400">Memuat statistik…</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat icon={MessagesSquare} label="Total Percakapan" value={s.conversations.total} sub={`${s.conversations.active} aktif · ${s.conversations.handoff} handoff`} tone="blue" />
        <Stat icon={CalendarCheck} label="Janji Temu Hari Ini" value={s.appointments.today} sub={`${s.appointments.total} total sepanjang waktu`} tone="orange" />
        <Stat icon={Bot} label="AI Containment Rate" value={`${s.containment_rate}%`} sub="Target ≥ 70%" tone="green" />
        <Stat icon={Activity} label="Total Pesan" value={s.messages_total} sub="AI + Pasien + Staf" tone="slate" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-kf-blue" />
            <h3 className="font-bold text-kf-ink">Aktivitas 7 Hari Terakhir</h3>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={s.trend} margin={{ left: -20, right: 8 }}>
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0B6FB8" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#0B6FB8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f6" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: "#94a3b8" }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 13 }} />
              <Area type="monotone" dataKey="messages" name="Pesan" stroke="#0B6FB8" strokeWidth={2.5} fill="url(#g1)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5">
          <h3 className="mb-4 font-bold text-kf-ink">Distribusi Intent</h3>
          {s.intent_distribution.length === 0 ? (
            <p className="py-16 text-center text-sm text-slate-400">Belum ada data intent</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={s.intent_distribution} margin={{ left: -20, right: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f6" vertical={false} />
                <XAxis dataKey="intent" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} interval={0} angle={-25} textAnchor="end" height={60} />
                <YAxis tick={{ fontSize: 12, fill: "#94a3b8" }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 13 }} />
                <Bar dataKey="count" name="Jumlah" fill="#F58220" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
