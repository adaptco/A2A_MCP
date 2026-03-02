import Fastify from "fastify";
import cors from "fastify-cors";
import websocket from "fastify-websocket";
import { PrismaClient } from "@prisma/client";
import { Queue } from "bullmq";
import { initialState, reduce, replay, stateHash, Action } from "@world-os/kernel";
import { ApiClient } from "@world-os/sdk";
import crypto from "crypto";
import { ethers } from "ethers";
import fs from "fs";
import path from "path";

const app = Fastify({ logger: true });
app.register(cors, { origin: true });
app.register(websocket);

const prisma = new PrismaClient();
const forgeQueue = new Queue(process.env.FORGE_QUEUE_NAME || "asset-forge", { connection: { url: process.env.REDIS_URL || "redis://localhost:6379" } });

const chronoRegistry = (() => {
  const keys: { pid: string; rarityTier: number; hash: string }[] = [];
  for (let i = 0; i < 20; i++) {
    const pid = `pid-${i}`;
    const rarityTier = i % 3;
    const hash = crypto.createHash("sha256").update(`key-${pid}`).digest("hex");
    keys.push({ pid, rarityTier, hash });
  }
  return keys;
})();

async function getCurrentState() {
  const latest = await prisma.ssotState.findFirst({ orderBy: { id: "desc" } });
  if (!latest) {
    const state = initialState();
    const hash = stateHash(state);
    await prisma.ssotState.create({ data: { state, hash } });
    return { state, hash };
  }
  return { state: latest.state as any, hash: latest.hash };
}

app.get("/health", async () => ({ status: "ok" }));

app.post("/game/intent", async (request, reply) => {
  const body = request.body as any;
  const chat: string = body?.chat || "";
  const action: Action = {
    type: "Move",
    actor: "player-1",
    payload: { entityId: "architect", q: 0, r: 0 }
  };
  const reasoning = chat.includes("build") ? "Suggesting build" : "Default move";
  return { action, reasoning };
});

app.post("/game/act", async (request, reply) => {
  const action = request.body as Action;
  const current = await getCurrentState();
  const result = reduce(current.state, action);
  const hash = stateHash(result.state);
  await prisma.actionLog.create({ data: { actor: action.actor, action } });
  await prisma.ssotState.create({ data: { state: result.state, hash } });
  return { state: result.state, events: result.events, hash };
});

app.get("/game/state", async () => getCurrentState());

app.get("/game/replay", async () => {
  const actions = await prisma.actionLog.findMany({ orderBy: { id: "asc" } });
  return actions.map((a) => a.action);
});

app.post("/chrono/challenge", async (request, reply) => {
  const { key, wallet } = request.body as any;
  const hashed = crypto.createHash("sha256").update(key).digest("hex");
  const found = chronoRegistry.find((k) => k.hash === hashed);
  if (!found) return reply.status(400).send({ error: "invalid key" });
  const nonce = crypto.randomBytes(8).toString("hex");
  const expiresAt = Date.now() + 5 * 60 * 1000;
  const challenge = { nonce, expiresAt, pidHash: hashed, rarityTier: found.rarityTier, pid: found.pid };
  const message = JSON.stringify(challenge);
  return { challenge, message, wallet };
});

app.post("/chrono/claim", async (request, reply) => {
  const { challenge, signature, wallet } = request.body as any;
  const recovered = ethers.verifyMessage(JSON.stringify(challenge), signature);
  if (recovered.toLowerCase() !== wallet.toLowerCase()) return reply.status(400).send({ error: "bad sig" });
  if (challenge.expiresAt < Date.now()) return reply.status(400).send({ error: "expired" });
  const existing = await prisma.chronoKeyClaim.findUnique({ where: { pidHash: challenge.pidHash } });
  if (existing) return reply.status(400).send({ error: "used" });
  await prisma.chronoKeyClaim.create({ data: { pidHash: challenge.pidHash, rarityTier: challenge.rarityTier, wallet } });
  const provider = new ethers.JsonRpcProvider(process.env.CHAIN_RPC || "http://127.0.0.1:8545");
  const signer = new ethers.Wallet(process.env.MINTER_PRIVATE_KEY || ethers.Wallet.createRandom().privateKey, provider);
  const address = process.env.CONTRACT_ADDRESS || "";
  if (!address) return { authorized: true, note: "Deploy contract then mint" };
  const abiPath = path.join(__dirname, "..", "..", "packages", "contracts", "artifacts", "contracts", "TimekeepersTFT.sol", "TimekeepersTFT.json");
  const abi = JSON.parse(fs.readFileSync(abiPath, "utf-8")).abi;
  const contract = new ethers.Contract(address, abi, signer);
  const tx = await contract.chronoSyncMint(wallet, `0x${challenge.pidHash}`, challenge.rarityTier);
  const receipt = await tx.wait();
  return { tx: receipt?.hash };
});

app.post("/forge/request", async (request) => {
  const payload = request.body as any;
  await forgeQueue.add("forge", payload);
  return { enqueued: true };
});

app.get("/forge/assets", async () => {
  const assets = await prisma.forgeAsset.findMany({ orderBy: { id: "desc" }, take: 20 });
  return assets;
});

app.listen({ port: 3001, host: "0.0.0.0" }, (err, address) => {
  if (err) {
    app.log.error(err);
    process.exit(1);
  }
  app.log.info(`API running at ${address}`);
});
