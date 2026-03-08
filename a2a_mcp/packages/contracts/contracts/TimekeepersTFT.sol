// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract TimekeepersTFT is ERC721Enumerable, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    struct Provenance {
        bytes32 pidHash;
        uint8 rarityTier;
    }

    mapping(bytes32 => uint256) public pidToTokenId;
    mapping(uint256 => Provenance) private _provenanceById;

    constructor(address admin) ERC721("Timekeepers TFT", "TFT") {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
    }

    function chronoSyncMint(address to, bytes32 pidHash, uint8 rarityTier) external onlyRole(MINTER_ROLE) returns (uint256) {
        require(rarityTier <= 2, "rarity bounds");
        require(pidToTokenId[pidHash] == 0, "pid used");
        uint256 tokenId = totalSupply() + 1;
        pidToTokenId[pidHash] = tokenId;
        _provenanceById[tokenId] = Provenance({pidHash: pidHash, rarityTier: rarityTier});
        _safeMint(to, tokenId);
        return tokenId;
    }

    function provenance(uint256 tokenId) external view returns (Provenance memory) {
        require(_exists(tokenId), "missing");
        return _provenanceById[tokenId];
    }

    function pidReverse(bytes32 pidHash) external view returns (uint256) {
        return pidToTokenId[pidHash];
    }
}
