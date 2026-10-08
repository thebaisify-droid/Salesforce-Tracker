"""Manual read-only Actor identity and input schema evidence, no scraper runs."""
import json
import os
from urllib.request import Request, urlopen

ACTORS={"CV-Library":"T0edvAvD8lVcvc58G","Totaljobs":"RO7aokuNWfmP0kV0G"}
API="https://api.apify.com/v2/actors/"
def get_json(url,token):
    req=Request(url,method="GET",headers={"Authorization":"Bearer "+token,"Accept":"application/json"})
    with urlopen(req,timeout=45) as resp: return json.load(resp)["data"]
def inspect(token, get=get_json):
    if not token: raise ValueError("APIFY_TOKEN is required")
    items=[]
    for source,aid in ACTORS.items():
        meta=get(API+aid,token)
        build=get(API+aid+"/builds/default",token)
        schema=build.get("inputSchema")
        if isinstance(schema,str):
            try: schema=json.loads(schema)
            except ValueError: schema=None
        fields=(schema or {}).get("properties",{}) if isinstance(schema,dict) else {}
        items.append({"source":source,"actor_id":aid,"confirmed_actor_id":meta.get("id"),
                      "actor_name":meta.get("name"),"actor_owner":meta.get("username"),
                      "default_build_id":build.get("id"),
                      "schema_available":bool(fields),"input_field_names":sorted(fields),
                      "required_field_names":sorted((schema or {}).get("required",[])) if isinstance(schema,dict) else [],
                      "schema_values_redacted":True})
    return {"mode":"READ_ONLY","actor_runs_started":0,"task_updates":0,
            "pilot_authorised":False,"actors":items}
def main():
    token=os.environ.get("APIFY_TOKEN","")
    report=inspect(token)
    if any(x["actor_id"] != x["confirmed_actor_id"] for x in report["actors"]):
        raise ValueError("Actor identity mismatch")
    if any(not x["schema_available"] for x in report["actors"]):
        raise ValueError("Actor schema unavailable; no pilot authorisation")
    with open("actor-schema-evidence.json","w",encoding="utf-8") as f:
        json.dump(report,f,indent=2)
    print("Actor schema metadata retrieved and redacted for",len(report["actors"]),"Actors; no runs started")
if __name__=="__main__":main()
