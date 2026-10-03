# 008 — LSTM dự báo (tầng ① của MODUS 2)

- **Trạng thái**: đang làm
- **Ngày**: 2026-10-01
- **Ảnh hưởng tới**: `laplace/forecast/` (mới), `pipeline.py` (tách hàm ghép đặc trưng),
  `run_forecast.py`, `run_forecast.bat`; thư mục `experiments/` (không commit)
- **Cấu hình đã chốt**: [KIENTRUC.md](../KIENTRUC.md) mục 3 và mục 10

## 1. Câu hỏi

468 đặc trưng có giúp đoán **giá chạm mốc +1,5 ATR hay −1,5 ATR trước (hay đi ngang)**
tốt hơn việc đoán theo tỷ lệ nhóm không? Đồng thời sinh **dự báo ngoài mẫu 2019–2021**
làm dữ liệu học cho Meta.

## 2. Đầu vào → đầu ra

### Đáp án (nhãn) — head (a), và head (c) ở bản thí nghiệm

| Ký hiệu | Nghĩa | Đơn vị |
|---|---|---|
| *t* | Nến ra quyết định (đã đóng cửa) | — |
| `vao` | Giá vào lệnh = **giá mở cửa nến *t+1*** (cùng quy ước với profit) | điểm |
| `A` | ATR 51 nến tại *t* (chỉ dùng dữ liệu ≤ *t*) | điểm |
| mốc trên / dưới | `vao ± 1,5·A` | điểm |
| `het` | Nến cuối được xét = min(*t*+24, nến cuối cùng của phiên chứa *t*) | chỉ số nến |

- **(a)**: quét các nến *t+1 … het*. Chạm mốc trên trước → **lên** (2); chạm mốc dưới
  trước → **xuống** (0); cùng một nến chạm cả hai → theo giá đóng cửa nến đó so với `vao`;
  không chạm mốc nào → **đi ngang** (1).
- **(c)**: `(giá đóng cửa nến het − vao) / A`, đơn vị **ATR**.
- **Không có nhãn** khi nến *t+1* sang phiên khác (quyết định ở nến cuối phiên) hoặc
  `A` chưa xác định.

### Mô hình

```
64 nến × F cột → Linear(F→64)+tanh → LSTM(64→64) → h_t (64 số)
                                                     ├→ head (a): MLP → 3 xác suất
                                                     └→ head (c): MLP → 1 số   [bản a+c]
```
Mất mát: entropy chéo cho (a) + Huber (δ = 1 ATR) cho (c), tỷ lệ 1 : 1.

### Lịch học (mỗi seed)

| Lần học | Học trên | Dự báo cho | Dùng để |
|---|---|---|---|
| vòng 1 | 2018 | 2019 | dữ liệu cho Meta |
| vòng 2 | 2018–2019 | 2020 | dữ liệu cho Meta |
| vòng 3 | 2018–2020 | 2021 | dữ liệu cho Meta |
| cuối | 2018–2021 | valid 2022 | **chấm điểm** |

2 bản (`a`, `ac`) × 4 lần học × **10 seed ngẫu nhiên** = **80 lần học**. Seed bốc
ngẫu nhiên lúc tạo thí nghiệm, ghi vào `run_config.json`.

Trong mỗi lần học: **10 % cuối** (theo thời gian) của phần học dùng để canh dừng; dừng
khi 3 epoch liền không tốt lên; tối đa 30 epoch. Checkpoint `latest` mỗi epoch và `best`
khi tốt lên, ghi nguyên tử; chạy lại cùng lệnh thì chạy tiếp.

### Đầu ra ghi đĩa (`experiments/forecast/<run_id>/`, không commit)

`run_config.json` (seed, cấu hình, commit git, hash dữ liệu, môi trường) · mỗi lần học:
`ckpt_latest.pt`, `ckpt_best.pt`, `history.json`, `pred.parquet` (xác suất từng nến
của giai đoạn dự báo), `metrics.json` · `summary.json` tổng hợp 10 seed.

## 3. Lập luận nhân quả

