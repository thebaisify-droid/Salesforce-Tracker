"""BA atomic snapshot transport; independent of Salesforce and disabled by default."""
from __future__ import annotations
import argparse,base64,hashlib,json,os
from pathlib import Path
from urllib.request import Request,build_opener,HTTPSHandler,HTTPRedirectHandler
ENDPOINT="https://jobs.zarafytek.com/wp-json/business-analysis-tracker/v1/snapshot"
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError("Redirect refused")
def envelope(snapshot):
    if not isinstance(snapshot,dict) or snapshot.get("schema")!="ba-live-snapshot/v1":
        raise ValueError("Not an approved BA snapshot schema")
    if snapshot.get("quality",{}).get("passed") is not True:
        raise ValueError("QA not passed")
    raw=json.dumps(snapshot,ensure_ascii=False,separators=(",",":"),sort_keys=True).encode("utf8")
    return {"snapshot":raw.decode("utf8"),"sha256":hashlib.sha256(raw).hexdigest()}
def send_once(doc,username,password,*,approved=False,opener=None):
    if not approved or not username or not password:raise ValueError("Dedicated BA delivery approval/credentials absent")
    body=envelope(doc)
    credential=base64.b64encode((username+":"+password).encode("utf8")).decode()
    req=Request(ENDPOINT,data=json.dumps(body).encode("utf8"),method="POST",
        headers={"Authorization":"Basic "+credential,"Content-Type":"application/json","Accept":"application/json"})
    conn=opener or build_opener(HTTPSHandler(),NoRedirect())
    with conn.open(req,timeout=25) as response:
        result=json.load(response)
    if result.get("accepted") is not True or result.get("sha256")!=body["sha256"]:
        raise ValueError("Receiver did not acknowledge checksum")
    return {"accepted":True,"sha256":body["sha256"],"records":result.get("record_count")}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--send",action="store_true")
    args=p.parse_args()
    doc=json.loads(args.input.read_text(encoding="utf8"))
    pkg=envelope(doc)
    if not args.send:
        print(json.dumps({"mode":"DRY_RUN","sha256":pkg["sha256"],"no_http_requests":True}))
        return
    if os.getenv("BA_WP_DELIVERY_APPROVAL")!="EXPLICIT_APPROVAL":
        raise SystemExit("BA delivery not separately approved")
    print(json.dumps(send_once(doc,os.getenv("BA_WP_USERNAME",""),
        os.getenv("BA_WP_APPLICATION_PASSWORD",""),approved=True)))
if __name__=="__main__":main()
