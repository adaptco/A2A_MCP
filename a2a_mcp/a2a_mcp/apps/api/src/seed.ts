import { PrismaClient } from "@prisma/client";
import { initialState, stateHash } from "@world-os/kernel";

async function main() {
  const prisma = new PrismaClient();
  const state = initialState();
  const hash = stateHash(state);
  await prisma.ssotState.create({ data: { state, hash } });
  console.log("Seeded state", hash);
  await prisma.$disconnect();
}

main();
