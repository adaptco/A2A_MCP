import { useMemo, useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Pizza, Bike, Store, Users, Flame, ShieldCheck, Cpu, Coins, ClipboardList } from "lucide-react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const PHASES = [
  { id: "opening",  label: "Open",    icon: "🏪", detail: "Boot systems, check inventory, set readiness." },
  { id: "prep",     label: "Prep",    icon: "🔪", detail: "Sauce, dough, toppings, station setup." },
  { id: "orders",   label: "Orders",  icon: "📞", detail: "Capture demand, route tickets, quote ETAs." },
  { id: "baking",   label: "Bake",    icon: "🔥", detail: "Run ovens, monitor quality, time throughput." },
  { id: "delivery", label: "Deliver", icon: "🛵", detail: "Dispatch drivers, complete routes, confirm handoff." },
  { id: "payment",  label: "Pay",     icon: "💳", detail: "Reconcile cash, cards, tips, refunds, closeout." },
];

const ROLE_META = {
  owner:    { label: "Owner",         color: "bg-rose-500/20 text-rose-200 border-rose-400/30",       mission: "Capital allocation, standards, margin, growth policy, authority map." },
  manager:  { label: "Manager",       color: "bg-sky-500/20 text-sky-200 border-sky-400/30",          mission: "Staffing, shift orchestration, SLA control, escalation, audit trail." },
  cooks:    { label: "Cooks",         color: "bg-amber-500/20 text-amber-100 border-amber-400/30",    mission: "Prep, oven throughput, quality, waste reduction, station flow." },
  foh:      { label: "Front of House",color: "bg-emerald-500/20 text-emerald-100 border-emerald-400/30", mission: "Order intake, CX, upsell, queue shaping, payment resolution." },
  delivery: { label: "Delivery",      color: "bg-violet-500/20 text-violet-100 border-violet-400/30", mission: "Route efficiency, handoff quality, cash/tip integrity, ETA confidence." },
};

const BACKEND_EPIC = [
  { title:"Owner domain",         bullets:["Authority map, pricing guardrails, labor target, quality thresholds.","Daily P&L summary, route profitability, promo governance, exception approval.","Policy engine for refunds, discounts, and store-wide incentives."] },
  { title:"Manager domain",       bullets:["Shift scheduler, role assignment, rush-mode toggles, inventory exception handling.","Kitchen/dispatch balancing and SLA breach alerts.","Conflict resolution queue for re-fire, remake, or refund decisions."] },
  { title:"Cook domain",          bullets:["Prep readiness scoring, recipe checklists, oven queues, batch timing.","Waste logging, substitution logic, station performance metrics.","Ticket prioritization by promised ETA and delivery bundling window."] },
  { title:"Front-of-house domain",bullets:["Counter, phone, kiosk, and web order orchestration with a single queue.","Customer sentiment markers, scripted upsells, payment exception routing.","Promise-time engine aligned to kitchen and driver availability."] },
  { title:"Delivery domain",      bullets:["Route planner, cash reconciliation, driver status, tip capture, proof of handoff.","Temperature-hold window, late-order escalation, zone balancing.","Driver safety prompts and mileage/event logging."] },
];

