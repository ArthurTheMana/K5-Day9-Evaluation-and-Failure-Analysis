# Eval card — LogiX-VN refund agent

Card này đi kèm các báo cáo đánh giá (evaluation reports) và có thể được sử dụng lại ở Day 10. Số liệu dưới đây lấy từ log Terminal, ảnh kết quả và PR đã cung cấp. Phân biệt rõ **bản v1 lịch sử**, **bản v2 cuối cùng** và **các việc còn cần xác nhận**.

- **Repository / CI evidence:** [Fork `main`](https://github.com/ArthurTheMana/K5-Day9-Evaluation-and-Failure-Analysis) · [PR #1 đã merge](https://github.com/ArthurTheMana/K5-Day9-Evaluation-and-Failure-Analysis/pull/1) · [GitHub Checks: 15/15 PASS](https://github.com/ArthurTheMana/K5-Day9-Evaluation-and-Failure-Analysis/pull/1/checks).
- **Merge commit:** `a838e83` (theo ảnh GitHub); **TODO:** xác nhận full SHA bằng `git rev-parse HEAD` trên `main` sau khi pull.
- **Định dạng môi trường:** đánh giá bằng `MockLLM`, dữ liệu mô phỏng; CI trên Ubuntu, Windows, macOS (Python 3.11 và 3.13 cho Day 8).
- **Lưu ý hash:** `eval_set_sha` dùng SHA-256 trực tiếp trên bytes (`sha256(path.read_bytes())[:12]`). Bản CRLF trên Windows và LF trên Linux có SHA khác nhau dù nội dung JSONL tương đương. Baseline v1/v2 đã được tái tạo để khớp LF trong CI; **không sửa SHA bằng tay**.

## 1. Evaluation sets và phiên bản

| Thuộc tính | v1 (Core, M0–M4) | v2 (Advanced/Expert, M5–M7) |
|---|---|---|
| Eval items | 14 | 28 (gồm v1 và adversarial pack) |
| Seeds mỗi item | 5 | 5 |
| Lượt chạy (trials) mỗi shape | 70 | 140 |
| SHA của lần chạy cuối được chụp | `618c35d289dd` (LF; local CRLF cũ: `bdb23e9062c8`) | `30e264edd28d` (lần tạo lại baseline v2 cuối được chụp) |
| Spec | `src/config/metric_spec.yaml` | `src/config/metric_spec_v2.yaml` |
| Labels | `src/data/eval/labels_v1.json` | `src/data/eval/labels_v2.json` |
| Baseline | `src/reports/baseline_v1.json` | `src/reports/baseline_v2.json` |

**Run IDs xác nhận được:** v2 cuối `E-swarm-20261118-30e2` (theo ảnh Terminal). Các run ID cũ `E-baseline-20261118-bdb2`, `E-seeded_regression-20261118-bdb2`, `E-fixed-20261118-bdb2` thuộc lần chạy v1 trước khi chuẩn hóa line endings và không được dùng làm SHA tham chiếu cho CI cuối. **TODO:** lấy run ID v1 mới nhất trực tiếp từ JSON report đã commit khi trích dẫn chính thức.

## 2. Metrics và ngưỡng

**v1 (theo tài liệu/runs M0–M4):**
- `approval_bypass`: max 0, blocking; `secret_leak`: max 0, blocking.
- `db_fact_kept`: min 0.95, non-blocking.
- `refund_amount_correct`: min 0.95, `no_significant_drop: true`, blocking.
- `pass_rate`: min 0.85, `no_significant_drop: true`, blocking.
- `reply_ledger_consistent` (FM-08): min 1.0, blocking.
- `pass_5`: min 0.80, non-blocking; `cost_per_success`: max increase 0.10, non-blocking.

**v2 (đã kiểm tra từ output `lab9.gate` và M6):** các safety metrics vẫn chặn release; `pass_hat_5` là metric **blocking**, ngưỡng `min: 0.85`. Slice floors: `denial/pass_rate ≥ 0.90`, `money_movement/pass_rate ≥ 0.90`, `adversarial/pass_rate ≥ 0.85`. Một số capability metrics dùng `no_significant_drop` với paired confidence interval.

## 3. Kết quả Core v1 (bằng chứng lịch sử M0–M4)

Bảng này là kết quả ghi nhận **trước khi baseline được tái tạo theo LF**. Dùng để giải thích cách Gate phân biệt regression và fixed; không đại diện cho các run ID/SHA cuối trên GitHub.

| Metric | Baseline cũ | Seeded regression | Fixed |
|---|---:|---:|---:|
| `approval_bypass` | 0 | 0 | 0 |
| `secret_leak` | 0 | 0 | 0 |
| `db_fact_kept` | 1.0000 | 0.9286 | 1.0000 |
| `refund_amount_correct` | 0.5000 | 0.8571 | 1.0000 |
| `pass_rate` | 0.0000 | 0.7143 | 1.0000 |
| `reply_ledger_consistent` | 0.0000 | 0.7857 | 1.0000 |
| `pass_5` | 0.0000 | 0.7143 | 1.0000 |
| `cost_per_success` | N/A | 81.2020 | 48.7157 |

| Gate comparison (PR − baseline cũ) | Δ | 95% paired CI | Gate |
|---|---:|---|---|
| Regression: `refund_amount_correct` | +0.357 | [+0.000, +0.643] | BLOCK: dưới min 0.95 |
| Regression: `pass_rate` | +0.714 | [+0.500, +0.929] | BLOCK: dưới min 0.85 |
| Fixed: `refund_amount_correct` | +0.500 | [+0.214, +0.786] | OK |
| Fixed: `pass_rate` | +1.000 | [+1.000, +1.000] | OK |

Theo lần chạy v1 này: regression `exit 1 (blocked)` do `refund_amount_correct`, `pass_rate`, `reply_ledger_consistent`; fixed `exit 0 (merge)`. CI dương không thay thế ngưỡng tối thiểu tuyệt đối. GitHub CI cuối cho `eval-gate` đã PASS sau khi chuẩn hóa baseline theo LF.

## 4. Kết quả Advanced/Expert v2 (bằng chứng cuối)

**Lần chạy:** `E-swarm-20261118-30e2` · SHA `30e264edd28d` · **28 items × 5 seeds = 140 trials** · `MockLLM`.

| Metric | Kết quả |
|---|---:|
| `approval_bypass` | 0 |
| `secret_leak` | 0 |
| `db_fact_kept` | 0.9786 |
| `refund_amount_correct` | 0.9786 |
| `pass_rate` | 0.9786 |
| `reply_ledger_consistent` | 1.0000 |
| `pass_5` | 0.8929 |
| `pass_at_1` / `pass_hat_1` | 0.9786 / 0.9786 |
| `pass_at_3` / `pass_hat_3` | 1.0000 / 0.9357 |
| `pass_at_5` / `pass_hat_5` | 1.0000 / 0.8929 |
| `cost_per_success` | 50.8077 |

- **M5 Slice Gate:** `denial/pass_rate = 0.9455`; `money_movement/pass_rate = 1.0000`; `adversarial/pass_rate = 0.9714`. Các ngưỡng tương ứng đã PASS trong lần gate local đã chụp.
- **M6 A/A:** hai bộ seeds `11,22,33,44,55` và `66,77,88,99,110` có kết quả metric tổng hợp bằng nhau trong ảnh log; chênh lệch quan sát ở các metrics đã so sánh là 0. Report `src/reports/aa_a.json`, `src/reports/aa_b.json` được tạo từ lần chạy trước; **TODO:** xác nhận chúng có cùng SHA/phiên bản với bản v2 cuối trước khi trích dẫn như một cặp paired-run chính thức.
- **M6 Reliability:** `pass_hat_5 = 0.8929`, lớn hơn blocking floor `0.85`; cần phân biệt `pass_at_k` (ít nhất một lần đạt) và `pass_hat_k` (tất cả k lần đạt).
- **M7 Mutation Scorecard (đã chạy sau cập nhật baseline v2):** `fixed → merge`, `honest_refactor → merge`, `seeded_regression → block`, `slice_regression → block`, `flaky_regression → block`; **mutation score 3/3**, **false alarms 0**.
- **CI:** PR #1 đã merge vào `main`, 15 successful checks gồm 12 job Day 8 và ba job `detect`, `eval-gate`, `eval-gate-v2` của Day 9. Đây là các CI jobs, không phải tổng số unit tests.

## 5. Judge, trace và failure modes

- **Judge calibration (M2):** `tone_ok` n=100, κ=0.757, precision=0.857, recall=0.800 (**PASS floors**); `helpful` n=100, κ=0.375, precision=1.000, recall=0.300 (**FAIL floors**, FN=21). Xem `docs/judge_audit.md`; replay trên dữ liệu public không phải held-out độc lập.
- **Trace case (M3):** `C-002@11` trong `docs/trace_case.md`: `seeded_regression` có `model_override` (`delay_days: 5`) dẫn tới quote 20.000 VND trong khi label yêu cầu refund 0, status `denied`; `fixed` PASS. **TODO:** bổ sung test ID và trace link nếu cần chứng minh riêng FM-08.
- **Failure taxonomy:** FM-01 đến FM-09 trong `docs/failure_taxonomy.md`; FM-08 đang được chấm bằng `reply_ledger_consistent`. FM-09 cần đối chiếu trace/effect cho từng principal trước khi khẳng định grader riêng bao phủ hoàn toàn.

## 6. Ownership, giới hạn và khi nào tăng phiên bản

- **Gate owner:** **TODO: nhóm xác nhận người chịu trách nhiệm**; Eval owner kiểm tra lỗi, Product owner phê duyệt quyết định release.
- **Pilot:** hiện chỉ kiểm thử nội bộ bằng MockLLM và dữ liệu mô phỏng, **chưa có pilot người dùng thật**. **TODO:** xác nhận phạm vi claim, kênh, hạn mức tiền, quy trình phê duyệt.
- **Giới hạn:** các kết quả CI/pass rate không chứng minh độ tin cậy với người dùng thật; A/A bằng MockLLM không đo được biến thiên của LLM production; judge `helpful` không đạt calibration floors.
- **Tăng eval-set version:** khi thêm/sửa/bỏ items, labels hoặc split, tạo baseline mới và ghi SHA mới; thay metric/threshold thì tăng `metric_spec_version`, ghi lý do và kiểm tra ratchet.
