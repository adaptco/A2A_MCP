#!/usr/bin/env python3
"""Training loop for Queen CiCi's vision capsule prototype."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms as T
from tqdm import tqdm


# --- Data ------------------------------------------------------------------
class CiciSet(Dataset):
    """Simple JSONL-backed dataset."""

    def __init__(self, manifest: str) -> None:
        path = Path(manifest)
        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest}")
        with path.open() as handle:
            self.rows = [json.loads(line) for line in handle if line.strip()]
        if not self.rows:
            raise ValueError("Manifest is empty; supply at least one exemplar.")
        self.tx = T.Compose(
            [
                T.Resize(336),
                T.CenterCrop(336),
                T.ToTensor(),
                T.Normalize([0.5] * 3, [0.5] * 3),
            ]
        )

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        image = Image.open(row["image_path"]).convert("RGB")
        return self.tx(image), row["prompt"], row


# --- Models (stub backbones; swap with production modules) ------------------
class TinyVision(nn.Module):
    def __init__(self, dim: int = 1024) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=7, stride=2, padding=3),
            nn.GELU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.proj = nn.Linear(32, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
        feats = self.encoder(x).flatten(1)
        return F.normalize(self.proj(feats), dim=-1)


class TinyText(nn.Module):
    def __init__(self, dim: int = 1024) -> None:
        super().__init__()
        self.emb = nn.Embedding(32000, 768)
        self.proj = nn.Linear(768, dim)

    def forward(self, toks: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
        z = self.emb(toks).mean(1)
        return F.normalize(self.proj(z), dim=-1)


# --- Tokenizer --------------------------------------------------------------
def tokenize(batch_prompts: Sequence[str], pad: int = 64) -> torch.LongTensor:
    """Very small placeholder tokenizer. Swap for production tokenizer."""

    encoded: List[List[int]] = []
    for prompt in batch_prompts:
        ids = [max(1, (ord(ch) % 30000)) for ch in prompt[:pad]]
        ids.extend([0] * (pad - len(ids)))
        encoded.append(ids)
    return torch.tensor(encoded, dtype=torch.long)


# --- Loss helpers -----------------------------------------------------------
def clip_loss(z_img: torch.Tensor, z_txt: torch.Tensor, temp: float = 0.07) -> torch.Tensor:
    logits = z_img @ z_txt.t() / temp
    labels = torch.arange(len(z_img), device=z_img.device)
    return (F.cross_entropy(logits, labels) + F.cross_entropy(logits.t(), labels)) / 2


def cosine(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    return F.cosine_similarity(a, b, dim=-1).mean()


def policy_guard_loss(meta_batch: Sequence[dict]) -> torch.Tensor:
    ok = 0
    total = 0
    for meta in meta_batch:
        policy = meta.get("policy", {})
        if policy.get("lattice"):
            ok += 1
        if policy.get("intentdiff"):
            ok += 1
        total += 1 + int(bool(policy.get("intentdiff")))
    frac = ok / max(1, total)
    return torch.tensor(1.0 - frac)


# --- Train ------------------------------------------------------------------
def resolve_device(requested: str | None = None) -> torch.device:
    if requested:
        return torch.device(requested)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def run_epoch(
    loader: DataLoader,
    vision: nn.Module,
    text: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    vision.train()
    text.train()
    running = 0.0
    for imgs, prompts, metas in tqdm(loader, desc="train", leave=False):
        imgs = imgs.to(device)
        toks = tokenize(prompts).to(device)
        z_img = vision(imgs)
        z_txt = text(toks)

        loss_clip = clip_loss(z_img, z_txt)
        loss_id = torch.tensor(0.0, device=device)
        loss_style = torch.tensor(0.0, device=device)

        ids = [m.get("id_embed_ref") for m in metas]
        if ids and all(isinstance(x, list) for x in ids):
            ref = torch.tensor(ids, dtype=torch.float32, device=device)
            ref = F.normalize(ref, dim=-1)
            loss_id = 1.0 - cosine(z_img, ref)

        styles = [m.get("style_vec") for m in metas]
        if styles and all(isinstance(x, list) for x in styles):
            style_vec = torch.tensor(styles, dtype=torch.float32, device=device)
            style_vec = F.normalize(style_vec, dim=-1)
            loss_style = 1.0 - cosine(z_img, style_vec)

        loss_guard = policy_guard_loss(metas).to(device)

        loss = loss_clip + loss_id + 0.5 * loss_style + 0.5 * loss_guard

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(list(vision.parameters()) + list(text.parameters()), 1.0)
        optimizer.step()

        running += float(loss.item())
    return running / max(1, len(loader))


def quick_eval(
    batch_imgs: torch.Tensor,
    batch_prompts: Sequence[str],
    vision: nn.Module,
    text: nn.Module,
    device: torch.device,
) -> float:
    vision.eval()
    text.eval()
    with torch.no_grad():
        imgs = batch_imgs.to(device)
        toks = tokenize(batch_prompts).to(device)
        z_img = vision(imgs)
        z_txt = text(toks)
        sim = torch.diag(z_img @ z_txt.t()).mean().item()
    return float(sim)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train CiCi's vision embedding prototype")
    parser.add_argument("manifest", nargs="?", default="data/cici_manifest.jsonl")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    dataset = CiciSet(args.manifest)
    loader = DataLoader(
        dataset,
        batch_size=args.batch,
        shuffle=True,
        num_workers=min(4, os.cpu_count() or 1),
        pin_memory=torch.cuda.is_available(),
    )

    device = resolve_device(args.device)

    vision = TinyVision().to(device)
    text = TinyText().to(device)
    optimizer = torch.optim.AdamW(
        list(vision.parameters()) + list(text.parameters()),
        lr=args.lr,
        betas=(0.9, 0.98),
        weight_decay=0.01,
    )

    for epoch in range(1, args.epochs + 1):
        avg_loss = run_epoch(loader, vision, text, optimizer, device)
        try:
            batch_imgs, batch_prompts, _ = next(iter(loader))
            subset_imgs = batch_imgs[: max(1, len(batch_imgs) // 2)]
            subset_prompts = batch_prompts[: max(1, len(batch_prompts) // 2)]
            eval_score = quick_eval(subset_imgs, subset_prompts, vision, text, device)
        except StopIteration:
            eval_score = float("nan")
        print(f"Epoch {epoch}: loss={avg_loss:.3f} diag-sim={eval_score:.3f}")

    Path(".out").mkdir(exist_ok=True)
    torch.save({"vision": vision.state_dict(), "text": text.state_dict()}, ".out/cici_vision_ckpt.pt")
    print("✅ Checkpoint → .out/cici_vision_ckpt.pt")


if __name__ == "__main__":
    main()
