"use client";

import { useConversation, ConversationProvider } from "@elevenlabs/react";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import JobvisOrb from "@/components/JobvisOrb";
import PortalView from "@/components/PortalView";
import { completeCall, getConfig, getSessionStart, type Config } from "@/lib/api";
import type { OrbMode } from "@/lib/orbScene";
import { buildClientTools } from "@/lib/tools";

type TranscriptLine = { role: "you" | "ai" | "tool" | "system"; text: string; time: string };

function ByteVoiceLandingContent() {
  const [config, setConfig] = useState<Config | null>(null);
  const [error, setError] = useState<string>("");
  const [engaging, setEngaging] = useState(false);
  const [callLines, setCallLines] = useState<TranscriptLine[]>([]);
  const [activeTool, setActiveTool] = useState<string>("");
  const [portalOpen, setPortalOpen] = useState(false);
  const [lang, setLang] = useState<"bn" | "en">("bn");
  const [callStartTime, setCallStartTime] = useState<number | null>(null);

  const addLine = useCallback((role: TranscriptLine["role"], text: string) => {
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setCallLines((prev) => [...prev, { role, text, time }]);
  }, []);

  // Build client tools dispatched to FastAPI backend
  const clientTools = useMemo(
    () =>
      buildClientTools(({ name }) => {
        setActiveTool(name);
        addLine("tool", `Action dispatched: ${name}()`);
        setTimeout(() => setActiveTool(""), 4000);
      }),
    [addLine]
  );

  const conversation = useConversation({
    clientTools,
    onConnect: () => {
      setError("");
      setCallStartTime(Date.now());
      addLine("system", "Connected to Dhaka Dental Care AI Receptionist.");
    },
    onDisconnect: () => {
      addLine("system", "Call ended.");
    },
    onError: (err: unknown) => {
      setError(String(err));
      addLine("system", `Call error: ${String(err)}`);
    },
    onMessage: ({ message, source }: { message: string; source: string }) => {
      addLine(source === "user" ? "you" : "ai", message);
    },
  });

  const connected = conversation.status === "connected";
  const connecting = engaging || conversation.status === "connecting";

  // Sync finished call data with FastAPI backend when session disconnects
  const callLinesRef = useRef(callLines);
  useEffect(() => {
    callLinesRef.current = callLines;
  });

  const callStartTimeRef = useRef(callStartTime);
  useEffect(() => {
    callStartTimeRef.current = callStartTime;
  });

  const prevConnected = useRef(connected);
  useEffect(() => {
    if (prevConnected.current && !connected) {
      // Call just disconnected
      const duration = callStartTimeRef.current ? Math.round((Date.now() - callStartTimeRef.current) / 1000) : 0;
      const transcripts = callLinesRef.current
        .filter((l) => l.role === "you" || l.role === "ai")
        .map((l) => ({
          speaker: l.role === "ai" ? ("ai" as const) : ("patient" as const),
          text_bn: l.text,
        }));

      if (transcripts.length > 0) {
        completeCall({
          duration_s: duration,
          status: transcripts.some((t) => t.text_bn.includes("কনফার্ম")) ? "booked" : "enquiry",
          summary: `Web conversation completed (${duration}s)`,
          transcripts,
        }).catch((err) => console.error("Error saving call:", err));
      }
    }
    prevConnected.current = connected;
  }, [connected]);

  // Audio frequency analyser for Three.js 3D Orb animation
  const getFrequencies = useCallback(() => {
    try {
      return connected ? conversation.getOutputByteFrequencyData() : null;
    } catch {
      return null;
    }
  }, [connected, conversation]);

  const orbMode: OrbMode = error
    ? "error"
    : connecting
    ? "connecting"
    : connected
    ? conversation.isSpeaking
      ? "speaking"
      : "listening"
    : "idle";

  // Toggle live WebRTC voice session
  async function handleToggleCall() {
    if (connected) {
      conversation.endSession();
      return;
    }

    setEngaging(true);
    setError("");
    setCallLines([]);

    try {
      // 1. Get short-lived token from our FastAPI backend
      const { token } = await getSessionStart();

      // 2. Request mic and start WebRTC connection
      await conversation.startSession({
        conversationToken: token,
        connectionType: "webrtc",
      });
    } catch (caught: any) {
      setError(caught?.message || "Failed to start call. Ensure ELEVENLABS_API_KEY is configured in backend.");
    } finally {
      setEngaging(false);
    }
  }

  useEffect(() => {
    getConfig().then(setConfig).catch(() => undefined);
  }, []);

  return (
    <div className="relative min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-emerald-500 selection:text-white">
      {/* 3D Orb Background Glow & Ambience */}
      <div className="fixed inset-0 pointer-events-none z-0 opacity-40">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] bg-emerald-600/10 rounded-full blur-[140px]" />
        <div className="absolute top-1/3 right-1/4 w-[400px] h-[400px] bg-cyan-600/10 rounded-full blur-[120px]" />
      </div>

      {/* Top Navbar */}
      <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto flex h-20 items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-white shadow-lg shadow-emerald-500/20 text-xl font-bold">
              🦷
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-extrabold tracking-tight text-white">ByteVoice</span>
                <span className="rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-400 border border-emerald-500/20">
                  Bangladesh
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Dhaka Dental Care — AI Receptionist</p>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-300">
            <a href="#features" className="hover:text-emerald-400 transition">
              {lang === "bn" ? "ফিচারসমূহ" : "Features"}
            </a>
            <a href="#how-it-works" className="hover:text-emerald-400 transition">
              {lang === "bn" ? "কীভাবে কাজ করে" : "How It Works"}
            </a>
            <a href="#use-cases" className="hover:text-emerald-400 transition">
              {lang === "bn" ? "ব্যবহার ক্ষেত্র" : "Use Cases"}
            </a>
            <a href="#pricing" className="hover:text-emerald-400 transition">
              {lang === "bn" ? "সার্ভিস ও ফি" : "Services & Fees"}
            </a>
            <a href="#contact" className="hover:text-emerald-400 transition">
              {lang === "bn" ? "যোগাযোগ" : "Contact"}
            </a>
          </nav>

          <div className="flex items-center gap-4">
            {/* Language Switcher */}
            <button
              onClick={() => setLang(lang === "bn" ? "en" : "bn")}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-white hover:border-slate-600 transition"
            >
              🌐 {lang === "bn" ? "English" : "বাংলা"}
            </button>

            {/* Admin Portal Button */}
            <button
              onClick={() => setPortalOpen(true)}
              className="flex items-center gap-2 rounded-xl bg-slate-900 border border-slate-700 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-slate-800 hover:border-emerald-500/50 transition"
            >
              <span>📊 Staff Portal</span>
              <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section with Live 3D Orb and WebRTC Voice Call */}
      <section className="relative z-10 pt-12 pb-24 px-6 overflow-hidden">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Column: Headlines & Call Action */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-medium text-emerald-400 backdrop-blur-md">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              StrategyByte Australia — Expansion into Bangladesh
            </div>

            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.15]">
              {lang === "bn" ? (
                <>
                  বাংলাদেশের প্রথম <br />
                  <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
                    ডেন্টাল ক্লিনিক AI রিসেপশনিস্ট
                  </span>
                </>
              ) : (
                <>
                  Bangla AI Voice Receptionist for <br />
                  <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
                    Dental Clinics & Hospitals
                  </span>
                </>
              )}
            </h1>

            <p className="text-base md:text-lg text-slate-300 max-w-xl leading-relaxed">
              {lang === "bn"
                ? "রোগীর প্রতিটি ফোন কলের উত্তর দেবে স্বাভাবিক ও প্রমিত বাংলাদেশি বাংলায়। অ্যাপয়েন্টমেন্ট শিডিউলিং, দাঁতের সেবার তথ্য প্রদান ও ক্লিনিক্যাল ডেটা হ্যান্ডওভার—সম্পূর্ণ স্বয়ংক্রিয় ও নির্ভুল।"
                : "Answers patient phone calls in authentic Bangladeshi Bangla. Handles dental appointment bookings, answers clinic FAQs, and structures patient data for clinic staff."}
            </p>

            {/* LIVE VOICE CALL CTA BUTTON */}
            <div className="pt-2 space-y-4">
              <div className="flex flex-wrap items-center gap-4">
                <button
                  onClick={handleToggleCall}
                  disabled={engaging}
                  className={`group relative flex items-center gap-3.5 rounded-2xl px-8 py-4 text-base font-bold text-white shadow-xl transition-all transform active:scale-95 ${
                    connected
                      ? "bg-rose-600 hover:bg-rose-500 shadow-rose-900/40"
                      : "bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-emerald-900/40"
                  }`}
                >
                  <span className="text-xl">
                    {connected ? "🛑" : connecting ? "⏳" : "🎙️"}
                  </span>
                  <span>
                    {connected
                      ? lang === "bn"
                        ? "কল শেষ করুন (End Call)"
                        : "End Conversation"
                      : connecting
                      ? lang === "bn"
                        ? "সংযোগ হচ্ছে (Connecting...)"
                        : "Connecting..."
                      : lang === "bn"
                      ? "Talk to our Bangla caller"
                      : "Talk to our Bangla caller"}
                  </span>
                  {connected && (
                    <span className="flex h-3 w-3 rounded-full bg-white animate-ping" />
                  )}
                </button>

                <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${
                      connected
                        ? "bg-emerald-400 animate-pulse"
                        : connecting
                        ? "bg-amber-400 animate-bounce"
                        : "bg-slate-600"
                    }`}
                  />
                  <span>
                    {connected
                      ? "Status: Live Call (বাংলায় কথা বলুন)"
                      : connecting
                      ? "Status: Connecting..."
                      : "Status: Standing By"}
                  </span>
                </div>
              </div>

              {/* Error Notification */}
              {error && (
                <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3.5 text-xs text-rose-300 max-w-xl">
                  ⚠️ <b>Notice:</b> {error}
                  {!config?.voice_ok && (
                    <p className="mt-1 text-slate-400">
                      Add <code>ELEVENLABS_API_KEY</code> and <code>ELEVENLABS_AGENT_ID</code> to <code>.env</code> to activate live browser WebRTC conversation.
                    </p>
                  )}
                </div>
              )}

              {/* Real-time Action Badge */}
              {activeTool && (
                <div className="inline-flex items-center gap-2 rounded-lg bg-teal-500/20 border border-teal-500/40 px-3 py-1.5 text-xs font-mono text-teal-300">
                  <span className="animate-spin">⚙️</span>
                  <span>Database Tool Executing: {activeTool}</span>
                </div>
              )}
            </div>

            {/* Real-time Conversation Stream / Ticker */}
            {callLines.length > 0 && (
              <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 max-w-xl max-h-56 overflow-y-auto space-y-2 backdrop-blur-md">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
                    Live Call Dialogue Stream
                  </span>
                  <span className="text-[10px] text-slate-400">{callLines.length} events</span>
                </div>
                {callLines.map((line, idx) => (
                  <div
                    key={idx}
                    className={`text-xs flex gap-2 ${
                      line.role === "ai"
                        ? "text-emerald-300"
                        : line.role === "you"
                        ? "text-cyan-200"
                        : line.role === "tool"
                        ? "text-amber-300 font-mono"
                        : "text-slate-400 italic"
                    }`}
                  >
                    <span className="font-bold flex-shrink-0">
                      {line.role === "ai" ? "AI:" : line.role === "you" ? "Patient:" : "System:"}
                    </span>
                    <span className="flex-1">{line.text}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: 3D Holographic WebGL Orb (The AI Core) */}
          <div className="lg:col-span-5 flex flex-col items-center justify-center">
            <div className="relative w-full aspect-square max-w-[440px] rounded-3xl border border-slate-800 bg-gradient-to-b from-slate-900/40 to-slate-950/80 p-4 shadow-2xl backdrop-blur-md overflow-hidden flex items-center justify-center">
              {/* Orb Canvas */}
              <div className="w-full h-full relative">
                <JobvisOrb
                  mode={orbMode}
                  getFrequencies={getFrequencies}
                  gesturesOn={false}
                  onGestureReady={() => undefined}
                  onGestureError={() => undefined}
                />
              </div>

              {/* Status Overlay HUD */}
              <div className="absolute bottom-6 left-6 right-6 flex items-center justify-between rounded-xl border border-slate-700/60 bg-slate-900/80 px-4 py-2.5 backdrop-blur-md text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${
                      orbMode === "speaking"
                        ? "bg-rose-400 animate-pulse"
                        : orbMode === "listening"
                        ? "bg-emerald-400 animate-pulse"
                        : "bg-cyan-400"
                    }`}
                  />
                  <span className="font-mono text-slate-300 uppercase tracking-wider">
                    {orbMode === "speaking"
                      ? "AI Speaking"
                      : orbMode === "listening"
                      ? "Listening to Patient"
                      : orbMode === "connecting"
                      ? "Connecting..."
                      : "Orb: Standing By"}
                  </span>
                </div>
                <span className="text-slate-500 font-mono">3D WebGL</span>
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-3 text-center">
              3D Reactive Voice Core: Speaks & listens in authentic Bangladeshi Bangla.
            </p>
          </div>
        </div>
      </section>

      {/* Section 2: Features / How It Solves Clinic Problems */}
      <section id="features" className="relative z-10 py-20 px-6 border-t border-slate-900 bg-slate-950/50">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-emerald-400">Core Capabilities</h2>
            <p className="text-3xl md:text-4xl font-extrabold text-white">
              {lang === "bn"
                ? "বাংলাদেশের ক্লিনিকগুলোর ৫টি প্রধান সমস্যার সমাধান"
                : "Solving the 5 Biggest Phone Reception Bottlenecks"}
            </p>
            <p className="text-sm text-slate-400">
              {lang === "bn"
                ? "রিসিপশনিস্ট ব্যস্ত থাকা বা ছুটির দিনেও কোনো রোগীর কল মিস হবে না।"
                : "Never lose a patient to missed calls, busy receptionists, or after-hour inquiries."}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-3 hover:border-emerald-500/40 transition">
              <div className="h-10 w-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-xl text-emerald-400">
                📞
              </div>
              <h3 className="text-base font-bold text-white">Zero Missed Calls</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                একসাথে একাধিক রোগীর কল রিসিভ করতে পারে। ক্লিনিক বন্ধ থাকলেও ২৪/৭ দিনরাত কল রিসিভ করে বুকিং গ্রহণ করে।
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-3 hover:border-emerald-500/40 transition">
              <div className="h-10 w-10 rounded-xl bg-cyan-500/10 flex items-center justify-center text-xl text-cyan-400">
                🗣️
              </div>
              <h3 className="text-base font-bold text-white">Natural Bangla Code-Switching</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                বাংলা ও ইংরেজির স্বাভাবিক মিশ্রণ ("scaling", "appointment", "Sunday 5 PM") সহজেই বুঝতে পারে কোনো রোবোটিক ভাব ছাড়াই।
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-3 hover:border-emerald-500/40 transition">
              <div className="h-10 w-10 rounded-xl bg-teal-500/10 flex items-center justify-center text-xl text-teal-400">
                📅
              </div>
              <h3 className="text-base font-bold text-white">Zero Double-Booking</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                ব্যাকএন্ড ডেটাবেজের সাথে সরাসরি কানেক্টেড। স্লট খালি আছে কি না স্বয়ংক্রিয়ভাবে চেক করে কনফার্ম বুকিং নিশ্চিত করে।
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-3 hover:border-emerald-500/40 transition">
              <div className="h-10 w-10 rounded-xl bg-purple-500/10 flex items-center justify-center text-xl text-purple-400">
                🔒
              </div>
              <h3 className="text-base font-bold text-white">Clinical Staff Data Portal</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                প্রতিটি কলের শুরু থেকে শেষ পর্যন্ত পূর্ণাঙ্গ ট্রান্সক্রিপ্ট, রোগীর নাম, নম্বর ও বুকিং স্ট্যাটাস পোর্টালে রিয়েলটাইমে জমা হয়।
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Section 3: How It Works Flow */}
      <section id="how-it-works" className="relative z-10 py-20 px-6 border-t border-slate-900">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-cyan-400">Step-by-Step Flow</h2>
            <p className="text-3xl md:text-4xl font-extrabold text-white">কীভাবে কলটি পরিচালিত হয়</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 space-y-4">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500 text-sm font-bold text-white">
                1
              </span>
              <h3 className="text-base font-bold text-white">স্বাভাবিক সম্ভাষণ ও সমস্যা শোনা</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                "আসসালামু আলাইকুম, ঢাকা ডেন্টাল কেয়ারে স্বাগতম।" রোগীর সমস্যার কারণ (যেমন দাঁতে ব্যথা বা স্কেলিং) মনোযোগ দিয়ে বুঝে নেয়।
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 space-y-4">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-500 text-sm font-bold text-white">
                2
              </span>
              <h3 className="text-base font-bold text-white">নাম, ফোন ও স্লট যাচাই</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                রোগীর নাম ও ১১ ডিজিটের মোবাইল নম্বর নিশ্চিত করে। পছন্দের দিন ও সময় ব্যাকএন্ড ডাটাবেজে মিলিয়ে দেখে।
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 space-y-4">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500 text-sm font-bold text-white">
                3
              </span>
              <h3 className="text-base font-bold text-white">কনফার্মেশন ও পোর্টালে সিঙ্ক</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                রোগীকে তথ্যটি পড়ে শুনিয়ে ফাইনাল কনফার্ম করে। কল শেষ হওয়া মাত্রই ডেটাবেজ ও স্টাফ পোর্টালে ট্রান্সক্রিপ্ট সহ সেভ হয়ে যায়।
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Section 4: Clinical Use Cases */}
      <section id="use-cases" className="relative z-10 py-20 px-6 border-t border-slate-900 bg-slate-950/60">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-emerald-400">Industries & Sectors</h2>
            <p className="text-3xl md:text-4xl font-extrabold text-white">কারা ByteVoice ব্যবহার করবে?</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-2">
              <h3 className="text-base font-bold text-white">🦷 ডেন্টাল ক্লিনিক (Dental Clinics)</h3>
              <p className="text-xs text-slate-400">
                স্কেলিং, ফিলিং, রুট ক্যানেল ও ডেন্টাল সার্জারির সময়সূচি ও ডাক্তারের অ্যাপয়েন্টমেন্ট শিডিউলিং।
              </p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-2">
              <h3 className="text-base font-bold text-white">🧪 ডায়াগনস্টিক সেন্টার (Diagnostic Centres)</h3>
              <p className="text-xs text-slate-400">
                টেস্টের ফি, রিপোর্ট ডেলিভারির সময় ও টেস্টের আগে প্রস্তুতির নিয়মাবলি সম্পর্কে নির্ভুল তথ্য প্রদান।
              </p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-2">
              <h3 className="text-base font-bold text-white">🏥 হসপিটাল আউটপেশেন্ট (OPD Chambers)</h3>
              <p className="text-xs text-slate-400">
                বিশেষজ্ঞ ডাক্তারদের চেম্বার শিডিউল, রোগী সিরিয়াল ও ফলো-আপ কল হ্যান্ডলিং।
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Section 5: Services & Official Pricing */}
      <section id="pricing" className="relative z-10 py-20 px-6 border-t border-slate-900">
        <div className="max-w-4xl mx-auto space-y-8">
          <div className="text-center space-y-2">
            <h2 className="text-xs font-bold uppercase tracking-widest text-emerald-400">Dhaka Dental Care</h2>
            <p className="text-3xl font-extrabold text-white">যাচাইকৃত ডেন্টাল সেবা ও ফি তালিকা</p>
            <p className="text-xs text-slate-400">আমাদের AI এজেন্ট শুধুমাত্র এই যাচাইকৃত রেট ও তথ্য প্রদান করে।</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden shadow-xl">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 text-slate-400 uppercase tracking-wider text-[11px] border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-6">সেবার নাম (Dental Service)</th>
                  <th className="py-3.5 px-6">সময় (Duration)</th>
                  <th className="py-3.5 px-6 text-right">অফিসিয়াল ফি (Standard Fee)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-200">
                <tr>
                  <td className="py-3.5 px-6 font-semibold text-white">সাধারণ ডেন্টাল পরামর্শ ও চেকআপ</td>
                  <td className="py-3.5 px-6 text-slate-400">২০ মিনিট</td>
                  <td className="py-3.5 px-6 text-right font-bold text-emerald-400">৫০০ টাকা</td>
                </tr>
                <tr>
                  <td className="py-3.5 px-6 font-semibold text-white">দাঁত স্কেলিং ও পলিশিং (Teeth Scaling)</td>
                  <td className="py-3.5 px-6 text-slate-400">৪৫ মিনিট</td>
                  <td className="py-3.5 px-6 text-right font-bold text-emerald-400">১,৫০০ টাকা</td>
                </tr>
                <tr>
                  <td className="py-3.5 px-6 font-semibold text-white">কম্পোজিট ফিলিং (Dental Filling)</td>
                  <td className="py-3.5 px-6 text-slate-400">৩০ মিনিট</td>
                  <td className="py-3.5 px-6 text-right font-bold text-emerald-400">১,২০০ - ২,০০০ টাকা</td>
                </tr>
                <tr>
                  <td className="py-3.5 px-6 font-semibold text-white">রুট ক্যানেল ট্রিটমেন্ট (Root Canal)</td>
                  <td className="py-3.5 px-6 text-slate-400">৬০ মিনিট</td>
                  <td className="py-3.5 px-6 text-right font-bold text-emerald-400">৪,৫০০ - ৬,০০০ টাকা</td>
                </tr>
                <tr>
                  <td className="py-3.5 px-6 font-semibold text-white">দাঁত তোলা (Tooth Extraction)</td>
                  <td className="py-3.5 px-6 text-slate-400">৩০ মিনিট</td>
                  <td className="py-3.5 px-6 text-right font-bold text-emerald-400">১,০০০ - ২,৫০০ টাকা</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Section 6: Contact & Clinic Location */}
      <section id="contact" className="relative z-10 py-20 px-6 border-t border-slate-900 bg-slate-950/40">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12">
          <div className="space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-widest text-cyan-400">Get in Touch</h2>
            <p className="text-3xl font-extrabold text-white">ক্লিনিক লোকেশন ও সময়সূচি</p>
            <p className="text-sm text-slate-400 leading-relaxed">
              Dhaka Dental Care is equipped with state-of-the-art dental equipment and experienced oral surgeons.
            </p>
            <div className="space-y-2 text-xs text-slate-300 pt-2">
              <p>📍 <b>ঠিকানা:</b> হাউজ ১২, রোড ৪, ধানমন্ডি, ঢাকা-১২০৫ (ধানমন্ডি লেকের কাছে)</p>
              <p>🕒 <b>সময়সূচি:</b> শনিবার - বৃহস্পতিবার: সকাল ১০টা - রাত ৯টা | শুক্রবার: বিকেল ৪টা - রাত ৯টা</p>
              <p>📞 <b>ফোন:</b> +880 1711-223344</p>
              <p>🏢 <b>Technology Provider:</b> StrategyByte, Parramatta NSW, Australia</p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
            <h3 className="text-base font-bold text-white">ডেমো বুকিং অথবা ইনকোয়ারি</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">আপনার নাম</label>
                <input
                  type="text"
                  placeholder="e.g. Dr. Rafiqul Islam"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">ক্লিনিক বা হাসপাতালের নাম</label>
                <input
                  type="text"
                  placeholder="e.g. Uttara Dental Center"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">মোবাইল নম্বর</label>
                <input
                  type="text"
                  placeholder="017XXXXXXXX"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <button
                type="button"
                onClick={() => alert("ধন্যবাদ! আপনার অনুরোধটি গ্রহণ করা হয়েছে।")}
                className="w-full rounded-lg bg-emerald-600 py-2.5 font-bold text-white hover:bg-emerald-500 transition"
              >
                অনুরোধ পাঠান (Submit Demo Request)
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-900 py-8 px-6 text-center text-xs text-slate-500">
        <p>
          © 2026 StrategyByte — <b>ByteVoice Bangladesh</b>. Engineered for StrategyByte AI Engineer Take-Home Evaluation by{" "}
          <span className="text-emerald-400 font-medium">Masum Abedin</span>.
        </p>
        <p className="mt-1 text-[11px] text-slate-600">
          Backend: FastAPI + PostgreSQL | Voice: ElevenLabs WebRTC (Dhaka Dialect) | Frontend: Next.js + Three.js WebGL
        </p>
      </footer>

      {/* Staff Portal Modal Overlay */}
      {portalOpen && <PortalView onClose={() => setPortalOpen(false)} />}
    </div>
  );
}

export default function ByteVoiceLanding() {
  return (
    <ConversationProvider>
      <ByteVoiceLandingContent />
    </ConversationProvider>
  );
}
