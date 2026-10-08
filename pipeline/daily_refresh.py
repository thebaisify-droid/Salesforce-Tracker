from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

COLLECTION_KEYS = ("records", "jobs", "vacancies", "items", "data")


@dataclass
class StepResult:
    name: str
    status: str
    started_at: str
    finished_at: str
    returncode: int | None = None
    command: str | None = None
    output_path: str | None = None
    record_count: int | None = None
    artifact_valid: bool | None = None
    artifact_error: str | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None
    reason: str | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except (OSError, json.JSONDecodeError):
        return default


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def append_ndjson(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def inspect_record_artifact(path: Path) -> tuple[int | None, bool, str | None]:
    if not path.exists():
        return None, False, "collector did not create its output file"
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return None, False, f"could not read collector output: {exc}"
    if not text:
        return None, False, "collector output file is empty"
    try:
        payload = json.loads(text)
        if isinstance(payload, list):
            return len(payload), True, None
        if isinstance(payload, dict):
            for key in COLLECTION_KEYS:
                if key in payload:
                    if isinstance(payload[key], list):
                        return len(payload[key]), True, None
                    return None, False, f"collector output field '{key}' is not a list"
            return None, False, "collector JSON object has no recognised collection key"
        return None, False, "collector JSON must contain records"
    except json.JSONDecodeError:
        count = 0
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                return None, False, f"invalid NDJSON at line {line_no}: {exc.msg}"
            count += 1
        return (count, True, None) if count else (None, False, "collector NDJSON contains no records")


def count_json_records(path: Path) -> int | None:
    count, valid, _ = inspect_record_artifact(path)
    return count if valid else None


def render_command(template: str, values: dict[str, str]) -> str:
    quoted = {key: shlex.quote(value) for key, value in values.items()}
    try:
        return template.format(**quoted)
    except KeyError as exc:
        raise ValueError(f"Unknown command placeholder: {exc.args[0]}") from exc


def run_step(name: str, command: str, cwd: Path, env: dict[str, str], output: Path | None = None) -> StepResult:
    started = utc_now()
    proc = subprocess.run(command, cwd=cwd, env=env, shell=True, text=True, capture_output=True)
    count = valid = error = None
    status = "success" if proc.returncode == 0 else "failed"
    if output is not None:
        count, valid, error = inspect_record_artifact(output)
        if proc.returncode == 0 and not valid:
            status = "failed"
    return StepResult(
        name=name, status=status, started_at=iso_z(started), finished_at=iso_z(utc_now()),
        returncode=proc.returncode, command=command, output_path=str(output) if output else None,
        record_count=count, artifact_valid=valid, artifact_error=error,
        stdout_tail=(proc.stdout or "")[-4000:] or None, stderr_tail=(proc.stderr or "")[-4000:] or None,
        reason=error if status == "failed" and proc.returncode == 0 else None,
    )


def due_now(config: dict[str, Any], now_utc: datetime) -> tuple[bool, str]:
    tz_name = config.get("timezone", "Europe/London")
    hour = int(config.get("scheduled_local_time", "07:15").split(":", 1)[0])
    local = now_utc.astimezone(ZoneInfo(tz_name))
    due = local.hour == hour
    return due, f"{'due' if due else 'not due'} in the {hour:02d}:00 local hour ({tz_name}); local time is {local:%H:%M}"


def successful_refresh_today(state_dir: Path, tz_name: str, now_utc: datetime) -> bool:
    latest = load_json(state_dir / "latest_success.json", {})
    try:
        finished = datetime.fromisoformat(latest["finished_at"].replace("Z", "+00:00"))
        tz = ZoneInfo(tz_name)
        return latest.get("status") == "success" and finished.astimezone(tz).date() == now_utc.astimezone(tz).date()
    except (KeyError, TypeError, ValueError):
        return False


def compact_dashboard_status(state_dir: Path, tz_name: str) -> dict[str, Any]:
    success = load_json(state_dir / "latest_success.json", {}) or {}
    attempt = load_json(state_dir / "latest_attempt.json", {}) or {}
    summary = success.get("summary", {})
    metrics = success.get("metrics", {}) or {}
    attempt_summary = attempt.get("summary", {})
    last = success.get("finished_at")
    local_date = None
    if last:
        try:
            local_date = datetime.fromisoformat(last.replace("Z", "+00:00")).astimezone(ZoneInfo(tz_name)).date().isoformat()
        except ValueError:
            pass
    return {
        "timezone": tz_name,
        "last_successful_refresh": last,
        "last_successful_refresh_local_date": local_date,
        "latest_attempt": {
            "status": attempt.get("status"), "finished_at": attempt.get("finished_at"),
            "reason": attempt.get("reason"), "run_id": attempt.get("run_id"),
            "sources_succeeded": attempt_summary.get("sources_succeeded"),
            "sources_configured": attempt_summary.get("sources_configured"),
        },
        "latest_success": {
            "run_id": success.get("run_id"), "sources_succeeded": summary.get("sources_succeeded"),
            "sources_configured": summary.get("sources_configured"), "raw_records_seen": summary.get("raw_records_seen"),
            "inserted_rows": summary.get("inserted_rows"), "updated_rows": summary.get("updated_rows"),
            "unchanged_rows": summary.get("unchanged_rows"), "rejected_rows": summary.get("rejected_rows"),
            "quality_passed": summary.get("quality_passed"), "master_data_version": metrics.get("master_data_version"),
            "role_taxonomy_version": metrics.get("role_taxonomy_version"),
        },
    }


def build_status(run_id: str, status: str, started: datetime, since: datetime, until: datetime,
                 sources: list[StepResult], transform: StepResult | None, quality_step: StepResult | None,
                 publish: StepResult | None, metrics: dict[str, Any] | None, quality: dict[str, Any] | None,
                 reason: str | None, config_path: str, tz_name: str) -> dict[str, Any]:
    return {
        "run_id": run_id, "status": status, "reason": reason, "timezone": tz_name,
        "started_at": iso_z(started), "finished_at": iso_z(utc_now()),
        "window": {"since": iso_z(since), "until": iso_z(until)}, "config_path": config_path,
        "summary": {
            "sources_configured": len(sources), "sources_succeeded": sum(s.status == "success" for s in sources),
            "raw_records_seen": sum(s.record_count or 0 for s in sources),
            "inserted_rows": (metrics or {}).get("inserted_rows"), "updated_rows": (metrics or {}).get("updated_rows"),
            "unchanged_rows": (metrics or {}).get("unchanged_rows"), "rejected_rows": (metrics or {}).get("rejected_rows"),
            "quality_passed": (quality or {}).get("passed") if quality is not None else None,
        },
        "sources": [asdict(s) for s in sources], "transform": asdict(transform) if transform else None,
        "quality": {"step": asdict(quality_step) if quality_step else None, "report": quality},
        "publish": asdict(publish) if publish else None, "metrics": metrics,
    }


def persist(state_dir: Path, run_dir: Path, status: dict[str, Any], success: bool = False) -> None:
    atomic_write_json(run_dir / "run_status.json", status)
    atomic_write_json(state_dir / "latest_attempt.json", status)
    append_ndjson(state_dir / "refresh_history.ndjson", status)
    if success:
        atomic_write_json(state_dir / "latest_success.json", status)
        atomic_write_json(state_dir / "latest_refresh.json", status)
    atomic_write_json(state_dir / "dashboard_status.json", compact_dashboard_status(state_dir, status.get("timezone", "Europe/London")))


def _placeholders(root: Path) -> dict[str, str]:
    run = root / "runs" / "PRECHECK"
    return {
        "run_id":"PRECHECK", "run_dir":str(run), "raw_dir":str(run / "raw"),
        "since":"2026-10-01T00:00:00Z", "until":"2026-10-02T00:00:00Z",
        "metrics":str(run / "metrics.json"), "quality_report":str(run / "quality_report.json"),
        "status":str(root / "state" / "latest_refresh.json"), "output":str(run / "raw" / "source.json"),
    }


def _python_script_error(command: str, root: Path) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return f"cannot parse command: {exc}"
    if not parts:
        return "command is empty"
    python_names = {"python", "python3", Path(sys.executable).name, sys.executable}
    if parts[0] not in python_names or len(parts) > 1 and parts[1] == "-m":
        return None
    if len(parts) < 2:
        return "python command has no script/module"
    path = Path(parts[1])
    path = path if path.is_absolute() else root / path
    return None if path.exists() else f"referenced Python script does not exist: {path}"


def preflight(config_path: Path) -> dict[str, Any]:
    root = config_path.resolve().parents[1]
    config = load_json(config_path)
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(config, dict):
        return {"ok":False, "errors":[f"invalid config: {config_path}"], "warnings":[]}
    try:
        ZoneInfo(config.get("timezone", "Europe/London"))
        hour, minute = map(int, config.get("scheduled_local_time", "07:15").split(":", 1))
        if not (0 <= hour <= 23 and 0 <= minute <= 59): raise ValueError
    except Exception:
        errors.append("timezone or scheduled_local_time is invalid")

    sources = [s for s in config.get("sources", []) if isinstance(s, dict) and s.get("enabled", True)]
    if not sources: errors.append("no enabled sources configured")
    names = [s.get("name") for s in sources]
    if any(not n for n in names) or len(names) != len(set(names)): errors.append("source names must be present and unique")
    minimum = int(config.get("min_sources_succeeded", len(sources))) if sources else 0
    if sources and not (1 <= minimum <= len(sources)): errors.append("min_sources_succeeded is invalid")
    required = config.get("required_sources", [])
    if not isinstance(required, list) or any(not isinstance(name, str) or not name for name in required):
        errors.append("required_sources must be a list of source names")
        required = []
    unknown_required = sorted(set(required) - set(names))
    if unknown_required:
        errors.append("required_sources contains disabled or unknown sources: " + ", ".join(unknown_required))

    values = _placeholders(root)
    for source in sources:
        name = source.get("name", "<unnamed>")
        if source.get("config"):
            source_cfg = load_json(root / source["config"])
            if not isinstance(source_cfg, dict): errors.append(f"source {name}: source config is missing or invalid")
            elif not source_cfg.get("ready", False): errors.append(f"source {name}: live provider is not configured yet ({root / source['config']})")
        command = source.get("command")
        if not isinstance(command, str) or not command.strip():
            errors.append(f"source {name}: command is missing"); continue
        try: rendered = render_command(command, values)
        except ValueError as exc: errors.append(f"source {name}: {exc}"); continue
        error = _python_script_error(rendered, root)
        if error: errors.append(f"source {name}: {error}")

    steps = config.get("steps", {})
    if config.get("strict_mode", True):
        for name in ("transform", "quality", "publish"):
            if not isinstance(steps.get(name), str) or not steps[name].strip(): errors.append(f"required step '{name}' is missing")
    for name, command in steps.items():
        if isinstance(command, str) and command.strip():
            try: rendered = render_command(command, values)
            except ValueError as exc: errors.append(f"step {name}: {exc}"); continue
            error = _python_script_error(rendered, root)
            if error: errors.append(f"step {name}: {error}")
    return {"ok":not errors, "project_root":str(root), "config_path":str(config_path), "enabled_sources":len(sources),
            "min_sources_succeeded":minimum, "required_sources":required, "errors":errors, "warnings":warnings}


def dry_run_plan(config_path: Path) -> dict[str, Any]:
    root = config_path.resolve().parents[1]
    config = load_json(config_path, {})
    values = _placeholders(root)
    sources = []
    for source in [s for s in config.get("sources", []) if s.get("enabled", True)]:
        local = dict(values); local["output"] = str(Path(values["raw_dir"]) / source.get("output", f"{source['name']}.json"))
        sources.append({"name":source["name"], "command":render_command(source["command"], local)})
    return {"sources":sources, "steps":{k:render_command(v, values) for k,v in config.get("steps", {}).items()},
            "note":"PRECHECK paths are illustrative; no commands were executed."}


def execute(config_path: Path, *, force: bool, scheduled: bool, since_override: str | None = None) -> int:
    root = config_path.resolve().parents[1]
    config = load_json(config_path)
    check = preflight(config_path)
    if not check["ok"]:
        print(json.dumps({"status":"preflight_failed", **check}, indent=2)); return 6
    now = utc_now(); until = now
    since = datetime.fromisoformat(since_override.replace("Z", "+00:00")) if since_override else now - timedelta(hours=int(config.get("lookback_hours", 72)))
    if since.tzinfo is None: since = since.replace(tzinfo=timezone.utc)
    state_dir = root / config.get("state_dir", "state"); runs_dir = root / config.get("runs_dir", "runs")
    tz_name = config.get("timezone", "Europe/London")
    run_id = f"{now:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"; run_dir = runs_dir / run_id; raw_dir = run_dir / "raw"; raw_dir.mkdir(parents=True, exist_ok=True)

    if scheduled and not force:
        due, why = due_now(config, now)
        if not due or successful_refresh_today(state_dir, tz_name, now):
            if due: why = f"a successful refresh is already recorded for today in {tz_name}"
            status = build_status(run_id,"skipped",now,since,until,[],None,None,None,None,None,why,str(config_path),tz_name)
            atomic_write_json(run_dir / "run_status.json", status); append_ndjson(state_dir / "schedule_history.ndjson", status)
            print(json.dumps(status, indent=2)); return 0

    env = os.environ.copy(); assurance = config.get("assurance", {})
    env.update({"PIPELINE_RUN_ID":run_id,"PIPELINE_SINCE":iso_z(since),"PIPELINE_UNTIL":iso_z(until),"PIPELINE_RUN_DIR":str(run_dir),"PIPELINE_MIN_SOURCES":str(config.get("min_sources_succeeded",3))})
    for cfg_key, env_key in (("expected_master_data_version","PIPELINE_EXPECTED_MASTER_DATA_VERSION"),("expected_role_taxonomy_version","PIPELINE_EXPECTED_ROLE_TAXONOMY_VERSION"),("max_rejection_rate","PIPELINE_MAX_REJECTION_RATE")):
        if assurance.get(cfg_key) is not None: env[env_key] = str(assurance[cfg_key])
    values = {"run_id":run_id,"run_dir":str(run_dir),"raw_dir":str(raw_dir),"since":iso_z(since),"until":iso_z(until),"metrics":str(run_dir/"metrics.json"),"quality_report":str(run_dir/"quality_report.json"),"status":str(state_dir/"latest_refresh.json")}

    source_results=[]
    source_cfgs=[s for s in config["sources"] if s.get("enabled",True)]
    for source in source_cfgs:
        output=raw_dir/source.get("output",f"{source['name']}.json"); local=dict(values); local["output"]=str(output)
        source_results.append(run_step(f"collect:{source['name']}",render_command(source["command"],local),root,env,output))
    minimum=int(config.get("min_sources_succeeded",len(source_cfgs)))
    succeeded_names={
        source["name"]
        for source, result in zip(source_cfgs, source_results)
        if result.status=="success"
    }
    required_names=set(config.get("required_sources", []))
    missing_required=sorted(required_names - succeeded_names)
    succeeded_count=len(succeeded_names)
    if missing_required or succeeded_count < minimum:
        if missing_required:
            reason="required source gate failed: " + ", ".join(missing_required)
        else:
            reason=f"source gate failed: {succeeded_count}/{len(source_cfgs)} succeeded; minimum is {minimum}"
        status=build_status(run_id,"failed",now,since,until,source_results,None,None,None,None,None,reason,str(config_path),tz_name)
        persist(state_dir,run_dir,status); print(json.dumps(status,indent=2)); return 2

    steps=config["steps"]
    transform=run_step("transform",render_command(steps["transform"],values),root,env)
    if transform.status!="success":
        status=build_status(run_id,"failed",now,since,until,source_results,transform,None,None,None,None,"transform step failed",str(config_path),tz_name); persist(state_dir,run_dir,status); print(json.dumps(status,indent=2)); return 3
    metrics=load_json(run_dir/"metrics.json")
    if config.get("require_metrics_report",True) and not isinstance(metrics,dict):
        status=build_status(run_id,"failed",now,since,until,source_results,transform,None,None,None,None,"transform completed but metrics.json is missing or invalid",str(config_path),tz_name); persist(state_dir,run_dir,status); print(json.dumps(status,indent=2)); return 3

    quality_step=run_step("quality",render_command(steps["quality"],values),root,env); quality=load_json(run_dir/"quality_report.json")
    valid_quality=isinstance(quality,dict) and isinstance(quality.get("passed"),bool)
    if quality_step.status!="success" or not valid_quality or not quality.get("passed"):
        reason="quality gate failed" if valid_quality else "quality command succeeded but quality_report.json is missing, invalid, or has no boolean 'passed'"
        status=build_status(run_id,"failed",now,since,until,source_results,transform,quality_step,None,metrics,quality,reason,str(config_path),tz_name); persist(state_dir,run_dir,status); print(json.dumps(status,indent=2)); return 4

    publish=run_step("publish",render_command(steps["publish"],values),root,env)
    if publish.status!="success":
        status=build_status(run_id,"failed",now,since,until,source_results,transform,quality_step,publish,metrics,quality,"publish step failed",str(config_path),tz_name); persist(state_dir,run_dir,status); print(json.dumps(status,indent=2)); return 5
    status=build_status(run_id,"success",now,since,until,source_results,transform,quality_step,publish,metrics,quality,None,str(config_path),tz_name)
    persist(state_dir,run_dir,status,True); print(json.dumps(status,indent=2)); return 0


def main() -> int:
    parser=argparse.ArgumentParser(description="Run the UK Salesforce tracker daily refresh pipeline")
    parser.add_argument("--config",default="config/pipeline.json"); parser.add_argument("--force",action="store_true"); parser.add_argument("--scheduled",action="store_true"); parser.add_argument("--since"); parser.add_argument("--check",action="store_true"); parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args(); path=Path(args.config)
    if args.check:
        result=preflight(path); print(json.dumps(result,indent=2)); return 0 if result["ok"] else 6
    if args.dry_run:
        result=preflight(path); print(json.dumps({"preflight":result,"plan":dry_run_plan(path) if result["ok"] else None},indent=2)); return 0 if result["ok"] else 6
    return execute(path,force=args.force,scheduled=args.scheduled,since_override=args.since)


if __name__ == "__main__":
    raise SystemExit(main())