export default function CharleyFoxPizzaEpoch() {
  const [activePhase, setActivePhase] = useState("opening");
  const [completed,   setCompleted]   = useState([]);
  const [quests,      setQuests]      = useState([]);
  const [gold,        setGold]        = useState(0);
  const [heat,        setHeat]        = useState(28);
  const [notes,       setNotes]       = useState("Rush hour emerging from the East Side district. Focus on order capture → oven timing → route batching.");
  const [partyName,   setPartyName]   = useState("Charley Fox Guild");
  const [sessionId,   setSessionId]   = useState(null);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState(null);

  // Initialize session on mount
  useEffect(() => {
    initializeSession();
  }, []);

  // Fetch quests when phase changes
  useEffect(() => {
    if (sessionId) {
      fetchQuests(activePhase);
    }
  }, [activePhase, sessionId]);

  const initializeSession = async () => {
    try {
      setLoading(true);
      const res = await axios.post(`${API_BASE}/api/session/create`, null, {
        params: { party_name: partyName }
      });
      setSessionId(res.data.session_id);
      setGold(res.data.gold);
      setHeat(res.data.heat);
      setNotes(res.data.notes);
      fetchAllQuests();
    } catch (err) {
      setError(err.message);
      console.error("Failed to initialize session:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllQuests = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/quests`);
      setQuests(res.data);
    } catch (err) {
      console.error("Failed to fetch quests:", err);
    }
  };

  const fetchQuests = async (phase) => {
    try {
      const res = await axios.get(`${API_BASE}/api/quests/${phase}`);
      setQuests(res.data);
    } catch (err) {
      console.error("Failed to fetch quests:", err);
    }
  };

  const visibleQuests = useMemo(() => quests.filter((q) => q.phase === activePhase), [quests, activePhase]);
  const progress   = Math.round((completed.length / 6) * 100);
  const mergeReady = progress === 100;

  const completeQuest = async (quest) => {
    if (!sessionId || completed.includes(quest.id)) return;
    
    try {
      setLoading(true);
      const res = await axios.post(`${API_BASE}/api/session/${sessionId}/quest/complete`, {
        quest_id: quest.id,
        notes: notes
      });
      
      setCompleted((p) => [...p, quest.id]);
      setGold(res.data.gold);
      setHeat(res.data.heat);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      console.error("Failed to complete quest:", err);
    } finally {
      setLoading(false);
    }
  };

  const resetRun = async () => {
    if (!sessionId) return;
    try {
      setLoading(true);
      await axios.post(`${API_BASE}/api/session/${sessionId}/reset`);
      setCompleted([]);
      setGold(0);
      setHeat(28);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const updateNotes = async (newNotes) => {
    setNotes(newNotes);
    if (sessionId) {
      try {
        await axios.post(`${API_BASE}/api/session/${sessionId}/update-notes`, null, {
          params: { notes: newNotes }
        });
      } catch (err) {
        console.error("Failed to update notes:", err);
      }
    }
  };

  const nextPhase = () => setActivePhase(PHASES[(PHASES.findIndex((p) => p.id === activePhase) + 1) % PHASES.length].id);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto grid max-w-7xl gap-6 p-4 md:p-8">

        {error && (
          <motion.div initial={{ opacity:0, y:12 }} animate={{ opacity:1, y:0 }} 
            className="rounded-2xl border border-red-600 bg-red-950/30 p-4 text-red-200">
            {error}
          </motion.div>
        )}

        <motion.div initial={{ opacity:0, y:12 }} animate={{ opacity:1, y:0 }} className="grid gap-4 lg:grid-cols-[1.3fr_.7fr]">

          {/* ── HERO CARD ── */}
          <Card className="overflow-hidden rounded-3xl border-slate-800 bg-gradient-to-br from-orange-950 via-slate-950 to-slate-900 shadow-2xl">
            <CardContent className="p-0">
              <div className="grid gap-0 lg:grid-cols-[1.1fr_.9fr]">

                <div className="border-b border-slate-800 p-6 lg:border-b-0 lg:border-r">
                  <div className="mb-4 flex items-center gap-3">
                    <div className="rounded-2xl bg-orange-500/15 p-3"><Pizza className="h-7 w-7" /></div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.3em] text-orange-300">Epoch Widget</p>
                      <h1 className="text-2xl font-semibold">Charley Fox: Pizza Delivery JRPG</h1>
                    </div>
                  </div>
                  <p className="text-sm leading-6 text-slate-300">
                    A browser-playable enterprise simulator where the pizza shop is the operating system. The player advances the workday through front-end actions while observing the role-based back-end control model.
                  </p>

                  <div className="mt-6 grid gap-3 sm:grid-cols-3">
                    {[
                      { icon:<Store className="h-4 w-4"/>, label:"Store Readiness", value:`${100 - Math.min(heat, 80)}%` },
                      { icon:<Coins className="h-4 w-4"/>, label:"Gold / Revenue",   value:gold },
                      { icon:<Cpu   className="h-4 w-4"/>, label:"Shift Completion", value:`${progress}%` },
                    ].map((s) => (
                      <Card key={s.label} className="rounded-2xl border-slate-800 bg-slate-900/70">
                        <CardContent className="p-4">
                          <div className="flex items-center gap-2 text-sm text-slate-300">{s.icon} {s.label}</div>
                          <div className="mt-2 text-2xl font-semibold">{s.value}</div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>

                  <div className="mt-6 rounded-3xl border border-orange-500/20 bg-black/20 p-4">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div>
                        <div className="text-sm font-medium">Adventure Party</div>
                        <div className="text-xs text-slate-400">Rename the operating guild for embedded deployments.</div>
                      </div>
                      <Badge className="rounded-full border-orange-400/30 bg-orange-500/10 text-orange-200">Session: {sessionId?.slice(0, 8)}</Badge>
                    </div>
                    <Input value={partyName} onChange={(e) => setPartyName(e.target.value)} className="rounded-2xl border-slate-700 bg-slate-900" />
                    <Textarea value={notes} onChange={(e) => updateNotes(e.target.value)} className="mt-3 min-h-[80px] rounded-2xl border-slate-700 bg-slate-900" />
                  </div>
                </div>

                {/* Phase selector */}
                <div className="p-6">
                  <div className="rounded-3xl border border-slate-800 bg-slate-950/90 p-4">
                    <div className="mb-4 flex items-center justify-between">
                      <div>
                        <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Control Gate</p>
                        <h2 className="text-xl font-semibold">Workday Worldline</h2>
                      </div>
                      <Badge className={mergeReady ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200" : "border-slate-700 bg-slate-800 text-slate-300"}>
                        {mergeReady ? "MERGE READY" : "IN PROGRESS"}
                      </Badge>
                    </div>
                    <Progress value={progress} className="h-3" />
                    <div className="mt-3 text-xs text-slate-400">All six gameplay phases map to one enterprise control loop.</div>
                    <Separator className="my-4 bg-slate-800" />
                    <div className="space-y-3">
                      {PHASES.map((phase) => {
                        const sel = phase.id === activePhase;
                        return (
                          <button key={phase.id} onClick={() => setActivePhase(phase.id)}
                            className={`flex w-full items-start gap-3 rounded-2xl border p-3 text-left transition ${sel ? "border-orange-400/40 bg-orange-500/10" : "border-slate-800 bg-slate-900/70 hover:border-slate-700"}`}>
                            <div className="text-xl">{phase.icon}</div>
                            <div>
                              <div className="font-medium">{phase.label}</div>
                              <div className="text-xs text-slate-400">{phase.detail}</div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* ── PHASE HUD ── */}
          <Card className="rounded-3xl border-slate-800 bg-slate-900/80">
            <CardHeader>
              <CardTitle>Live Phase HUD</CardTitle>
              <CardDescription>JRPG command deck for the selected phase.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {visibleQuests.map((quest) => {
                  const isDone = completed.includes(quest.id);
                  const meta   = ROLE_META[quest.role];
                  return (
                    <motion.div key={quest.id} layout className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                      <div className="mb-3 flex items-start justify-between gap-3">
                        <div>
                          <div className="text-lg font-medium">{quest.title}</div>
                          <div className="mt-1 text-sm text-slate-400">{quest.description}</div>
                        </div>
                        <Badge className={`rounded-full border ${meta.color}`}>{meta.label}</Badge>
                      </div>
                      <div className="mb-4 flex flex-wrap gap-2">
                        <Badge variant="outline" className="rounded-full border-slate-700 text-xs">Reward +{quest.reward}</Badge>
                        <Badge variant="outline" className="rounded-full border-slate-700 text-xs">Heat +{quest.effort}</Badge>
                      </div>
                      <Button disabled={isDone || loading} onClick={() => completeQuest(quest)} className="w-full rounded-2xl">
                        {isDone ? "✓ Completed" : `Execute ${quest.title}`}
                      </Button>
                    </motion.div>
                  );
                })}
                <div className="grid grid-cols-2 gap-3">
                  <Button variant="secondary" className="rounded-2xl" onClick={resetRun} disabled={loading}>Reset Shift</Button>
                  <Button className="rounded-2xl" onClick={nextPhase}>Next Phase →</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* ── TABS ── */}
        <Tabs defaultValue="backend" className="w-full">
          <TabsList className="grid w-full grid-cols-4 rounded-2xl bg-slate-900">
            <TabsTrigger value="backend">Back End Roles</TabsTrigger>
            <TabsTrigger value="epic">Coding Epic</TabsTrigger>
            <TabsTrigger value="widget">Embed Widget</TabsTrigger>
            <TabsTrigger value="telemetry">Control Telemetry</TabsTrigger>
          </TabsList>

          <TabsContent value="backend" className="mt-4">
            <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
              {Object.entries(ROLE_META).map(([key, meta]) => (
                <Card key={key} className="rounded-3xl border-slate-800 bg-slate-900/80">
                  <CardHeader>
                    <CardTitle>{meta.label}</CardTitle>
                    <CardDescription>{meta.mission}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[180px] pr-3">
                      <ul className="space-y-2 text-sm text-slate-300">
                        {(BACKEND_EPIC.find((x) => x.title.toLowerCase().includes(meta.label.toLowerCase().split(" ")[0]))?.bullets || []).map((bullet, idx) => (
                          <li key={idx} className="rounded-2xl border border-slate-800 bg-slate-950 p-3">{bullet}</li>
                        ))}
                      </ul>
                    </ScrollArea>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="epic" className="mt-4">
            <Card className="rounded-3xl border-slate-800 bg-slate-900/80">
              <CardHeader>
                <CardTitle>Epic: Charley Fox Pizza Delivery V1</CardTitle>
                <CardDescription>Hand-off artifact for coding agents across gameplay, workflow, and platform layers.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 lg:grid-cols-2">
                {[
                  { title:"Player-facing scope", items:["JRPG town hub with shift loop: opening, prep, orders, baking, delivery, payment.","Quest-based progression with revenue, heat, SLA, and quality stats.","Embeddable game widget for the Agent Hub, plus mobile-safe control cards.","NPC role dialogues for owner, manager, cooks, FOH, and delivery personas."] },
                  { title:"Systems scope", items:["Workflow graph for ticket routing, kitchen state, dispatch state, payment settlement, and audit events.","RBAC-aligned actor model with authority boundaries and event-sourced logs.","Firebase Studio state mirror for sessions, orders, routes, users, and terminal feeds.","Frontier-model node hooks for assistance, summarization, QA, and RAG retrieval."] },
                ].map((col) => (
                  <div key={col.title} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                    <h3 className="mb-3 font-medium">{col.title}</h3>
                    <ul className="space-y-2 text-sm text-slate-300">
                      {col.items.map((item, i) => <li key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-2 text-xs">{item}</li>)}
                    </ul>
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="widget" className="mt-4">
            <Card className="rounded-3xl border-slate-800 bg-slate-900/80">
              <CardHeader>
                <CardTitle>Embed Contract</CardTitle>
                <CardDescription>Drop-in widget abstraction for Parker Sandbox / Canvas / Agent Hub.</CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950 p-4 text-xs text-slate-300">{`<charley-fox-pizza-epoch
  id="charley-fox-pizza-v1"
  mode="agent-hub-widget"
  framework="parkers-sandbox"
  theme="jrpg-night-market"
  stateSource="firebase://agent-hub/charley-fox/pizza-v1"
  workflowRunner="agent-hub.runner.charley-fox"
  productionSpoke="agent-hub.spoke.delivery"
  terminalFeed="chat.window.terminals.charley-fox"
  ragEngine="realtime-order-memory"
  intelligenceLayer="overlay"
  width="100%"
  height="720"
/>`}</pre>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="telemetry" className="mt-4">
            <div className="grid gap-4 lg:grid-cols-3">
              <Card className="rounded-3xl border-slate-800 bg-slate-900/80">
                <CardHeader><CardTitle>Heat Index</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-4xl font-semibold">{heat}</div>
                  <Progress value={heat} className="mt-3 h-2" />
                  <div className="mt-2 text-sm text-slate-400">Shift complexity proxy for queue pressure and route spillover.</div>
                </CardContent>
              </Card>
              <Card className="rounded-3xl border-slate-800 bg-slate-900/80">
                <CardHeader><CardTitle>Audit State</CardTitle></CardHeader>
                <CardContent>
                  <div className={`text-4xl font-semibold ${mergeReady ? "text-emerald-400" : "text-amber-400"}`}>{mergeReady ? "Green" : "Amber"}</div>
                  <div className="mt-2 text-sm text-slate-400">Maps the simulator state to hand-off readiness for the coding pipeline.</div>
                </CardContent>
              </Card>
              <Card className="rounded-3xl border-slate-800 bg-slate-900/80">
                <CardHeader><CardTitle>Terminal Feed</CardTitle></CardHeader>
                <CardContent>
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs font-mono text-orange-300">{notes}</div>
                  <div className="mt-3 text-xs text-slate-500">Party: {partyName}</div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
