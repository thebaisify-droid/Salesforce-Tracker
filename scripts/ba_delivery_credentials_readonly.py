"""Read-only verification of BA delivery identity and REST route. Never POST."""
import base64,json,os
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
BASE="https://jobs.zarafytek.com/wp-json/"
def check():
    username=os.environ.get("BA_WP_USERNAME","")
    password=os.environ.get("BA_WP_APPLICATION_PASSWORD","")
    if username!="ba-delivery" or not password:
        raise RuntimeError("BA delivery username or application password missing")
    token=base64.b64encode((username+":"+password).encode()).decode()
    headers={"Authorization":"Basic "+token,"Accept":"application/json"}
    req=Request(BASE+"wp/v2/users/me?context=edit",headers=headers,method="GET")
    with urlopen(req,timeout=20) as response:
        user=json.load(response)
    if user.get("slug")!="ba-delivery":
        raise RuntimeError("Authenticated identity mismatch")
    roles=user.get("roles") or []
    caps=user.get("capabilities") or {}
    if "administrator" in roles or "ba_snapshot_delivery" not in roles or caps.get("ba_deliver_snapshot") is not True:
        raise RuntimeError("Identity does not have restricted delivery role/capability")
    # OPTIONS only: do not call the POST handler or transmit any snapshot.
    req=Request(BASE+"business-analysis-tracker/v1/snapshot",headers=headers,method="OPTIONS")
    with urlopen(req,timeout=20) as response:
        route=json.load(response)
    methods=route.get("methods") or []
    if "POST" not in methods:
        raise RuntimeError("BA snapshot receiver POST route unavailable")
    print(json.dumps({"identity":"ba-delivery","restricted_role_confirmed":True,
       "receiver_route_available":True,"wordpress_post_requests":0,
       "snapshots_sent":0,"actor_runs_started":0}))
if __name__=="__main__":
    check()
