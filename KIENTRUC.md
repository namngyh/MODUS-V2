# MODUS 2 — Kiến trúc

Tài liệu này ghi **những gì đã chốt** và **những gì đang bàn**. Bản đề xuất gốc của người
dùng (ARS + LSTM + Meta-Labeling + PPO + Guardrails) là khung định hướng; mọi chi tiết thi
công vẫn phải qua spec trong [specs/](specs/).

## 1. Luồng dữ liệu

```
Dữ liệu 5 phút ─┬─→ Đặc trưng thị trường (496 cột) → dừng hoá → chuẩn hoá  ─┐
                ├─→ ARS / ARSH        P(trạng thái 1…K)          [bật/tắt]  │
                ├─→ EGARCH-X          σ ngày, z                  [bật/tắt]  ├→ HỢP NHẤT
                └─→ Phân phối (DBB)   σ theo giờ trong phiên, đuôi [bật/tắt] ┘
                                          ↓
                     Lọc đặc trưng: tĩnh (trước LSTM) + động (theo thời điểm t)
                                          ↓
                           LSTM → p_up, p_down, lợi suất kỳ vọng, độ bất định
                                          ↓  (chỉ dự báo NGOÀI MẪU — mục 3)
     tín hiệu 2 bot AFL ─┐
     ARS, rủi ro, đuôi  ─┼──→  META-LABELING  →  P(lệnh thành công)
     dự báo LSTM ────────┘                              ↓
                              trạng thái vị thế ──→  PPO: 2 head entry / exit
                              (PPO KHÔNG nhận h_t của LSTM)
```

Mỗi tầng tách thành module riêng để kiểm tra và làm ablation độc lập: bỏ một tầng thì
tầng sau vẫn chạy được với đầu vào còn lại.

## 2. Vai trò từng tầng

| Tầng | Trả lời câu hỏi | Không làm |
|---|---|---|
| ARS | Thị trường đang ở trạng thái nào, chắc chắn bao nhiêu | Không phải tín hiệu giao dịch |
| EGARCH-X | Hôm nay rủi ro cỡ nào (dữ liệu ngày) | Không dự báo hướng |
| Phân phối (DBB) | Giá có thể dao động rộng tới đâu | Không dự báo hướng |
| LSTM | Tương lai gần: lên hay xuống, bao nhiêu, chắc cỡ nào | Không ra quyết định giao dịch |
| Meta | Dự báo này có đáng vào lệnh trong bối cảnh hiện tại không | Không quyết định khối lượng |
| PPO | Vào / giữ / thoát lệnh | Không được vượt giới hạn rủi ro cứng |

## 3. Nguyên tắc ngoài mẫu (out-of-fold) — áp cho MỌI tầng xếp chồng

> Tại mỗi thời điểm *t*, dự báo dùng để huấn luyện tầng sau phải do một mô hình **chưa
> từng học dữ liệu tại *t* hoặc sau *t*** tạo ra.

Tuyệt đối không huấn luyện Meta bằng dự báo mà LSTM tạo trên chính dữ liệu nó đã học.
Hình dung: học sinh tự chấm bài mình đã học thuộc — điểm cao giả tạo, Meta sẽ tin LSTM
quá mức và sụp khi gặp dữ liệu mới.

Nguyên tắc này áp **cả cho PPO**: PPO phải học trên xác suất mà Meta tạo ngoài mẫu.

### Lịch trong tập train 2018–2021 (bước 1 năm, cửa sổ mở rộng)

| Tầng | Học trên | Dự báo ngoài mẫu cho |
|---|---|---|
| LSTM | 2018 | 2019 |
| LSTM | 2018–2019 | 2020 |
| LSTM | 2018–2020 | 2021 |
| Meta | dự báo ngoài mẫu của LSTM năm 2019 | 2020 |
| Meta | dự báo ngoài mẫu của LSTM 2019–2020 | 2021 |
| **PPO** | **2020–2021**, dùng xác suất Meta ngoài mẫu | — |

Valid (2022) và test (2023 → 2026-09) dùng LSTM học trên 2018–2021 và Meta học trên toàn
bộ dự báo ngoài mẫu 2019–2021.

Hệ quả phải biết: dự báo LSTM cho 2019 đến từ mô hình chỉ học 1 năm, cho 2021 từ mô hình
học 3 năm — chất lượng đầu vào của Meta không đồng đều giữa các năm.

