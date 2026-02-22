use sha2::{Digest, Sha256};

const DOMAIN: &str = "PSP.MerkleRoot.v1";
const SHA_TAG_PREFIX: &str = "sha256:";

fn sha_tag_to_bytes(tag: &str) -> Result<[u8; 32], String> {
    if !tag.starts_with(SHA_TAG_PREFIX) || tag.len() != SHA_TAG_PREFIX.len() + 64 {
        return Err(format!("bad sha tag: {}", tag));
    }
    let hex = &tag[SHA_TAG_PREFIX.len()..];
    let mut out = [0u8; 32];
    for i in 0..32 {
        let b = u8::from_str_radix(&hex[i * 2..i * 2 + 2], 16)
            .map_err(|_| format!("bad hex in sha tag: {}", tag))?;
        out[i] = b;
    }
    Ok(out)
}

fn bytes_to_sha_tag(bytes: &[u8; 32]) -> String {
    let mut s = String::from(SHA_TAG_PREFIX);
    for b in bytes {
        s.push_str(&format!("{:02x}", b));
    }
    s
}

fn sha256(preimage: &[u8]) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(preimage);
    let out = h.finalize();
    let mut arr = [0u8; 32];
    arr.copy_from_slice(&out);
    arr
}

pub fn psp_merkle_root_from_tick_hashes(tick_hashes: &[String]) -> Result<String, String> {
    if tick_hashes.is_empty() {
        return Ok(format!("{}{}", SHA_TAG_PREFIX, "0".repeat(64)));
    }

    let domain_bytes = DOMAIN.as_bytes();
    let mut layer: Vec<[u8; 32]> = Vec::with_capacity(tick_hashes.len());
    for t in tick_hashes {
        layer.push(sha_tag_to_bytes(t)?);
    }

    while layer.len() > 1 {
        let mut next: Vec<[u8; 32]> = Vec::with_capacity((layer.len() + 1) / 2);
        let mut i = 0usize;
        while i < layer.len() {
            let left = layer[i];
            let right = if i + 1 < layer.len() { layer[i + 1] } else { layer[i] };
            let mut preimage = Vec::with_capacity(domain_bytes.len() + 1 + 32 + 32);
            preimage.extend_from_slice(domain_bytes);
            preimage.push(0u8);
            preimage.extend_from_slice(&left);
            preimage.extend_from_slice(&right);
            next.push(sha256(&preimage));
            i += 2;
        }
        layer = next;
    }

    Ok(bytes_to_sha_tag(&layer[0]))
}
