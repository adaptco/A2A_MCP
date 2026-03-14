use serde::Serialize;
use std::fs;

#[derive(Debug, Serialize)]
pub struct LedgerEntry {
    pub sequence_id: u64,
    pub entry_type: EntryType,
    pub timestamp: f64,
    pub merkle_root: Vec<u8>,
    pub prev_merkle_root: Option<Vec<u8>>,
    pub drift: Option<f64>,
    pub ppm: Option<f64>,
    pub intervention_status: Option<String>,
}

#[derive(Debug, Serialize)]
pub enum EntryType {
    Standard,
    Refusal,
}

#[derive(Debug)]
pub struct WindchillLedger {
    pub entries: Vec<LedgerEntry>,
}

#[derive(Debug)]
pub struct CaptureFrame {
    pub scene_id: String,
}

pub fn seal_frame_into_ledger(_cap: &CaptureFrame, _ledger: &mut WindchillLedger) {
    // GUARD: Ensure the identity surface is defined before sealing.
    assert!(
        !_cap.scene_id.is_empty(),
        "Identity Breach: Attempted to seal frame with empty Scene ID."
    );
}

pub fn export_to_vault(ledger: &WindchillLedger) -> std::io::Result<()> {
    let vault_path = "vault/audits/burn_in_2026/";
    fs::create_dir_all(vault_path)?;

    for entry in &ledger.entries {
        let yaml = serde_yaml::to_string(&entry).unwrap();
        let content = format!(
            "---\n{}---\n# Audit Entry: Sequence {}\n\n**Status:** {}\n**Timestamp:** {:.4}s\n\n> [!ABSTRACT] Merkle Proof\n> Root: `0x{}`\n> Prev Root: `{}`\n\n**Drift:** {}\n**PPM:** {}\n**Intervention Status:** {}\n",
            yaml,
            entry.sequence_id,
            match entry.entry_type {
                EntryType::Standard => "✅ Nominal",
                EntryType::Refusal => "🚫 Sentinel Veto",
            },
            entry.timestamp,
            hex::encode(&entry.merkle_root),
            entry
                .prev_merkle_root
                .as_ref()
                .map(|root| format!("0x{}", hex::encode(root)))
                .unwrap_or_else(|| "n/a".to_string()),
            entry
                .drift
                .map(|value| format!("{value}"))
                .unwrap_or_else(|| "n/a".to_string()),
            entry
                .ppm
                .map(|value| format!("{value}"))
                .unwrap_or_else(|| "n/a".to_string()),
            entry
                .intervention_status
                .clone()
                .unwrap_or_else(|| "n/a".to_string())
        );

        let file_name = format!("{}burn_in_seq_{:06}.md", vault_path, entry.sequence_id);
        fs::write(file_name, content)?;
    }
    Ok(())
}
