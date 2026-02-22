import React, { useEffect, useState } from "react";
import { ApiClient } from "@world-os/sdk";

const api = new ApiClient({ baseUrl: (window as any).__API_URL__ || (import.meta.env.VITE_API_URL as string) || "http://localhost:3001" });

const CasePage: React.FC = () => {
  const [assets, setAssets] = useState<any[]>([]);
  useEffect(() => {
    api.forgeAssets().then(setAssets);
  }, []);

  return (
    <div className="space-y-3">
      <h2 className="font-semibold">Digital Display Case</h2>
      <div className="grid grid-cols-3 gap-3">
        {assets.map((asset) => (
          <div key={asset.id} className="bg-slate-800 p-3 rounded">
            <div className="font-semibold">Asset #{asset.id}</div>
            <div className="text-xs">Seed: {asset.tokenSeedHash}</div>
            <div className="text-xs">Base: {asset.baseAssetId}</div>
            <div className="text-xs">Rarity/Clamp: {asset.styleClamp}</div>
            <div className="text-xs">URL: {asset.url}</div>
            <div className="mt-2 h-16 bg-slate-700 rounded flex items-center justify-center text-xs">3D Viewer Placeholder</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CasePage;
