"""Canh spec 008 - LSTM du bao (tang 1 cua MODUS 2).

Hai bai quan trong nhat canh bat bien #20: du bao dung de hoc tang sau phai do mot mo
hinh CHUA TUNG thay du lieu tai hay sau thoi diem do tao ra. Loi nay khong lam chuong
trinh dung - no chi lam Meta tin LSTM qua muc va sup khi gap du lieu moi.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch

from laplace.config import FeatureConfig
from laplace.forecast.labels import FLAT, DOWN, UP, NO_LABEL, barrier_labels
from laplace.forecast.folds import make_schedule, split_train_holdout
from laplace.forecast.metrics import baseline_probs, log_loss
from laplace.forecast.model import ForecastNet
from laplace.forecast.prep import prepare_fold_matrix
from laplace.forecast.train import TrainConfig, predict, train_fold
from laplace.scaling import make_split


# --------------------------------------------------------------------------- #
# Nhan
# --------------------------------------------------------------------------- #
def _bars(rows, session=None):
    o, h, l, c = (np.array(x, float) for x in zip(*rows))
    s = np.zeros(len(o), int) if session is None else np.asarray(session)
    return o, h, l, c, s


def test_barrier_label_matches_hand_example():
    """ATR = 1, k = 1,5 -> moc vao +- 1,5. Vao o gia MO CUA nen t+1."""
    o, h, l, c, s = _bars([
        (99, 99, 99, 99),        # 0: nen ra quyet dinh
        (100, 100.5, 99.5, 100), # 1: vao = 100, moc 101,5 / 98,5
        (101, 101.6, 99.9, 101), # 2: cham 101,5 -> t=0 LEN
        (101, 101, 97, 98),      # 3
        (98, 98, 98, 98),
    ])
    atr = np.ones(len(o))
    lab = barrier_labels(o, h, l, c, s, atr, k=1.5, horizon=3)
    assert lab.label[0] == UP
    # t=1: vao o open nen 2 = 101, moc 102,5 / 99,5. Nen 2 (99,9..101,6) chua cham;
    # nen 3 xuong 97 -> XUONG
    assert lab.label[1] == DOWN
    # cung mot nen cham ca hai moc: phan xu bang gia dong cua so voi gia vao
    o2, h2, l2, c2, s2 = _bars([(0, 0, 0, 0), (100, 100, 100, 100),
                                (100, 102, 98, 101), (101, 101, 101, 101)])
    assert barrier_labels(o2, h2, l2, c2, s2, np.ones(4), 1.5, 3).label[0] == UP


def test_label_never_crosses_session_end():
    """Het phien ma chua cham moc -> DI NGANG; quyet dinh o nen cuoi phien -> khong nhan."""
    rows = [(100, 100.2, 99.8, 100)] * 6
    o, h, l, c, s = _bars(rows, session=[0, 0, 0, 0, 1, 1])
    lab = barrier_labels(o, h, l, c, s, np.ones(6), k=1.5, horizon=24)
    assert lab.label[0] == FLAT
    assert lab.end[0] == 3, "khong duoc quet sang nen 4 cua phien sau"
    assert lab.label[3] == NO_LABEL, "nen cuoi phien: vao lenh se o phien sau"


def test_return_target_is_in_atr_units():
    o, h, l, c, s = _bars([(0, 0, 0, 0), (100, 100, 100, 100), (100, 100, 100, 103),
                           (103, 103, 103, 104)])
    lab = barrier_labels(o, h, l, c, s, np.full(4, 2.0), k=10, horizon=2)
    # vao 100, nen het = t+2 = 2, dong cua 103 -> (103 - 100) / 2 = 1,5 ATR
    assert lab.ret_atr[0] == pytest.approx(1.5)


# --------------------------------------------------------------------------- #
# Lich hoc - bat bien #20
# --------------------------------------------------------------------------- #
def _synthetic_index():
    days = pd.bdate_range("2017-12-01", "2023-03-31")
    return pd.DatetimeIndex([d + pd.Timedelta(minutes=540 + 5 * i)
                             for d in days for i in range(51)])


@pytest.fixture(scope="module")
def sched():
    idx = _synthetic_index()
    split = make_split(idx, FeatureConfig())
    session = idx.normalize().asi8
    end = np.minimum(np.arange(len(idx)) + 24, len(idx) - 1)
    return idx, split, make_schedule(idx, split, end, session)


def test_training_labels_never_reach_the_predicted_period(sched):
    idx, split, folds = sched
    end = np.minimum(np.arange(len(idx)) + 24, len(idx) - 1)
    assert [f.name for f in folds] == ["oof_2019", "oof_2020", "oof_2021", "final"]
    for f in folds:
        first_pred = f.predict_ends.min()
        assert (end[f.train_ends] < first_pred).all(), f"{f.name}: dap an cham giai doan du bao"
        fit, hold = split_train_holdout(f.train_ends, end, holdout_frac=0.1)
        assert (end[fit] < hold.min()).all(), f"{f.name}: dap an cua phan hoc cham phan canh dung"
        assert idx[hold].min() > idx[fit].max()


def test_schedule_never_predicts_the_test_set(sched):
    idx, split, folds = sched
    allowed = split.train | split.valid
    for f in folds:
        assert allowed[f.predict_ends].all(), f"{f.name} du bao vao tap test"
    final = folds[-1]
    assert set(final.predict_ends) == set(np.flatnonzero(split.valid))
    assert idx[final.train_ends].max() < pd.Timestamp("2022-01-01")


def test_preprocessing_fits_only_on_the_training_part():
    """Doi gia tri NGOAI phan hoc thi scaler va danh sach cot giu nguyen."""
    rng = np.random.default_rng(0)
    idx = pd.date_range("2020-01-01", periods=600, freq="5min")
    df = pd.DataFrame(rng.normal(size=(600, 4)), index=idx, columns=list("abcd"))
    mask = np.zeros(600, bool); mask[:300] = True
    m1, cols1 = prepare_fold_matrix(df, mask, clip=8.0)
    tampered = df.copy(); tampered.iloc[300:] *= 1000.0
    m2, cols2 = prepare_fold_matrix(tampered, mask, clip=8.0)
    assert cols1 == cols2
    np.testing.assert_allclose(m1[:300], m2[:300])


# --------------------------------------------------------------------------- #
# Mo hinh va hoc
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("variant, has_c", [("a", False), ("ac", True)])
def test_probabilities_sum_to_one_and_heads_match_variant(variant, has_c):
    net = ForecastNet(n_features=7, variant=variant)
    out = net(torch.randn(5, 16, 7))
    torch.testing.assert_close(out["prob"].sum(-1), torch.ones(5))
    assert ("ret" in out) == has_c


def _planted(n=4000, f=5, seed=0):
    """Nhan phu thuoc dac trung 0 cua nen cuoi cua so - mang PHAI hoc duoc."""
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, f)).astype("float32")
    label = np.where(x[:, 0] > 0.4, UP, np.where(x[:, 0] < -0.4, DOWN, FLAT)).astype(np.int64)
    ret = x[:, 0].astype("float32")
    return x, label, ret


def test_network_learns_a_planted_signal(tmp_path):
    x, label, ret = _planted()
    ends = np.arange(15, len(x))
    end = np.minimum(np.arange(len(x)), len(x) - 1)       # dap an chi nhin chinh no
    tc = TrainConfig(window=16, max_epochs=8, patience=3, batch=256, lr=3e-3)
    model, hist = train_fold(x, ends, label, ret, end, "a", seed=1, cfg=tc,
                             ckpt_dir=tmp_path, device=torch.device("cpu"))
    p = predict(model, x, ends, tc.window, torch.device("cpu"))
    base = baseline_probs(label[ends])
    assert log_loss(p["prob"], label[ends]) < 0.7 * log_loss(np.tile(base, (len(ends), 1)),
                                                             label[ends])


def test_checkpoint_resume_restores_training_state(tmp_path):
    """Hoc 4 epoch lien = hoc 2 epoch, dung, roi chay tiep tu checkpoint."""
    x, label, ret = _planted(n=1500)
    ends = np.arange(15, len(x))
    end = np.arange(len(x))
    dev = torch.device("cpu")
    full = TrainConfig(window=16, max_epochs=4, patience=99, batch=128)
    m_full, _ = train_fold(x, ends, label, ret, end, "ac", 7, full, tmp_path / "a", dev)

    half = TrainConfig(window=16, max_epochs=2, patience=99, batch=128)
    train_fold(x, ends, label, ret, end, "ac", 7, half, tmp_path / "b", dev)
    m_res, hist = train_fold(x, ends, label, ret, end, "ac", 7, full, tmp_path / "b", dev)

    assert hist["resumed_from_epoch"] == 2
    for a, b in zip(m_full.state_dict().values(), m_res.state_dict().values()):
        torch.testing.assert_close(a, b)


def test_baseline_is_class_frequency_of_the_training_part():
    y = np.array([DOWN] * 5 + [FLAT] * 1 + [UP] * 4)
    np.testing.assert_allclose(baseline_probs(y), [0.5, 0.1, 0.4])
