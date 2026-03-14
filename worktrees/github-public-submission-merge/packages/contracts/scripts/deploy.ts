import { ethers } from "hardhat";

async function main() {
  const [signer] = await ethers.getSigners();
  const Factory = await ethers.getContractFactory("TimekeepersTFT");
  const contract = await Factory.deploy(await signer.getAddress());
  await contract.waitForDeployment();
  console.log("TimekeepersTFT deployed to", await contract.getAddress());
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
