# Dashboard refresh status

After every real refresh attempt, the orchestrator writes `state/dashboard_status.json`.

The dashboard should use:

- `last_successful_refresh` and `last_successful_refresh_local_date`;
- `latest_attempt.status`, `reason` and source coverage;
- latest successful insert/update/unchanged/reject counts;
- quality-gate result;
- master-data and role-taxonomy versions.

A failed attempt does not overwrite the timestamp of the last successful refresh. Non-due BST/GMT schedule probes are recorded separately and do not become the latest real attempt.

For an operator-readable view:

```bash
python scripts/show_refresh_status.py
```
