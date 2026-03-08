import { Worker } from "bullmq";
import { PrismaClient } from "@prisma/client";
import { stableHash } from "@world-os/kernel";

const connection = { url: process.env.REDIS_URL || "redis://localhost:6379" };
const queueName = process.env.FORGE_QUEUE_NAME || "asset-forge";
const prisma = new PrismaClient();

const worker = new Worker(
  queueName,
  async (job) => {
    const { tokenSeed, baseAssetId, styleClamp } = job.data as any;
    const tokenSeedHash = stableHash(tokenSeed);
    const url = `https://assets.local/${tokenSeedHash}.glb`;
    const lineage = `${baseAssetId}:${tokenSeedHash}`;
    if (JSON.stringify(job.data).length > 2048) throw new Error("payload too large");
    const record = await prisma.forgeAsset.create({
      data: { tokenSeed, tokenSeedHash, baseAssetId, styleClamp, url, lineage }
    });
    return record;
  },
  { connection }
);

worker.on("completed", (job) => {
  console.log("Forge complete", job.id);
});

worker.on("failed", (job, err) => {
  console.error("Forge failed", job?.id, err.message);
});
