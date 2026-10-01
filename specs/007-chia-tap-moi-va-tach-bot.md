# 007 — Chia tập mới, tách đặc trưng bot ra khỏi đầu vào LSTM

- **Trạng thái**: xong
- **Ngày**: 2026-09-28
- **Ảnh hưởng tới**: `config.py`, `scaling.py`, `pipeline.py`, `dataset.py`,
  `build_features.py`, `rl/env.py`, `rl/state.py`; bất biến #4, #6, #9, #19
- **Đánh số lại**: behavior cloning → spec 008 trở đi; bỏ đảo chiều (PPO) làm sau

## 1. Câu hỏi

Người dùng chốt kiến trúc MODUS 2 ([KIENTRUC.md](../KIENTRUC.md)): LSTM dự báo → Meta
→ PPO. Hai việc phải làm trước khi xây LSTM: (1) chia tập theo mốc người dùng đã chốt,
(2) đầu ra bot AFL chỉ đi vào Meta, không còn là đặc trưng của LSTM.

## 2. Đầu vào → đầu ra

### Chia tập (người dùng chốt 2026-09-28)

| Tập | Mốc | Trước (spec 001–006) |
|---|---|---|
| Train | 2018-01-01 → 2021-12-31 | 2017-12-18 → 2024-06-30 |
| Valid | 2022-01-01 → 2022-12-31 | 2024-07 → 2025-06 |
| Test — bài thi cuối | 2023-01-01 → hết dữ liệu (2026-09-04) | 2025-07 → 2026-09 |

Vùng đệm giữ nguyên: bỏ 2 phiên (102 bar) đầu mỗi tập valid và test. Bar trước
`train_start` không thuộc tập nào.

### Đặc trưng bot

| | Trước | Sau |
|---|---|---|
| Cột `bot__*` (đầu vào hai bot, đã đổi đơn vị + dừng hoá) | nằm trong X | **bảng riêng `bot_inputs`**, không qua scaler của X |
| Tín hiệu bot (−1 / 0 / +1) | bảng riêng `signals` | giữ nguyên |
| Người dùng | LSTM | **chỉ Meta** |

Lưu ra đĩa: `bot_inputs.parquet` cạnh `signals.parquet`.

### PPO

Đầu vào trạng thái đang dùng cột `bot__kespt_st_dist_atr`. Bỏ cột này: số hạng tương
tác còn 3 (`ret1`, `ret12`, `ret51`), vector trạng thái từ 10 xuống **9** số.

## 3. Lập luận nhân quả

Không đổi phép biến đổi nào. Scaler, danh sách cột tỉa và bất biến #19 khớp lại trên
train mới 2018–2021. Bảng `bot_inputs` dùng đúng phép biến đổi nhân quả đã có (bất biến
#2, #10).

## 4. Bất biến

- **#6 (sửa)**: Tín hiệu **và đặc trưng** bot không bao giờ nằm trong X. Chúng chỉ nằm ở
  `signals` và `bot_inputs`, dành cho Meta.
- **#9**: cờ `use_bots` nay bật/tắt bảng `bot_inputs`; X không bao giờ có cột `bot__`.
- **#4**: thêm kiểm tra train bắt đầu từ `train_start`.
- **#19**: chạy lại trên train mới. Nếu cột nào vượt 1σ thì báo, không nới ngưỡng.

## 5. Bài test làm spec này thất bại

```
tests/test_bots.py::test_bot_columns_never_in_feature_matrix
tests/test_bots.py::test_bot_inputs_are_kept_for_meta
tests/test_no_lookahead.py::test_split_matches_the_agreed_dates
tests/test_invariants.py::test_disabled_group_leaves_no_columns     (sửa)
tests/test_env.py — cập nhật theo vector trạng thái 9 số
```

## 6. Tiêu chí chấp nhận

Tập test: **không đo hiệu năng mô hình nào**. Đặt trước khi chạy:

| Tiêu chí | Ngưỡng |
|---|---|
| Số bar | train ≈ 51.068; valid ≈ 12.698 − 102; test ≈ 45.824 − 102 |
| X | không còn cột `bot__` nào |
| `bot_inputs` | có các cột lõi của cả hai bot (`kespt_st_dist_atr`, `kespt_storsi`, `roof_filt`, `roof_momz`) |
| Toàn bộ suite | xanh |
| Sổ ghi tập test | cập nhật mốc mới và mọi lần đã nhìn đoạn 2023–2026 |
| Báo cáo build | chỉ in thống kê tín hiệu bot trên train + valid |

Hệ quả: ngưỡng nhiễu (spec 005) vẫn chưa đo lại — nay phải đo trên valid 2022.

---

## Kết quả (2026-09-28)

| Tiêu chí | Kết quả |
|---|---|
| Số bar | **đạt** — train 51.068 (2018-01-02 → 2021-12-31) · valid 12.596 (2022-01-06 → 2022-12-30) · test 45.722 (2023-01-05 → 2026-09-04) |
| X không còn cột `bot__` | **đạt** — X: 496 → **468 cột** (91 cột loại vì trùng lặp, tính lại trên train mới) |
| `bot_inputs` giữ cột lõi hai bot | **đạt** — 34 cột, lưu `bot_inputs.parquet` |
| Báo cáo build chỉ in train + valid | **đạt** |
| Sổ ghi tập test | **đạt** — ghi mốc mới và 7 việc đã dùng đoạn 2023–2026 |
| Bất biến #19 trên train mới | **đạt** (nằm trong suite) |
| Toàn bộ suite | lần 1: 111/112 (xem dưới) → sau khi sửa bài test: **112/112** |

### Một bài test chặt hơn bất biến của nó

`test_windows_stay_inside_their_split` đòi **mọi bar** của cửa sổ train thuộc train. Đúng
trước đây chỉ vì train bắt đầu ở bar đầu tiên của dữ liệu. Nay 63 cửa sổ train đầu lấy
bối cảnh từ cuối 12/2017 — không thuộc tập nào, nằm trước train, không nhìn tương lai.
Bất biến #5 chỉ cấm chạm bar của **tập khác**, và valid/test vẫn luôn lấy bối cảnh từ vùng
đệm. Sửa bài test cho đúng bất biến và mở rộng ra cả ba tập: cửa sổ của mỗi tập không
chứa bar nào của tập khác.
