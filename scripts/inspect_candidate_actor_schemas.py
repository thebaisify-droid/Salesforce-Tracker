"""Read only the default build schemas of the two proven saved-task Actor IDs."""
import argparse
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

ACTORS={"CV-Library":"T0edvAvD8lVcvc58G","Totaljobs":"RO7aokuNWfmP0kV0G"}
SENSITIVE=("secret","token","password","cookie","authorization","api_key","apikey")

def summarise(name, actor_id, response):
    data=response.get("data",{})
    if not isinstance(data,dict) or data.get("actId") not in (actor_id,None):
        raise ValueError("Actor build identity mismatch")
    schema=data.get("actorDefinition",{}).get("input")
    if not isinstance(schema,dict):
        encoded=data.get("inputSchema")
        if not isinstance(encoded,str):
            raise ValueError("No input schema found")
        schema=json.loads(encoded)
    props=schema.get("properties",{})
    if not isinstance(props,dict):
        raise ValueError("Invalid schema properties")
    fields=[]
    for key,value in props.items():
        if any(s in key.lower() for s in SENSITIVE):
            continue
        fields.append({"name":key,"type":value.get("type") if isinstance(value,dict) else None,
                       "required":key in schema.get("required",[])})
    return {"source":name,"actor_id":actor_id,"build_id":data.get("id"),
            "schema_available":True,"fields":sorted(fields,key=lambda x:x["name"]),
            "example_values_included":False}

def inspect():
    output=[]
    for source,actor_id in ACTORS.items():
        url=f"https://api.apify.com/v2/actors/{actor_id}/builds/default"
        request=Request(url,headers={"Accept":"application/json"},method="GET")
        with urlopen(request,timeout=45) as response:
            body=json.load(response)
        output.append(summarise(source,actor_id,body))
    return {"schema":"candidate-actor-input-schema-readonly/v1",
            "actors":output,"actor_runs_started":0,"actor_builds_started":0,
            "production_changes":False,"acquisition_authorised":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    a=p.parse_args()
    path=Path(a.output)
    if path.resolve() in {Path("dashboard/live-data.json").resolve(),
                          Path("config/pipeline.json").resolve()}:
        p.error("Protected path")
    report=inspect()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"actors_inspected":len(report["actors"]),
                      "actor_runs_started":0,"actor_builds_started":0}))
if __name__=="__main__":
    main()
