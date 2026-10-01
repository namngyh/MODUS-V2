"""Mang LSTM du bao (spec 008).

    64 nen x F cot -> Linear(F->64)+tanh -> LSTM(64->64) -> h_t (64 so)
                                                            |-> head (a): 3 xac suat
                                                            |-> head (c): 1 so (ban "ac")

Phan doc du lieu giong encoder cua policy PPO (spec 002) de hai noi so sanh duoc; khac
o cho day la hoc CO DAP AN o moi nen chu khong hoc tu reward.
"""

from __future__ import annotations

import torch
import torch.nn as nn

VARIANTS = ("a", "ac")


def _head(in_dim: int, out_dim: int, hidden: int = 64) -> nn.Sequential:
    return nn.Sequential(nn.Linear(in_dim, hidden), nn.ReLU(), nn.Linear(hidden, out_dim))


class ForecastNet(nn.Module):
    def __init__(self, n_features: int, variant: str = "a", proj_dim: int = 64,
                 hidden: int = 64):
        super().__init__()
        if variant not in VARIANTS:
            raise ValueError(f"ban khong biet: {variant!r}")
        self.n_features, self.variant = n_features, variant
        self.proj = nn.Linear(n_features, proj_dim)
        self.lstm = nn.LSTM(proj_dim, hidden, num_layers=1, batch_first=True)
        self.head_a = _head(hidden, 3)
        self.head_c = _head(hidden, 1) if variant == "ac" else None

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """(N, window, F) -> h_t (N, hidden)."""
        out, _ = self.lstm(torch.tanh(self.proj(x)))
        return out[:, -1]

    def forward(self, x: torch.Tensor) -> dict:
        h = self.encode(x)
        logits = self.head_a(h)
        out = {"logits": logits, "prob": torch.softmax(logits, dim=-1)}
        if self.head_c is not None:
            out["ret"] = self.head_c(h).squeeze(-1)
        return out
