import { Worker } from "bullmq";
import { stableHash } from "@world-os/kernel";

const connection = { url: process.env.REDIS_URL || "redis://localhost:6379" };
const queueName = process.env.FORGE_QUEUE_NAME || "asset-forge";

type ForgeAssetRecordInput = {
  tokenSeed: string;
  tokenSeedHash: string;
  baseAssetId: string;
  styleClamp: number;
  url: string;
  lineage: string;
};

type PrismaClientLike = {
  forgeAsset: {
    create(args: { data: ForgeAssetRecordInput }): Promise<unknown>;
  };
};

function createPrismaClient(): PrismaClientLike {
  // `@prisma/client` only exposes PrismaClient after `prisma generate` runs.
  // Keep import dynamic so CI type-checks do not fail when generation is skipped.
  const prismaModule = require("@prisma/client") as {
    PrismaClient?: new () => PrismaClientLike;
  };

  if (!prismaModule.PrismaClient) {
    throw new Error("PrismaClient is unavailable. Run `prisma generate` before starting worker.");
  }

  return new prismaModule.PrismaClient();
}

const prisma = createPrismaClient();

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
