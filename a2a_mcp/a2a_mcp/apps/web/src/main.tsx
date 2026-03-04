import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Home from "./pages/Home";
import SyncPage from "./pages/Sync";
import CasePage from "./pages/Case";
import JurassicPixels from "./pages/JurassicPixels";
import "./index.css";

const App = () => (
  <BrowserRouter>
    <div className="p-4 space-y-4">
      <header className="flex items-center gap-4">
        <h1 className="text-xl font-bold">World OS Codex</h1>
        <nav className="flex gap-3 text-sm text-slate-200">
          <Link to="/">Game</Link>
          <Link to="/sync">Sync</Link>
          <Link to="/case">Case</Link>
          <Link to="/jurassic-pixels">Jurassic Pixels</Link>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/sync" element={<SyncPage />} />
        <Route path="/case" element={<CasePage />} />
        <Route path="/jurassic-pixels" element={<JurassicPixels />} />
      </Routes>
    </div>
  </BrowserRouter>
);

ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
