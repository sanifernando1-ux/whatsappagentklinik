import React, { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard, QrCode, MessagesSquare, CalendarDays,
  BookOpen, Workflow as WorkflowIcon, Settings as SettingsIcon,
  LogOut, Menu, X, Bell, Plus,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import api from "../lib/api";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/koneksi", label: "Koneksi WhatsApp", icon: QrCode },
  { to: "/percakapan", label: "Percakapan", icon: MessagesSquare },
  { to: "/janji-temu", label: "Janji Temu", icon: CalendarDays },
  { to: "/knowledge", label: "Knowledge Base", icon: BookOpen },
  { to: "/workflow", label: "Alur AI (Workflow)", icon: WorkflowIcon },
  { to: "/pengaturan", label: "Pengaturan", icon: SettingsIcon },
];

function Brand() {
  return (
    <div className="flex items-center gap-3" data-testid="app-brand">
      <div className="relative grid h-10 w-10 place-items-center rounded-xl bg-kf-blue text-white shadow-card">
        <Plus size={20} strokeWidth={3} />
        <span className="absolute -bottom-1 -right-1 grid h-4 w-4 place-items-center rounded-md bg-kf-orange text-[8px] font-extrabold text-white">KF</span>
      </div>
      <div className="leading-tight">
        <p className="text-sm font-extrabold text-kf-ink">Klinik KF Sepinggan</p>
        <p className="text-[11px] font-semibold text-kf-blue">WhatsApp AI Agent</p>
      </div>
    </div>
  );
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [notifs, setNotifs] = useState([]);
  const [showNotif, setShowNotif] = useState(false);
  const loc = useLocation();

  useEffect(() => { setOpen(false); }, [loc.pathname]);

  const loadNotifs = () => api.get("/notifications").then((r) => setNotifs(r.data)).catch(() => {});
  useEffect(() => {
    loadNotifs();
    const t = setInterval(loadNotifs, 8000);
    return () => clearInterval(t);
  }, []);

  const markAll = async () => { await api.post("/notifications/read-all"); setNotifs([]); setShowNotif(false); };

  const SidebarInner = (
    <div className="flex h-full flex-col">
      <div className="px-5 py-5 border-b border-slate-100"><Brand /></div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            data-testid={`nav-${n.to === "/" ? "dashboard" : n.to.slice(1)}`}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-semibold transition-colors ${
                isActive ? "bg-kf-blueLight text-kf-blueDark" : "text-slate-500 hover:bg-slate-50 hover:text-kf-ink"
              }`
            }
          >
            <n.icon size={19} />
            {n.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-slate-100 p-3">
        <button onClick={logout} data-testid="logout-btn" className="flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-semibold text-slate-500 transition-colors hover:bg-red-50 hover:text-red-600">
          <LogOut size={19} /> Keluar
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-kf-panel">
      {/* Desktop sidebar */}
      <aside className="hidden w-72 shrink-0 border-r border-slate-100 bg-white lg:block">{SidebarInner}</aside>

      {/* Mobile sidebar */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/30" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-72 bg-white shadow-xl">{SidebarInner}</aside>
        </div>
      )}

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-100 bg-white px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button className="lg:hidden" onClick={() => setOpen(true)} data-testid="mobile-menu-btn"><Menu /></button>
            <h1 className="text-base font-bold text-kf-ink">
              {NAV.find((n) => (n.end ? loc.pathname === n.to : loc.pathname.startsWith(n.to) && n.to !== "/"))?.label || "Dashboard"}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <button onClick={() => setShowNotif((s) => !s)} data-testid="notif-btn" className="relative grid h-10 w-10 place-items-center rounded-lg text-slate-500 hover:bg-slate-50">
                <Bell size={20} />
                {notifs.length > 0 && (
                  <span className="absolute right-1.5 top-1.5 grid h-4 min-w-4 place-items-center rounded-full bg-kf-orange px-1 text-[10px] font-bold text-white">{notifs.length}</span>
                )}
              </button>
              {showNotif && (
                <div className="absolute right-0 top-12 z-30 w-80 rounded-xl border border-slate-100 bg-white shadow-xl" data-testid="notif-dropdown">
                  <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                    <span className="text-sm font-bold">Notifikasi</span>
                    {notifs.length > 0 && <button onClick={markAll} className="text-xs font-semibold text-kf-blue">Tandai dibaca</button>}
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {notifs.length === 0 ? (
                      <p className="px-4 py-6 text-center text-sm text-slate-400">Tidak ada notifikasi baru</p>
                    ) : notifs.map((n) => (
                      <div key={n.id} className="border-b border-slate-50 px-4 py-3">
                        <p className="text-sm font-semibold text-kf-ink">🔔 {n.patient_name}</p>
                        <p className="text-xs text-slate-500">{n.message}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2.5">
              <div className="grid h-9 w-9 place-items-center rounded-full bg-kf-blueLight text-sm font-bold text-kf-blueDark">
                {(user?.name || user?.username || "A").charAt(0).toUpperCase()}
              </div>
              <div className="hidden text-right sm:block">
                <p className="text-sm font-bold leading-tight text-kf-ink">{user?.name || user?.username}</p>
                <p className="text-[11px] capitalize text-slate-400">{user?.role}</p>
              </div>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
