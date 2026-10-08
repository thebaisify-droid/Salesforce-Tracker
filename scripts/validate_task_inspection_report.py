"""Validate redacted task-inspection output before artifact upload."""
import argparse
import json
from pathlib import Path

EXPECTED={"CV-Library","Totaljobs"}
def validate(report):
    rows=report.get("tasks")
    errors=[]
    if not isinstance(rows,list) or len(rows)!=2 or {x.get("source") for x in rows if isinstance(x,dict)}!=EXPECTED:
        errors.append("missing_expected_tasks")
    if report.get("actor_runs_started")!=0 or report.get("task_updates")!=0 or report.get("paid_acquisition_approved") is not False:
        errors.append("unsafe_task_activity")
    for row in rows or []:
        if not isinstance(row,dict):
            errors.append("invalid_task_record")
            continue
        if row.get("raw_input_included") is not False:
            errors.append("raw_task_input_must_be_omitted")
        for name in row.get("input_field_names",[]):
            if any(s in str(name).lower() for s in ("token","secret","password","cookie","authorization","apikey","api_key")):
                errors.append("secret_field_name_present")
    return {"passed":not errors,"errors":errors}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    args=p.parse_args()
    result=validate(json.loads(Path(args.input).read_text(encoding="utf-8")))
    print(json.dumps(result,sort_keys=True))
    return 0 if result["passed"] else 2
if __name__=="__main__":
    raise SystemExit(main())
