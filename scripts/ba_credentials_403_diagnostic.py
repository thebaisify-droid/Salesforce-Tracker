"""One-time GET-only WordPress BA delivery credential diagnosis; never print secrets."""
import base64,json,os
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from scripts.ba_wp_rest_routes import AUTH_IDENTITY_URL
HOST="https://jobs.zarafytek.com"
def probe(path,auth=None):
    headers={"Accept":"application/json"}
    if auth:headers["Authorization"]="Basic "+auth
    req=Request(HOST+path,headers=headers,method="GET")
    try:
        with urlopen(req,timeout=20) as res:
            body=json.load(res)
            return {"http":res.status,"wordpress_code":body.get("code") if isinstance(body,dict) else None,
                "user_slug":body.get("slug") if isinstance(body,dict) and res.status==200 and path.startswith("/?rest_route=/wp/v2/users/me") else None}
    except HTTPError as exc:
        raw=exc.read(512)
        try:
            obj=json.loads(raw)
            code=obj.get("code")
        except (ValueError,UnicodeDecodeError):
            code="NON_JSON_RESPONSE"
        return {"http":exc.code,"wordpress_code":code,"server":exc.headers.get("Server","")[:50],"cf_ray":exc.headers.get("CF-Ray","")[:90]}
    except URLError:
        return {"http":None,"wordpress_code":"NETWORK_ERROR"}
def main():
    username=os.getenv("BA_WP_USERNAME","")
    password=os.getenv("BA_WP_APPLICATION_PASSWORD","")
    print(json.dumps({"username_matches":username=="ba-delivery",
        "username_present":bool(username),"password_present":bool(password)}))
    if not username or not password:raise SystemExit("Required secrets absent")
    auth=base64.b64encode((username+":"+password).encode()).decode()
    results={"authenticated_identity":probe(AUTH_IDENTITY_URL.removeprefix(HOST),auth)}
    print(json.dumps(results))
if __name__=="__main__":main()
