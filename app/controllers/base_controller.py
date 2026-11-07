"""Base de solicitudes HTTP."""

from http.server import SimpleHTTPRequestHandler

from app.core import PUBLIC, SimpleCookie, datetime, db, hashlib, iso, json, user_payload


class BaseController(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(PUBLIC),**kwargs)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control","no-store, no-cache, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args): print(f"[{self.log_date_time_string()}] {fmt % args}")

    def json(self, status, payload, cookie=None):
        body=json.dumps(payload,ensure_ascii=False,default=lambda value: value.isoformat() if isinstance(value,(datetime,)) else str(value)).encode()
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff")
        if cookie: self.send_header("Set-Cookie",cookie)
        self.end_headers(); self.wfile.write(body)

    def body(self):
        try:
            size=int(self.headers.get("Content-Length","0")); return json.loads(self.rfile.read(size)) if 0 < size <= 100_000 else {}
        except (ValueError,json.JSONDecodeError): return {}

    def session(self):
        cookie=SimpleCookie(self.headers.get("Cookie")); morsel=cookie.get("session")
        if not morsel: return None
        token_hash=hashlib.sha256(morsel.value.encode()).hexdigest()
        with db() as c:
            row=c.execute("SELECT usuario_id FROM sesiones WHERE token_hash=? AND fecha_fin IS NULL AND expira_en>?",(token_hash,iso())).fetchone()
            return user_payload(c,row["usuario_id"]) if row else None

    def require(self, permission=None):
        user=self.session()
        if not user: self.json(401,{"error":"Sesión no válida o vencida."}); return None
        if permission and permission not in user["permisos"]: self.json(403,{"error":"No tiene permiso para esta función."}); return None
        return user
