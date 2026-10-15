"""Single GET-only BA WordPress identity probe; never prints credentials."""
import base64,json,os
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
URL="https://jobs.zarafytek.com/wp-json/wp/v2/users/me?context=edit"
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
            print(json.dumps({"status":resp.status,"slug":val.get("slug"),"roles":val.get("roles"),
                "delivery_capability":(val.get("capabilities") or {}).get("ba_deliver_snapshot"),
                "receiver_sent":False}))
    except HTTPError as err:
        raw=err.read(600)
        try:
            payload=json.loads(raw)
            code=payload.get("code","NO_CODE")
        except (ValueError,UnicodeDecodeError):
            code="NON_JSON"
        print(json.dumps({"status":err.code,"wordpress_error_code":code,
            "server":err.headers.get("Server","")[:40],"no_post_requests":True}))
    except URLError:
        print(json.dumps({"status":"NETWORK_ERROR","no_post_requests":True}))
if __name__=="__main__":main()
