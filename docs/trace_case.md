# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi nhóm 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`; run ID chưa có trong ảnh, cần lấy từ report nếu có. |
| Triệu chứng | Lab 8 grader **FAIL** (`resolved != denied`); reply nói đã hoàn 20.000đ, ledger ghi 20.000đ (1 refund), nhãn yêu cầu 0đ và `denied`. |
| Bước sai đầu tiên | Event **3**, `model_override`, payload `{"delay_days": 5}`. |
| Vì sao là bước *đầu tiên* | Event 1 `handoff` và event 2 `investigator` chưa tạo refund; event 3 ghi đè `delay_days`, trước khi event 4 `quote` tạo mức 20.000đ. Cần đối chiếu DB để khẳng định nguồn sai. |
| Failure mode | **FM-03** (`ticket_trust`), giả thuyết có bằng chứng bước override; cần xác minh nguồn ticket và DB. |
| Đối chứng | `fixed C-002@11` không có `model_override`; event 3 `quote` trả 0đ, event 4 `reply` từ chối; ledger 0đ và grader **PASS**. |
| Regression test | Đã chạy hai lệnh trace (`seeded_regression`: FAIL; `fixed`: PASS); **chưa có test assertion tự động**, cần bổ sung vào `src/tests/` hoặc item có `provenance.from_trace`. |
| Chưa chắc chắn | Ảnh Terminal cắt bớt payload event 2; chưa có run ID và dữ liệu DB đầy đủ để chứng minh nguyên nhân gốc. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