- **Đặc trưng** tại *t* chỉ dùng dữ liệu ≤ *t* (bất biến #2).
- **Nhãn cố ý nhìn trước** tới nến `het` ≤ *t+24*. Vì vậy:
  - **Cắt bỏ (purge)**: nến *t* chỉ được dùng để học nếu `het(t)` **trước** nến đầu tiên
    của giai đoạn dự báo — nếu không, đáp án của nó chứa giá của năm cần dự báo.
  - Cùng quy tắc giữa phần học và 10 % canh dừng.
- **Tiền xử lý khớp lại ở từng lần học**: bỏ cột trùng lặp và scaler chỉ khớp trên phần
  học của lần đó. Khớp trên cả 2018–2021 thì lần "học 2018 → dự báo 2019" đã ngầm thấy số
  liệu 2019–2021 — trái nguyên tắc ngoài mẫu (KIENTRUC mục 3).
- **Tập test (2023+) không được đụng tới**: mọi giai đoạn dự báo nằm trong train hoặc
  valid.

## 4. Bất biến

**Mới #20** — Mỗi dự báo dùng để học tầng sau (hoặc để chấm) do một mô hình **chưa từng
học dữ liệu tại hay sau thời điểm đó** tạo ra: không nến học nào có đáp án chạm giai đoạn
dự báo, và tiền xử lý chỉ khớp trên phần học.

## 5. Bài test làm spec này thất bại

```
tests/test_forecast.py::test_barrier_label_matches_hand_example
tests/test_forecast.py::test_label_never_crosses_session_end
tests/test_forecast.py::test_return_target_is_in_atr_units
tests/test_forecast.py::test_training_labels_never_reach_the_predicted_period   (#20)
tests/test_forecast.py::test_preprocessing_fits_only_on_the_training_part       (#20)
tests/test_forecast.py::test_schedule_never_predicts_the_test_set
tests/test_forecast.py::test_probabilities_sum_to_one_and_heads_match_variant
tests/test_forecast.py::test_network_learns_a_planted_signal
tests/test_forecast.py::test_checkpoint_resume_restores_training_state
tests/test_forecast.py::test_baseline_is_class_frequency_of_the_training_part
```

## 6. Tiêu chí chấp nhận

**Phần code** (spec này):

| Tiêu chí | Ngưỡng |
|---|---|
| Bài test mục 5 + toàn bộ suite | xanh |
| Chạy thử ngắn trên GPU (1 seed, 1 epoch, 2 bản, 4 lần học) | chạy hết, ghi đủ file, đo thời gian/epoch |
| `run_forecast.bat` | kiểm tra môi trường, chạy tiếp được sau khi ngắt |

**Phần kết quả** (lần chạy thật của người dùng, đặt trước khi chạy). Chấm trên **valid
2022**, sai số = entropy chéo của head (a) (nats, nhỏ hơn là tốt hơn):

| Câu hỏi | Kết luận "có" khi |
|---|---|
| LSTM (a) có hơn đoán theo tỷ lệ nhóm? | Trung bình 10 seed tốt hơn mốc **và** ≥ 8/10 seed tốt hơn mốc |
| Head (c) có giúp head (a)? | Sai số (a) của bản `ac` thấp hơn bản `a` hơn 2 lần sai số chuẩn của chênh lệch giữa 10 seed |
| Xác suất có đúng? | Báo bảng "nói X % thì xảy ra bao nhiêu %" theo 10 khoảng; **không đặt ngưỡng** — chưa có cơ sở. Lệch thì **không** sửa ở tầng LSTM: Meta tự hiệu chỉnh (chốt 2026-10-03) |

Không chấm bằng tỷ lệ đoán đúng. Tập test: không nhìn.

---

## Kết quả phần code (2026-10-01)

| Tiêu chí | Kết quả |
|---|---|
| 11 bài test mục 5 | **xanh** |
| Chạy thử ngắn trên GPU | **đạt** — 8 lần học, đủ file. **0,2–0,5 giây/epoch** → chạy thật 80 lần × tối đa 30 epoch ≈ 15 phút |
| `run_forecast.bat` | đã viết |

Số nến mỗi vòng: oof_2019 học 12.737 → dự báo 12.739 · oof_2020 25.476 → 12.848 ·
oof_2021 38.324 → 12.744 · final 51.068 → valid 12.596.

### Phát hiện: tiêu chí ở mục 6 quá dễ — chờ người dùng quyết

Chạy thử 1 epoch đã "tốt hơn mốc" trên valid 2022 (0,8467 so với 0,9207). Kiểm tra lại:
nhãn bị cắt ở cuối phiên nên gần cuối phiên gần như chắc chắn **đi ngang** (nến áp chót:
100 %), và LSTM có cột vị trí trong phiên. Một **mốc chỉ biết giờ trong phiên** (tỷ lệ
nhóm theo từng nến trong ngày, khớp trên train) đạt **0,7873 — tốt hơn cả LSTM**. Riêng
phần đoán hướng (bỏ nến đi ngang): LSTM 0,6867, mốc 0,6928.

Giữ tiêu chí cũ thì lần chạy thật gần như chắc chắn "đạt" mà không chứng minh gì về hướng.
Đề xuất đổi mốc — xem tin nhắn cùng ngày. Đây là đổi tiêu chí **chặt hơn**, không nới.
