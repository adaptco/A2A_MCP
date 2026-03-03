import React, { useEffect, useMemo, useState } from "react";
import { ApiClient, Action, State } from "@world-os/sdk";

const api = new ApiClient({ baseUrl: (window as any).__API_URL__ || (import.meta.env.VITE_API_URL as string) || "http://localhost:3001" });

const HexBoard: React.FC<{ state: State | null }> = ({ state }) => {
  if (!state) return <div className="p-4">Loading board...</div>;
  return (
    <div className="grid grid-cols-3 gap-2">
      {state.board.entities.map((e) => (
        <div key={e.id} className="border border-slate-700 rounded p-2">
          <div className="font-semibold">{e.kind}</div>
          <div className="text-xs text-slate-300">{e.id}</div>
          <div className="text-xs">q:{e.q} r:{e.r}</div>
          <div className="text-xs">hp:{e.hp}</div>
        </div>
      ))}
    </div>
  );
};

const Home: React.FC = () => {
  const [state, setState] = useState<State | null>(null);
  const [chat, setChat] = useState("");
  const [action, setAction] = useState<Action | null>(null);
  const [events, setEvents] = useState<string[]>([]);

  useEffect(() => {
    api.getState().then((res) => setState(res.state));
  }, []);

  const preview = useMemo(() => JSON.stringify(action, null, 2), [action]);

  const propose = async () => {
    const res = await api.proposeIntent(chat);
    setAction(res.action);
  };

  const commit = async () => {
    if (!action) return;
    const res = await api.act(action);
    setState(res.state);
    setEvents(res.events);
  };

  return (
    <div className="grid grid-cols-3 gap-4">
      <section className="col-span-2 space-y-3">
        <h2 className="font-semibold">Hex Board</h2>
        <HexBoard state={state} />
      </section>
      <section className="space-y-2">
        <h2 className="font-semibold">Chat / Intent</h2>
        <textarea
          value={chat}
          onChange={(e) => setChat(e.target.value)}
          className="w-full h-24 bg-slate-800 border border-slate-700 rounded p-2"
        />
        <button className="bg-indigo-600 px-3 py-2 rounded" onClick={propose}>
          Propose
        </button>
        <h3 className="font-semibold">Action Preview</h3>
        <pre className="bg-slate-800 p-2 rounded text-xs whitespace-pre-wrap">{preview}</pre>
        <button className="bg-green-600 px-3 py-2 rounded" onClick={commit} disabled={!action}>
          Execute Turn
        </button>
        <h3 className="font-semibold">Events</h3>
        <ul className="text-xs space-y-1">
          {events.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      </section>
    </div>
  );
};

export default Home;
