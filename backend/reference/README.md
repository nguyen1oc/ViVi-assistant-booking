# Vietnam Administrative Reference 2025

`vietnam_admin_units_2025.csv` contains the 34 province-level units and 3,321
commune-level units effective from 2025-07-01 under Decision
19/2025/QD-TTg. District rows are intentionally absent because the decision
defines independent province and commune-level code lists for the current
two-tier model.

Official sources:

- Decision page: <https://vanban.chinhphu.vn/?pageid=27160&docid=214409>
- Gazette 919-920 (provinces through Ha Tinh):
  <https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2025/6/45430/57438-1-2025919-92019-2025-qd-ttg.pdf>
- Gazette 921-922 (Quang Tri through Ca Mau):
  <https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2025/6/45430/57441-1-2025921-92219-2025-qd-ttg.pdf>

The builder refuses to write output unless it extracts exactly 34 provinces,
3,321 unique commune-level codes, and at least one commune-level row for every
province. Example after extracting both PDFs with `pdftotext -layout -enc UTF-8`:

```powershell
python backend/scripts/build_vietnam_admin_reference.py `
  --source-text gazette-919-920.txt gazette-921-922.txt
```

The generated CSV is a source reference. PostgreSQL remains the application
source of truth; `enrich_postgres_reference_data.py` validates and imports the
reference, maps all 319 showroom addresses uniquely, and derives operational
rows from existing slots and assignments.
