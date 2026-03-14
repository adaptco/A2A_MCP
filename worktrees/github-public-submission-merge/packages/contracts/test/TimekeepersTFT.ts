import { expect } from "chai";
import { ethers } from "hardhat";

describe("TimekeepersTFT", () => {
  it("enforces rarity bounds and pid uniqueness", async () => {
    const [owner, other] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("TimekeepersTFT");
    const contract = await Factory.deploy(await owner.getAddress());
    await contract.waitForDeployment();
    const pid = ethers.id("pid-1");
    await expect(contract.connect(owner).chronoSyncMint(await owner.getAddress(), pid, 1)).to.emit(contract, "Transfer");
    await expect(contract.connect(owner).chronoSyncMint(await owner.getAddress(), pid, 1)).to.be.revertedWith("pid used");
    await expect(contract.connect(owner).chronoSyncMint(await owner.getAddress(), ethers.id("pid-2"), 3)).to.be.revertedWith(
      "rarity bounds"
    );
    const tokenId = await contract.pidReverse(pid);
    const prov = await contract.provenance(tokenId);
    expect(prov.rarityTier).to.equal(1);
    expect(prov.pidHash).to.equal(pid);
    await expect(contract.connect(other).chronoSyncMint(await other.getAddress(), ethers.id("pid-3"), 1)).to.be.reverted;
  });
});
