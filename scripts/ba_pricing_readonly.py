"""Read current Apify account reserve and five Actor pricing definitions, no paid calls."""
from __future__ import annotations
import json, os
from urllib.parse import quote
from urllib.request import Request,urlopen
from scripts.ba_controlled_refresh import CONFIG, BASE, validate

def get(path,token):
    request=Request(BASE+path,method="GET",
       headers={"Authorization":"Bearer "+token,"Accept":"application/json"})
    with urlopen(request,timeout=25) as response:
        document=json.load(response)
    if not isinstance(document,dict) or not isinstance(document.get("data"),dict):
        raise RuntimeError("Unusable Apify metadata response")
    return document["data"]

def check(config,token,reader=get):
    validate(config)
    if not token:
        raise RuntimeError("Missing APIFY_TOKEN; pricing cannot be verified")
    limits=reader("users/me/limits",token)
    raw_limit=(limits.get("limits") or {}).get("maxMonthlyUsageUsd")
    used=(limits.get("current") or {}).get("monthlyUsageUsd")
    if type(raw_limit) not in (int,float) or abs(raw_limit-19)>0.00001:
        raise RuntimeError("Unexpected monthly Apify account spending limit")
    if type(used) not in (int,float) or used<0 or used>raw_limit:
        raise RuntimeError("Current account usage unavailable")
    actors=[]
    for source in config["sources"]:
        act=reader("acts/"+quote(source["actor"].replace("/","~"),safe="~"),token)
        details=act.get("pricingInfos") or act.get("pricingInfo") or {}
        if isinstance(details,list):
            details=details[-1] if details else {}
        if not isinstance(details,dict):
            details={}
        data={
          "source":source["name"],
          "actor":source["actor"],
          "pricing_model":details.get("pricingModel") or details.get("model"),
          "price_per_unit_usd":details.get("pricePerUnitUsd", details.get("pricePerUnit")),
          "unit_name":details.get("unitName"),
          "pricing_info_fields":sorted(details.keys()),
          "minimal_max_total_charge_usd":details.get("minimalMaxTotalChargeUsd"),
          "platform_usage_paid_by_user":details.get("isPPEPlatformUsagePaidByUser"),
          "declared_max_items":source["max_items"],
          "declared_max_charge_usd":source["max_charge_usd"],
        }
        actors.append(data)
    return {"account_limit_usd":19,
            "account_usage_usd":round(used,4),
            "available_after_salesforce_reserve_usd":round(max(0,raw_limit-used-8),4),
            "actor_pricing":actors,
            "actor_runs_started":0,
            "wordpress_requests":0,
            "pricing_automatically_verified":False}

def validate_cost_models(report, config):
    """Fail closed unless 10 billable items or event caps bound each source."""
    reviewed={row["source"]:row for row in report.get("actor_pricing",[])}
    issues=[]
    for src in config["sources"]:
        name=src["name"]
        row=reviewed.get(name,{})
        model=row.get("pricing_model")
        if model in ("FREE", "FREE_PLAN"):
            continue
        if model in ("PRICE_PER_DATASET_ITEM", "PAY_PER_RESULT"):
            unit=row.get("price_per_unit_usd")
            if type(unit) not in (int,float) or unit < 0:
                issues.append(name+":UNKNOWN_UNIT_PRICE")
            elif src["max_items"] * unit > src["max_charge_usd"] + 1e-9:
                issues.append(name+":PPR_CAP_EXCEEDED")
        elif model in ("PAY_PER_EVENT", "PPE"):
            # PPE maxTotalChargeUsd is enforced by Apify. Reject minimum
            # charges above the authorised cap or uncapped compute charges.
            if not (0 < src["max_charge_usd"] <= 0.50):
                issues.append(name+":INVALID_EVENT_CEILING")
            required=row.get("minimal_max_total_charge_usd")
            if required is not None:
                if type(required) not in (int,float) or required < 0:
                    issues.append(name+":UNKNOWN_MINIMUM_CHARGE")
                elif required > src["max_charge_usd"] + 1e-9:
                    issues.append(name+":ACTOR_MINIMUM_EXCEEDS_CAP")
            if row.get("platform_usage_paid_by_user") is True:
                issues.append(name+":PPE_COMPUTE_CHARGE_NOT_IN_EVENT_CAP")
        else:
            issues.append(name+":UNSUPPORTED_OR_UNKNOWN_PRICING_MODEL")
    if report.get("account_limit_usd")!=19:
        issues.append("ACCOUNT_LIMIT_MISMATCH")
    return {"pricing_guard_passed":not issues,"issues":issues}


def main():
    cfg=json.loads(CONFIG.read_text(encoding="utf8"))
    report=check(cfg,os.getenv("APIFY_TOKEN",""))
    report["pricing_validation"]=validate_cost_models(report,cfg)
    print(json.dumps(report,sort_keys=True))
    if not report["pricing_validation"]["pricing_guard_passed"]:
        raise SystemExit(2)
if __name__=="__main__":
    main()
