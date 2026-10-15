"""BA WordPress page updater: opt-in, single request, no redirects or retries.

Requires a separate BA WordPress application credential and explicit release
approval. Never calls Apify and never touches the Salesforce page or receiver.
No production delivery is enabled by CI at introduction.
"""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
from urllib.request import Request, HTTPSHandler, HTTPRedirectHandler, build_opener
from scripts.ba_wordpress_delivery_package import ROOT
from scripts.ba_wp_rest_routes import BA_PAGE_EDIT_URL as PAGE_URL, BA_PAGE_UPDATE_URL as PUT_URL
DEFAULT=ROOT/"business-analysis-tracker/data/wordpress-delivery-preview.json"
APPROVAL="APPROVE_BA_PAGE_49_DELIVERY"
class RefuseRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError("Redirect denied")
def authenticated_request(url,username,password,*,body=None,opener=None):
    if url not in (PAGE_URL,PUT_URL):
        raise ValueError("Unexpected WordPress destination")
    if not username or not password:
        raise ValueError("Dedicated WordPress BA application credentials missing")
    auth=base64.b64encode((username+":"+password).encode("utf8")).decode()
    request=Request(url,method="PUT" if body is not None else "GET",
        data=json.dumps(body).encode("utf8") if body is not None else None,
        headers={"Authorization":"Basic "+auth,"Accept":"application/json",
                 "Content-Type":"application/json"})
    transport=opener or build_opener(HTTPSHandler(),RefuseRedirect())
    with transport.open(request,timeout=25) as response:
        return json.load(response)
def replace_exact(source,start_marker,end_marker,replacement):
    start=source.find(start_marker)
    if start<0 or source.find(start_marker,start+1)>=0:
        raise ValueError("Expected one start marker")
    end=source.find(end_marker,start)
    if end<0:raise ValueError("Missing end marker")
    stop=end+len(end_marker)
    return source[:start]+replacement+source[stop:]
def make_update(raw,package):
    if package.get("schema")!="ba-wordpress-delivery-package/v1" or package.get("page_id")!=49:
        raise ValueError("Unsupported delivery package")
    if package.get("delivery_approved") is not False:
        raise ValueError("Package must be staged, approval is supplied separately")
    if package.get("rows",0)<=0:raise ValueError("No rows")
    updated=replace_exact(raw,'<tbody id="ba-v2-body">','</tbody>',package["table_fragment"])
    updated=replace_exact(updated,'<script type="application/json" id="ba-v2-json">','</script>',package["embedded_json_fragment"])
    return updated
def publish(package,username,password,*,approval,opener=None):
    if approval!=APPROVAL:raise ValueError("BA delivery not approved")
    # GET the protected raw content; never use rendered HTML to replace WP data.
    page=authenticated_request(PAGE_URL,username,password,opener=opener)
    if page.get("id")!=49 or page.get("status")!="publish":
        raise ValueError("Unexpected WordPress page")
    raw=(page.get("content") or {}).get("raw")
    if not isinstance(raw,str):raise ValueError("WordPress raw edit context unavailable")
    new=make_update(raw,package)
    # One PUT, no fallback retries; a separate preflight checks full content.
    result=authenticated_request(PUT_URL,username,password,body={"content":new},opener=opener)
    if result.get("id")!=49:raise ValueError("WordPress returned wrong page ID")
    return {"submitted":True,"page_id":49,"rows":package["rows"],
            "verified_after_delivery":False,"requires_readback":True}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--package",type=Path,default=DEFAULT)
    p.add_argument("--send",action="store_true")
    args=p.parse_args()
    doc=json.loads(args.package.read_text(encoding="utf8"))
    if not args.send:
        print(json.dumps({"status":"DRY_RUN_NO_WORDPRESS_REQUESTS",
                          "page_id":doc["page_id"],"rows":doc["rows"]}))
        return
    if os.getenv("BA_WP_DELIVERY_APPROVAL")!=APPROVAL:
        raise SystemExit("BA publication approval missing")
    result=publish(doc,os.getenv("BA_WP_USERNAME",""),
                   os.getenv("BA_WP_APPLICATION_PASSWORD",""),
                   approval=APPROVAL)
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
