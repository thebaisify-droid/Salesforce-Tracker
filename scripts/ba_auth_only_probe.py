"""Single GET-only BA WordPress identity probe; never prints credentials."""
import base64,json,os
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from scripts.ba_wp_rest_routes import AUTH_IDENTITY_URL as URL
def main():
    username=os.environ.get("BA_WP_USERNAME","")
    password=os.environ.get("BA_WP_APPLICATION_PASSWORD","")
    if username!="ba-delivery" or not password:
        raise SystemExit("BA secret missing or wrong username")
    token=base64.b64encode((username+":"+password).encode()).decode()
    req=Request(URL,headers={"Authorization":"Basic "+token,"Accept":"application/json","User-Agent":"BA-Snapshot-Delivery-Preflight/1.0"},method="GET")
    try:
        with urlopen(req,timeout=20) as resp:
            val=json.load(resp)
            slug=val.get("slug")
            roles=val.get("roles") or []
            cap=(val.get("capabilities") or {}).get("ba_deliver_snapshot")
            verified=(slug=="ba-delivery" and "ba_snapshot_delivery" in roles
                and "administrator" not in roles and cap is True)
            print(json.dumps({"status":resp.status,"identity_matches":slug=="ba-delivery",
                "restricted_role_verified":verified,"receiver_sent":False,
                "no_post_requests":True}))
            return 0 if verified else 2
    except HTTPError as err:
        raw=err.read(600)
        try:
            payload=json.loads(raw)
            code=payload.get("code","NO_CODE")
        except (ValueError,UnicodeDecodeError):
            code="NON_JSON"
        print(json.dumps({"status":err.code,"wordpress_error_code":code,
            "server":err.headers.get("Server","")[:40],
            "cf_ray":err.headers.get("CF-Ray","")[:90],
            "content_type":err.headers.get("Content-Type","")[:70],
            "no_post_requests":True}))
        return 2
    except URLError:
        print(json.dumps({"status":"NETWORK_ERROR","no_post_requests":True}))
        return 2
if __name__=="__main__":raise SystemExit(main())
