import React, { useState } from "react";
import { ApiClient } from "@world-os/sdk";
import { ethers } from "ethers";

const api = new ApiClient({ baseUrl: (window as any).__API_URL__ || (import.meta.env.VITE_API_URL as string) || "http://localhost:3001" });

const SyncPage: React.FC = () => {
  const [wallet, setWallet] = useState<string>("");
  const [key, setKey] = useState<string>("");
  const [challenge, setChallenge] = useState<any>(null);
  const [tx, setTx] = useState<string>("");

  const requestChallenge = async () => {
    const res = await api.chronoChallenge(key, wallet);
    setChallenge(res.challenge);
  };

  const signAndClaim = async () => {
    if (!challenge) return;
    const signer = ethers.Wallet.createRandom();
    const signature = await signer.signMessage(JSON.stringify(challenge));
    const res = await api.chronoClaim({ challenge, signature, wallet: signer.address });
    setTx(res.tx || res.note);
  };

  return (
    <div className="space-y-3">
      <h2 className="font-semibold">Chrono-Sync Claim</h2>
      <input
        className="bg-slate-800 border border-slate-700 rounded p-2 w-full"
        placeholder="Wallet"
        value={wallet}
        onChange={(e) => setWallet(e.target.value)}
      />
      <input
        className="bg-slate-800 border border-slate-700 rounded p-2 w-full"
        placeholder="Chrono-Key"
        value={key}
        onChange={(e) => setKey(e.target.value)}
      />
      <div className="flex gap-2">
        <button className="bg-indigo-600 px-3 py-2 rounded" onClick={requestChallenge}>
          Get Challenge
        </button>
        <button className="bg-green-600 px-3 py-2 rounded" onClick={signAndClaim} disabled={!challenge}>
          Sign & Claim
        </button>
      </div>
      {challenge && (
        <pre className="bg-slate-800 p-2 rounded text-xs whitespace-pre-wrap">{JSON.stringify(challenge, null, 2)}</pre>
      )}
      {tx && <div className="text-sm">Result: {tx}</div>}
    </div>
  );
};

export default SyncPage;
