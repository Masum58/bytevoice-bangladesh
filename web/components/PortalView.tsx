"use client";

import React, { useEffect, useState } from "react";
import {
  CallDetail,
  CallSummary,
  PortalStats,
  AppointmentItem,
  CallbackItem,
  getPortalStats,
  getPortalCalls,
  getPortalCallDetail,
  getPortalAppointments,
  getPortalCallbacks,
  loginPortal,
  getClinicInfo,
} from "@/lib/api";

interface Props {
  onClose: () => void;
}

export default function PortalView({ onClose }: Props) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [loginError, setLoginError] = useState("");

  const [activeTab, setActiveTab] = useState<"calls" | "appointments" | "callbacks" | "clinic">("calls");
  const [stats, setStats] = useState<PortalStats | null>(null);

  // Calls state
  const [calls, setCalls] = useState<CallSummary[]>([]);
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [callDetail, setCallDetail] = useState<CallDetail | null>(null);
  const [callDetailLoading, setCallDetailLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");

  // Appointments state
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);

  // Callbacks state
  const [callbacks, setCallbacks] = useState<CallbackItem[]>([]);

  // Clinic settings state
  const [clinicData, setClinicData] = useState<any>(null);

  const [loading, setLoading] = useState(true);

  // Fetch initial portal data
  const loadData = async () => {
    setLoading(true);
    try {
      const [statsData, callsData, apptsData, cbData, clinicInfo] = await Promise.all([
        getPortalStats().catch(() => null),
        getPortalCalls(0, 50, statusFilter, searchTerm).catch(() => ({ total: 0, calls: [] })),
        getPortalAppointments().catch(() => ({ total: 0, appointments: [] })),
        getPortalCallbacks().catch(() => []),
        getClinicInfo().catch(() => null),
      ]);
      setStats(statsData);
      setCalls(callsData.calls);
      setAppointments(apptsData.appointments);
      setCallbacks(cbData);
      setClinicData(clinicInfo);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isLoggedIn) {
      loadData();
    }
  }, [isLoggedIn, statusFilter, searchTerm]);

  // Load single call detail when clicked
  const handleSelectCall = async (id: string) => {
    setSelectedCallId(id);
    setCallDetailLoading(true);
    try {
      const detail = await getPortalCallDetail(id);
      setCallDetail(detail);
    } catch (err) {
      console.error(err);
    } finally {
      setCallDetailLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError("");
    try {
      await loginPortal(username, password);
      setIsLoggedIn(true);
    } catch (err: any) {
      setLoginError(err.message || "Login failed");
    }
  };

  // If not logged in, render reviewer login screen
  if (!isLoggedIn) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
        <div className="w-full max-w-md rounded-2xl border border-white/20 bg-slate-900/90 p-8 shadow-2xl">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-white tracking-wide">Staff Portal Login</h2>
            <p className="text-xs text-emerald-400 mt-1 font-mono">Dhaka Dental Care — Reviewer Access</p>
          </div>
          {loginError && (
            <div className="mb-4 rounded-lg bg-rose-500/20 border border-rose-500/40 p-3 text-xs text-rose-300">
              {loginError}
            </div>
          )}
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">Username / Email</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-sm text-white focus:border-emerald-500 focus:outline-none"
                placeholder="admin"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-sm text-white focus:border-emerald-500 focus:outline-none"
                placeholder="admin123"
              />
            </div>
            <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 p-2.5 text-xs text-emerald-300">
              💡 Reviewer Hint: Default demo credentials are <b>admin</b> / <b>admin123</b>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 rounded-lg border border-slate-700 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 rounded-lg bg-emerald-600 py-2.5 text-sm font-semibold text-white shadow-lg hover:bg-emerald-500"
              >
                Sign In
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Navigation */}
      <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-900/80 px-6 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 shadow-md">
            🦷
          </div>
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              ByteVoice Staff Portal
              <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/30">
                Dhaka Dental Care
              </span>
            </h1>
            <p className="text-[11px] text-slate-400">Clinical Voice Activity & Appointment Management</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-slate-400">
            Logged in as: <span className="font-semibold text-white">admin</span>
          </span>
          <button
            onClick={loadData}
            title="Refresh Data"
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700 hover:text-white"
          >
            ↻ Refresh
          </button>
          <button
            onClick={() => setIsLoggedIn(false)}
            title="Sign Out"
            className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-300 hover:bg-rose-500/20"
          >
            Sign Out
          </button>
          <button
            onClick={onClose}
            className="rounded-lg bg-slate-800 px-3.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700"
          >
            ✕ Close Portal
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Tabs */}
        <aside className="w-56 border-r border-slate-800 bg-slate-900/50 p-4 space-y-1">
          <button
            onClick={() => { setActiveTab("calls"); setSelectedCallId(null); }}
            className={`flex w-full items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-medium transition ${
              activeTab === "calls"
                ? "bg-emerald-600 text-white shadow-md shadow-emerald-900/30"
                : "text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            <span>📞</span> All Calls (কলসমূহ)
          </button>
          <button
            onClick={() => { setActiveTab("appointments"); setSelectedCallId(null); }}
            className={`flex w-full items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-medium transition ${
              activeTab === "appointments"
                ? "bg-emerald-600 text-white shadow-md shadow-emerald-900/30"
                : "text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            <span>📅</span> Appointments (বুকিং)
          </button>
          <button
            onClick={() => { setActiveTab("callbacks"); setSelectedCallId(null); }}
            className={`flex w-full items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-medium transition ${
              activeTab === "callbacks"
                ? "bg-emerald-600 text-white shadow-md shadow-emerald-900/30"
                : "text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            <span>🔔</span> Follow-up Callbacks
          </button>
          <button
            onClick={() => { setActiveTab("clinic"); setSelectedCallId(null); }}
            className={`flex w-full items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-medium transition ${
              activeTab === "clinic"
                ? "bg-emerald-600 text-white shadow-md shadow-emerald-900/30"
                : "text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            <span>🏥</span> Clinic Configuration
          </button>
        </aside>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-950">
          {/* Quick Metrics Bar */}
          {stats && (
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <span className="text-xs uppercase tracking-wider text-slate-400">Total Calls Handled</span>
                <p className="text-2xl font-bold text-white mt-1">{stats.total_calls}</p>
                <span className="text-[11px] text-emerald-400">100% Bangla Voice Receptionist</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <span className="text-xs uppercase tracking-wider text-slate-400">Appointments Booked</span>
                <p className="text-2xl font-bold text-emerald-400 mt-1">{stats.total_appointments}</p>
                <span className="text-[11px] text-slate-400">Grounded slot confirmation</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <span className="text-xs uppercase tracking-wider text-slate-400">General Enquiries</span>
                <p className="text-2xl font-bold text-cyan-400 mt-1">{stats.enquiry_calls}</p>
                <span className="text-[11px] text-slate-400">Pricing, hours, directions</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <span className="text-xs uppercase tracking-wider text-slate-400">Staff Callbacks Needed</span>
                <p className="text-2xl font-bold text-amber-400 mt-1">{stats.pending_callbacks}</p>
                <span className="text-[11px] text-slate-400">Urgent/out-of-scope follow-ups</span>
              </div>
            </div>
          )}

          {/* TAB 1: ALL CALLS */}
          {activeTab === "calls" && (
            <div className="space-y-4">
              {/* Filter and Search Bar */}
              <div className="flex items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/40 p-3">
                <div className="flex gap-2">
                  {["all", "booked", "enquiry", "follow_up_needed"].map((st) => (
                    <button
                      key={st}
                      onClick={() => setStatusFilter(st)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition ${
                        statusFilter === st
                          ? "bg-slate-200 text-slate-900 font-semibold"
                          : "text-slate-400 hover:bg-slate-800 hover:text-white"
                      }`}
                    >
                      {st.replace("_", " ")}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  placeholder="Search by caller name, phone or note..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-72 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                />
              </div>

              {/* Calls Table */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">Caller</th>
                      <th className="py-3 px-4">Phone</th>
                      <th className="py-3 px-4">Date & Time</th>
                      <th className="py-3 px-4">Duration</th>
                      <th className="py-3 px-4">Outcome</th>
                      <th className="py-3 px-4">Visit Reason / Summary</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-200">
                    {calls.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-slate-500">
                          No calls match the current filter.
                        </td>
                      </tr>
                    ) : (
                      calls.map((call) => (
                        <tr
                          key={call.id}
                          className="hover:bg-slate-800/40 transition cursor-pointer"
                          onClick={() => handleSelectCall(call.id)}
                        >
                          <td className="py-3 px-4 font-semibold text-white">{call.caller_name}</td>
                          <td className="py-3 px-4 font-mono text-slate-300">{call.caller_phone}</td>
                          <td className="py-3 px-4 text-slate-400">
                            {new Date(call.started_at).toLocaleString("en-US", {
                              month: "short",
                              day: "numeric",
                              hour: "numeric",
                              minute: "2-digit",
                              hour12: true,
                            })}
                          </td>
                          <td className="py-3 px-4">{call.duration_s}s</td>
                          <td className="py-3 px-4">
                            <span
                              className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
                                call.status === "booked"
                                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                  : call.status === "enquiry"
                                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                                  : call.status === "follow_up_needed"
                                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                                  : "bg-slate-700/50 text-slate-400"
                              }`}
                            >
                              {call.status.replace("_", " ")}
                            </span>
                          </td>
                          <td className="py-3 px-4 max-w-xs truncate text-slate-400">{call.summary}</td>
                          <td className="py-3 px-4 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectCall(call.id);
                              }}
                              className="rounded-lg bg-emerald-600/20 border border-emerald-500/40 px-2.5 py-1 text-[11px] font-medium text-emerald-300 hover:bg-emerald-600 hover:text-white"
                            >
                              View Transcript 💬
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: APPOINTMENTS */}
          {activeTab === "appointments" && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow">
              <div className="p-4 border-b border-slate-800 flex justify-between items-center">
                <h3 className="font-semibold text-white">Confirmed Dental Appointments</h3>
                <span className="text-xs text-slate-400">Total: {appointments.length}</span>
              </div>
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Patient Name</th>
                    <th className="py-3 px-4">Contact Phone</th>
                    <th className="py-3 px-4">Slot Date & Time</th>
                    <th className="py-3 px-4">Service Required</th>
                    <th className="py-3 px-4">Assigned Doctor</th>
                    <th className="py-3 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-200">
                  {appointments.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-800/40">
                      <td className="py-3 px-4 font-semibold text-white">{a.patient_name}</td>
                      <td className="py-3 px-4 font-mono text-slate-300">{a.patient_phone}</td>
                      <td className="py-3 px-4 font-medium text-emerald-400">{a.slot_datetime}</td>
                      <td className="py-3 px-4 text-slate-300">{a.service_name}</td>
                      <td className="py-3 px-4 text-slate-400">{a.doctor_name}</td>
                      <td className="py-3 px-4">
                        <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/30">
                          {a.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 3: CALLBACKS */}
          {activeTab === "callbacks" && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow">
              <div className="p-4 border-b border-slate-800">
                <h3 className="font-semibold text-white">Urgent Receptionist Callback Requests</h3>
                <p className="text-xs text-slate-400 mt-0.5">Calls escalated by AI for human handover or medical emergencies.</p>
              </div>
              <div className="divide-y divide-slate-800">
                {callbacks.length === 0 ? (
                  <p className="p-6 text-center text-slate-500 text-xs">No pending callbacks right now.</p>
                ) : (
                  callbacks.map((cb) => (
                    <div key={cb.id} className="p-4 flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-sm">{cb.patient_name}</span>
                          <span className="text-xs font-mono text-slate-400">({cb.patient_phone})</span>
                          <span className="rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold uppercase text-amber-400 border border-amber-500/30">
                            {cb.status}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 mt-1.5 bg-slate-800/40 p-2 rounded-lg border border-slate-700/40">
                          {cb.reason}
                        </p>
                      </div>
                      <span className="text-[11px] text-slate-500">
                        {new Date(cb.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 4: CLINIC CONFIGURATION */}
          {activeTab === "clinic" && clinicData && (
            <div className="space-y-6">
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
                <h3 className="font-bold text-white text-base mb-1">{clinicData.clinic_name}</h3>
                <p className="text-xs text-slate-300">📍 {clinicData.address}</p>
                <p className="text-xs text-slate-400 mt-1">🕒 {clinicData.opening_hours}</p>
                <p className="text-xs text-slate-400">📞 Phone: {clinicData.phone}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400 mb-3">
                    Verified Services & Fees
                  </h4>
                  <div className="space-y-2 text-xs">
                    {clinicData.services?.map((s: any, idx: number) => (
                      <div key={idx} className="flex justify-between border-b border-slate-800/60 pb-1.5">
                        <span className="text-slate-200">{s.name} ({s.name_bn})</span>
                        <span className="font-bold text-emerald-400">{s.fee}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-400 mb-3">
                    Consulting Dental Specialists
                  </h4>
                  <div className="space-y-3 text-xs">
                    {clinicData.doctors?.map((d: any, idx: number) => (
                      <div key={idx} className="border-b border-slate-800/60 pb-2">
                        <p className="font-bold text-white">{d.name} <span className="text-[11px] text-slate-400">({d.degrees})</span></p>
                        <p className="text-cyan-300 text-[11px]">{d.specialty}</p>
                        <p className="text-slate-400 text-[10px] mt-0.5">Availability: {d.available_days}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* CALL DETAIL & TRANSCRIPT DRAWER / MODAL */}
      {selectedCallId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-6">
          <div className="flex h-[88vh] w-full max-w-4xl flex-col rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4 bg-slate-900/80">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  Call Record & Dialogue Transcript
                  <span className="text-xs font-mono text-slate-400">#{selectedCallId.slice(0, 14)}...</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Patient: <span className="text-white font-medium">{callDetail?.caller_name}</span> ({callDetail?.caller_phone})
                </p>
              </div>
              <button
                onClick={() => setSelectedCallId(null)}
                className="rounded-lg bg-slate-800 p-2 text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex flex-1 overflow-hidden">
              {/* Left Column: Extraction & Appointment Summary */}
              <div className="w-80 border-r border-slate-800 p-5 overflow-y-auto space-y-4 bg-slate-950/40 text-xs">
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Call Outcome</span>
                  <p className="mt-1 font-semibold text-emerald-400 capitalize">{callDetail?.status.replace("_", " ")}</p>
                  <p className="text-slate-400 text-[11px] mt-0.5">Duration: {callDetail?.duration_s} seconds</p>
                </div>

                {callDetail?.extraction && (
                  <div className="space-y-3 pt-3 border-t border-slate-800">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">AI Clinical Extraction</span>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Reason for Visit:</span>
                      <p className="font-medium text-white">{callDetail.extraction.reason_for_visit || "General Checkup"}</p>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Preferred Time:</span>
                      <p className="font-medium text-cyan-300">{callDetail.extraction.preferred_datetime || "Flexible"}</p>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Urgency:</span>
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                        callDetail.extraction.urgency === "emergency" ? "bg-rose-500/20 text-rose-400" : "bg-emerald-500/20 text-emerald-400"
                      }`}>
                        {callDetail.extraction.urgency}
                      </span>
                    </div>
                  </div>
                )}

                {callDetail?.appointments && callDetail.appointments.length > 0 && (
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3 pt-3">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-400">Confirmed Booking</span>
                    <p className="font-bold text-white mt-1">{callDetail.appointments[0].service}</p>
                    <p className="text-emerald-300 font-mono text-[11px] mt-0.5">🕒 {callDetail.appointments[0].slot}</p>
                    <p className="text-slate-400 text-[10px] mt-1">👨‍⚕️ {callDetail.appointments[0].doctor}</p>
                  </div>
                )}
              </div>

              {/* Right Column: Full Turn-by-Turn Transcript */}
              <div className="flex-1 p-6 overflow-y-auto space-y-4 bg-slate-900/30">
                <h4 className="text-xs uppercase font-bold tracking-wider text-slate-400 mb-2">
                  Verbatim Turn-by-Turn Dialogue (Bangla & Translation)
                </h4>

                {callDetailLoading ? (
                  <p className="text-xs text-slate-500 text-center py-10">Loading dialogue transcript...</p>
                ) : !callDetail?.transcripts || callDetail.transcripts.length === 0 ? (
                  <p className="text-xs text-slate-500 text-center py-10">No transcript turns logged for this call.</p>
                ) : (
                  callDetail.transcripts.map((t, idx) => (
                    <div
                      key={idx}
                      className={`flex gap-3 text-xs ${
                        t.speaker === "ai" ? "justify-start" : "justify-end"
                      }`}
                    >
                      {t.speaker === "ai" && (
                        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-xs text-white">
                          🤖
                        </div>
                      )}
                      <div
                        className={`max-w-[80%] rounded-xl p-3 ${
                          t.speaker === "ai"
                            ? "bg-slate-800 text-slate-100 border border-slate-700/60"
                            : "bg-emerald-700/30 text-emerald-100 border border-emerald-500/40"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-4 mb-1">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                            {t.speaker === "ai" ? "AI Receptionist (ঢাকা ডেন্টাল)" : "Patient (রোগী)"}
                          </span>
                        </div>
                        <p className="text-sm font-medium leading-relaxed">{t.text_bn}</p>
                        {t.text_en && (
                          <p className="mt-1 text-[11px] text-slate-400 italic border-t border-slate-700/40 pt-1">
                            {t.text_en}
                          </p>
                        )}
                      </div>
                      {t.speaker !== "ai" && (
                        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-cyan-700 text-xs text-white">
                          👤
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

