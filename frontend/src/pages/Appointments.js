import React, { useEffect, useState } from "react";
import { CalendarDays, Plus, Check, X, Clock, BellRing } from "lucide-react";
import api from "../lib/api";

const STATUS = {
  pending: "bg-amber-50 text-amber-600",
  confirmed: "bg-emerald-50 text-emerald-600",
  cancelled: "bg-red-50 text-red-500",
  completed: "bg-slate-100 text-slate-500",
};
const SERVICE = { umum: "Umum", lab: "Laboratorium", farmasi: "Farmasi", vaksinasi: "Vaksinasi" };

export default function Appointments() {
  const [appts, setAppts] = useState([]);
  const [status, setStatus] = useState("all");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ patient_name: "", patient_phone: "", service_type: "umum", appointment_date: "", appointment_time: "09:00" });

  const load = () => api.get("/appointments", { params: { status } }).then((r) => setAppts(r.data)).catch(() => {});
  useEffect(() => { load(); }, [status]);

  const [remMsg, setRemMsg] = useState("");
  const sendReminders = async () => {
    setRemMsg("Mengirim…");
    try {
      const r = await api.post("/appointments/send-reminders");
      setRemMsg(r.data.skipped ? "Pengingat nonaktif di Pengaturan." : `Terkirim ${r.data.sent} dari ${r.data.total_due} pengingat H-1.`);
    } catch { setRemMsg("Gagal mengirim pengingat."); }
    setTimeout(() => setRemMsg(""), 5000);
  };

  const setStat = async (id, s) => { await api.patch(`/appointments/${id}`, { status: s }); load(); };
  const create = async (e) => {
    e.preventDefault();
    await api.post("/appointments", form);
    setShowForm(false);
    setForm({ patient_name: "", patient_phone: "", service_type: "umum", appointment_date: "", appointment_time: "09:00" });
    load();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1 rounded-lg bg-white p-1 shadow-card">
          {["all", "pending", "confirmed", "cancelled", "completed"].map((f) => (
            <button key={f} onClick={() => setStatus(f)} data-testid={`appt-filter-${f}`}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize transition ${status === f ? "bg-kf-blueLight text-kf-blueDark" : "text-slate-500 hover:bg-slate-50"}`}>
              {f === "all" ? "Semua" : f}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          {remMsg && <span className="text-xs font-semibold text-kf-blue" data-testid="reminder-msg">{remMsg}</span>}
          <button className="btn-ghost" onClick={sendReminders} data-testid="send-reminders-btn"><BellRing size={18} /> Kirim Pengingat H-1</button>
          <button className="btn-primary" onClick={() => setShowForm(true)} data-testid="add-appt-btn"><Plus size={18} /> Tambah Janji Temu</button>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs font-bold uppercase text-slate-400">
              <tr>
                <th className="px-4 py-3">Pasien</th>
                <th className="px-4 py-3">Layanan</th>
                <th className="px-4 py-3">Tanggal & Jam</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {appts.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-12 text-center text-slate-400"><CalendarDays className="mx-auto mb-2 text-slate-200" size={40} />Belum ada janji temu</td></tr>
              ) : appts.map((a) => (
                <tr key={a.id} className="border-t border-slate-50" data-testid={`appt-row-${a.id}`}>
                  <td className="px-4 py-3">
                    <p className="font-semibold text-kf-ink">{a.patient_name}</p>
                    <p className="text-xs text-slate-400">{a.patient_phone}</p>
                  </td>
                  <td className="px-4 py-3">{SERVICE[a.service_type] || a.service_type}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5"><Clock size={14} className="text-slate-400" />{a.appointment_date} · {a.appointment_time}</div>
                  </td>
                  <td className="px-4 py-3"><span className={`badge ${STATUS[a.status]}`}>{a.status}</span></td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      {a.status !== "completed" && <button onClick={() => setStat(a.id, "completed")} title="Selesai" className="rounded-md p-1.5 text-emerald-600 hover:bg-emerald-50" data-testid={`complete-${a.id}`}><Check size={16} /></button>}
                      {a.status !== "cancelled" && <button onClick={() => setStat(a.id, "cancelled")} title="Batalkan" className="rounded-md p-1.5 text-red-500 hover:bg-red-50" data-testid={`cancel-${a.id}`}><X size={16} /></button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" onClick={() => setShowForm(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={create} className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl" data-testid="appt-form">
            <h3 className="mb-4 text-lg font-bold text-kf-ink">Tambah Janji Temu</h3>
            <div className="space-y-3">
              <div><label className="label">Nama Pasien</label><input required className="input" value={form.patient_name} onChange={(e) => setForm({ ...form, patient_name: e.target.value })} data-testid="form-name" /></div>
              <div><label className="label">No. Telepon</label><input required className="input" value={form.patient_phone} onChange={(e) => setForm({ ...form, patient_phone: e.target.value })} data-testid="form-phone" /></div>
              <div><label className="label">Layanan</label>
                <select className="input" value={form.service_type} onChange={(e) => setForm({ ...form, service_type: e.target.value })} data-testid="form-service">
                  <option value="umum">Umum</option><option value="lab">Laboratorium</option><option value="farmasi">Farmasi</option><option value="vaksinasi">Vaksinasi</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Tanggal</label><input required type="date" className="input" value={form.appointment_date} onChange={(e) => setForm({ ...form, appointment_date: e.target.value })} data-testid="form-date" /></div>
                <div><label className="label">Jam</label><input required type="time" className="input" value={form.appointment_time} onChange={(e) => setForm({ ...form, appointment_time: e.target.value })} data-testid="form-time" /></div>
              </div>
            </div>
            <div className="mt-5 flex gap-2">
              <button type="button" className="btn-ghost flex-1" onClick={() => setShowForm(false)}>Batal</button>
              <button type="submit" className="btn-primary flex-1" data-testid="form-submit">Simpan</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
