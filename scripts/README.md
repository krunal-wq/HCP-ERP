# scripts/

One-off / manual scripts. **App inhe import nahi karta** — sirf manually chalaye jaate hain.
Har file ke top pe path-bootstrap header hai, isliye **project root se** chalayein:

```
python scripts/migrations/<name>.py
```

| Folder         | Kya hai                                                        |
|----------------|---------------------------------------------------------------|
| `migrations/`  | DB schema changes — `add_*`, `migrate_*`, `salary_config_migrate` |
| `seeds/`       | Seed/test data — `seed_*`, `rd_seed`, `insert_test_data`       |
| `fixes/`       | Data repair — `fix_*`, `reset_*`, `force_sync_*`, `cleanup_*`, `update_*` |
| `diagnostics/` | Read-only checks — `diagnose_*`, `debug_*`, `check_*`, `test_mail` |
| `maintenance/` | Cleanup/patch — `clean_*`, `setup_qc_module`, `patch_*`, `apply_*` |

> ⚠️ `fixes/`, `migrations/`, `maintenance/` DB ko modify karte hain — chalane se pehle backup le lein.