## 4. Meta-Labeling

| | |
|---|---|
| Đầu vào | Dự báo LSTM (`p_up`, `p_down`, lợi suất kỳ vọng, độ bất định); xác suất trạng thái ARS; đặc trưng rủi ro/biến động; đặc trưng phân phối/đuôi; **tín hiệu hai bot AFL** (đã chuẩn hoá bằng Python) |
| Nhãn | Lệnh ứng viên có thành công hay không (chi phí là một tham số) |
| Đầu ra | `P(trade_success)` — một xác suất liên tục, đưa vào PPO làm biến trạng thái |
| Mô hình cơ sở | Hồi quy logistic, cây tăng cường nhỏ, MLP nhỏ — không mặc định dùng mạng lớn |

Tín hiệu bot **không bao giờ** là đầu vào của LSTM (bất biến #6), chỉ vào Meta.

## 5. PPO

- Khung **5 phút** cho mọi tầng.
- **Hai head ra quyết định**: entry (LONG · SHORT · SKIP) khi FLAT; exit (HOLD · EXIT)
  khi đang giữ lệnh. **Không đảo chiều trong một bar**: muốn đổi chiều thì EXIT, về
  FLAT, rồi entry ở bar sau. Head value chỉ dùng khi học.
- Một vị thế tại một thời điểm.
- **Đầu vào của PPO**: `P(trade_success)` của Meta + trạng thái vị thế. **Không nhận `h_t`**
  của LSTM (chốt 2026-10-01).
- **Reward**: `w_R · R + w_C · C`, **bắt đầu ½R + ½C** (chốt 2026-10-01); các thành phần
  thưởng/phạt thêm sau, từng cái một. Thử tỷ lệ khác ở phase PPO.
  Định nghĩa R, C ở CLAUDE.md mục 9.
- **Profit** (đánh giá): khớp ở **giá mở cửa nến kế tiếp** sau nến ra quyết định.

## 6. Bật / tắt từng mô hình phụ trợ

Mỗi mô hình phụ trợ có một cờ trong config. Tắt cờ thì **không còn cột nào** của mô hình
đó trong mọi tầng (mở rộng bất biến #9).

| Cờ | Mô hình | Trạng thái |
|---|---|---|
| `use_ars` | ARSH | **Tắt** — ARSH còn đang phát triển (chưa chốt số trạng thái). Bật khi có v0.6 |
| `use_egarch` | EGARCH-X | chưa làm |
| `use_distribution` | Distributional BB | chưa làm |

## 7. Chia dữ liệu

| Tập | Khoảng | Số bar |
|---|---|---:|
| Train | 2018-01-02 → 2021-12-31 | 51.068 |
| Valid | 2022-01-04 → 2022-12-30 | 12.698 |
| Test — bài thi cuối | 2023-01-03 → 2026-09-04 | 45.824 |

Chạy nhiều lần, mỗi lần một seed **ngẫu nhiên** (ghi lại sau khi bốc, không cố định
trước). Mỗi lần chạy khởi tạo mô hình mới hoàn toàn. Walk-forward toàn bộ dữ liệu: làm
sau.

## 8. Đang bàn

| Vấn đề | Trạng thái |
|---|---|
| Chuyển khung ARS (1 phút) và EGARCH-X (ngày) về 5 phút | **chốt** — mục 9 |
| Học lại ba mô hình phụ trợ chỉ trên dữ liệu trước *t* | **chốt** — mục 9 |
| LSTM dự báo gì | **chốt 2026-10-01** — head (a): giá chạm mốc trên / mốc dưới trước, hay đi ngang (3 nhóm). **Thí nghiệm hai bản**: (a) và (a) + head (c) "sau H nến giá đi bao nhiêu" (tính bằng ATR) |
| Mốc của (a): khoảng cách, thời gian chờ, có qua cuối phiên không | **chốt** — mục 10 |
| Cách học và chấm LSTM | **chốt** — mục 10 |
| Nhãn "thành công" của Meta | chưa bàn |
| Lọc đặc trưng tĩnh và động | chưa bàn |
| Front-end điều khiển config | làm sau khi LSTM chạy được |
| **Tối ưu số nến LSTM nhìn lại** (hiện 64 nến, chọn ở spec 002, chưa thử giá trị khác) | việc cần làm — thí nghiệm khi LSTM dự báo chạy được, chấm trên valid nhiều seed |
| Tối ưu độ dài `h_t` (hiện 64 số; thử 96, 128) | việc cần làm — cùng đợt với dòng trên |
| **Tối ưu cửa sổ ATR**: ATR 51 nến (dùng cho R và cho mốc ±1,5 ATR của head (a)) và "1 năm" (dùng cho C) — cả hai đang chọn theo logic, chưa thử giá trị khác | việc cần làm — ghi 2026-10-01 |
| Giới hạn rủi ro cứng, phí | làm sau cùng |

## 9. Mô hình phụ trợ: chuyển khung và học lại (đã chốt)

### Chuyển khung về 5 phút

| Mô hình | Khung gốc | Cách đưa về nến 5 phút |
|---|---|---|
| ARSH | 1 phút | **Trung bình** xác suất trạng thái của 5 phút trong nến. Không lấy phút cuối: ở 1 phút trạng thái đổi 30–52 lần/100 phút và 58–64 % chỉ kéo dài 1 phút (ARSH v0.5, vòng 0–1), nên phút cuối gần như bốc thăm |
| EGARCH-X | ngày | Dự báo cho ngày *d* (chỉ dùng dữ liệu tới hết *d−1*) giữ nguyên cho mọi nến trong ngày, **cộng một cột**: biến động thực tế từ đầu phiên tới nến hiện tại so với mức dự báo cho hôm nay |
| Phân phối (DBB) | 1 và 5 phút | Dùng thẳng bản 5 phút |

Bài test canh: giá trị của mô hình phụ trợ ở nến *t* chỉ dùng dữ liệu tới hết nến *t*.

### Học lại theo từng vòng của MODUS

Mỗi lần LSTM học trên một khoảng (2018; 2018–2019; …; 2018–2021), ARSH và EGARCH-X được
học lại **trên đúng khoảng đó**, đóng băng tham số, rồi chạy tiến theo thời gian để sinh
đầu ra cho khoảng dự báo kế tiếp. DBB tự ước lượng cuốn chiếu từ quá khứ nên không cần
học lại.

Giới hạn phải ghi: **cấu hình** (số trạng thái, dạng phân phối, chu kỳ bán rã…) do các
repo gốc chọn khi có nhìn dữ liệu 2023–2026, tức tập test của MODUS. Học lại tham số thì
sạch; cấu hình thì không. Ghi ở sổ số lần nhìn tập test.

## 10. LSTM dự báo — cấu hình bản đầu (chốt 2026-10-01)

| # | Việc | Chốt |
|---|---|---|
| 1 | Head (a) | Giá chạm **+1,5 ATR(51)** hay **−1,5 ATR(51)** trước, chờ tối đa **24 nến**, **không** chờ qua cuối phiên → 3 nhóm: lên trước / xuống trước / đi ngang. Đo trên train: 44,9 % / 45,5 % / 9,7 % |
| 2 | Head (c) — chỉ ở bản (a)+(c) | Lợi suất sau 24 nến, tính bằng ATR, cách chấm ít nhạy với giá trị cực trị |
| 3 | Tỷ lệ học (a) : (c) | 1 : 1, không tinh chỉnh ở bản đầu |
| 4 | Dừng học | Mỗi vòng giữ 10 % cuối phần học để canh; dừng khi 3 epoch liền không tốt lên; tối đa 30 epoch. Không dùng valid 2022 khi học |
| 5 | Đầu vào | 468 cột hiện có — làm mốc; lọc tương quan 0,95 và mRMR so với mốc này sau |
| 6 | Số lần chạy | **10 seed ngẫu nhiên** mỗi bản (ghi seed sau khi bốc). 2 bản × 3 vòng × 10 seed = 60 lần học |
| 7 | Chấm trên valid 2022 | Sai số xác suất phải thắng mốc "đoán theo tỷ lệ nhóm" rõ hơn mức may rủi giữa các seed; xác suất phải đúng (nói 60 % thì xảy ra ≈ 60 %). Không chấm bằng tỷ lệ đoán đúng |
| 8 | Chạy thật | File `.bat` có checkpoint, chạy tiếp được; người dùng chạy. Thời gian một lần học: chưa đo |
