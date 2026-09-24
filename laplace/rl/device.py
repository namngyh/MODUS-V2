"""Chon thiet bi o MOT cho duy nhat (xem muc "Uu tien GPU" trong CLAUDE.md)."""

from __future__ import annotations

import torch


def get_device(prefer_gpu: bool = True) -> torch.device:
    """Tra ve cuda neu co, nguoc lai cpu.

    Rai `.cuda()` khap noi la cach chac chan nhat de mot tensor bi bo quen tren CPU
    va forward pass nem loi thiet bi giua chung huan luyen.
    """
    if prefer_gpu and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def describe(device: torch.device) -> str:
    if device.type != "cuda":
        return f"{device} (torch {torch.__version__})"
    p = torch.cuda.get_device_properties(device)
    return (f"{p.name} | {p.total_memory / 1e9:.1f} GB | {p.multi_processor_count} SM "
            f"| CUDA {torch.version.cuda}")
