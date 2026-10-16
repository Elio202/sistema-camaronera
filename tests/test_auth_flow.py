import http.cookiejar
import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import server

class Client:
    def __init__(self,base):
        self.base=base
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(self,path,method="GET",payload=None):
        data=json.dumps(payload).encode() if payload is not None else None
        req=urllib.request.Request(self.base+path,data=data,method=method,headers={"Content-Type":"application/json"})
        try:
            with self.opener.open(req,timeout=5) as response: return response.status,json.loads(response.read())
        except urllib.error.HTTPError as error: return error.code,json.loads(error.read())

class AuthFlowTests(unittest.TestCase):
    prefix=f"test_{int(time.time())}"
    @classmethod
    def setUpClass(cls):
        server.init_db()
        cls.http=ThreadingHTTPServer(("127.0.0.1",0),server.App)
        cls.base=f"http://127.0.0.1:{cls.http.server_port}"
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True); cls.thread.start()
        cls.admin=Client(cls.base)
        status,_=cls.admin.request("/api/login","POST",{"usuario":"admin","password":"Admin123!"})
        if status!=200: raise RuntimeError("No fue posible preparar la sesión administrativa")
    @classmethod
    def tearDownClass(cls):
        with server.db() as c:
            ids=[row["id"] for row in c.execute("SELECT id FROM usuarios WHERE nombre_usuario LIKE ?",(cls.prefix+"%",)).fetchall()]
            for uid in ids:
                c.execute("DELETE FROM sesiones WHERE usuario_id=?",(uid,)); c.execute("DELETE FROM recuperaciones_password WHERE usuario_id=?",(uid,)); c.execute("DELETE FROM usuarios WHERE id=?",(uid,))
        cls.http.shutdown(); cls.http.server_close()
    def create_user(self,suffix,role=5,password="Segura123"):
        payload={"nombre_usuario":self.prefix+suffix,"nombre":"Usuario de Prueba","correo":self.prefix+suffix+"@example.com","password":password,"rol_id":role}
        status,body=self.admin.request("/api/usuarios","POST",payload)
        self.assertEqual(status,201,body); return payload
    def find_user(self,username):
        _,body=self.admin.request("/api/usuarios")
        return next(user for user in body["usuarios"] if user["nombre_usuario"]==username)

    def test_01_rechaza_usuario_inexistente(self):
        status,body=Client(self.base).request("/api/login","POST",{"usuario":"no_existe","password":"Segura123"})
        self.assertEqual(status,401); self.assertEqual(body["error"],"Usuario o contraseña incorrectos.")
    def test_02_rechaza_password_incorrecta_sin_revelar_causa(self):
        status,body=Client(self.base).request("/api/login","POST",{"usuario":"admin","password":"incorrecta"})
        self.assertEqual(status,401); self.assertEqual(body["error"],"Usuario o contraseña incorrectos.")
    def test_03_solo_admite_nombre_de_usuario(self):
        status,_=Client(self.base).request("/api/login","POST",{"usuario":"emarroquin@esteromar.gt","password":"Admin123!"})
        self.assertEqual(status,401)
    def test_04_login_consulta_rol_y_permisos(self):
        client=Client(self.base); status,body=client.request("/api/login","POST",{"usuario":"admin","password":"Admin123!"})
        self.assertEqual(status,200); self.assertEqual(body["usuario"]["rol"],"Administrador"); self.assertIn("usuarios.ver",body["usuario"]["permisos"])
    def test_05_bloquea_panel_sin_sesion(self):
        status,_=Client(self.base).request("/api/me"); self.assertEqual(status,401)
    def test_06_usuario_sin_permiso_no_consulta_usuarios(self):
        payload=self.create_user("_gerencia",5); client=Client(self.base)
        self.assertEqual(client.request("/api/login","POST",{"usuario":payload["nombre_usuario"],"password":payload["password"]})[0],200)
        self.assertEqual(client.request("/api/usuarios")[0],403)
    def test_07_cuenta_inactiva_no_ingresa(self):
        payload=self.create_user("_inactivo"); user=self.find_user(payload["nombre_usuario"])
        self.assertEqual(self.admin.request(f"/api/usuarios/{user['id']}","PATCH",{"estado":0})[0],200)
        self.assertEqual(Client(self.base).request("/api/login","POST",{"usuario":payload["nombre_usuario"],"password":payload["password"]})[0],401)
    def test_08_rechaza_password_debil(self):
        payload={"nombre_usuario":self.prefix+"_debil","nombre":"Usuario Débil","correo":self.prefix+"_debil@example.com","password":"abcdefghi","rol_id":5}
        status,_=self.admin.request("/api/usuarios","POST",payload); self.assertEqual(status,400)
    def test_09_rechaza_correo_y_usuario_invalidos(self):
        base={"nombre":"Usuario Inválido","password":"Segura123","rol_id":5}
        status,_=self.admin.request("/api/usuarios","POST",{**base,"nombre_usuario":"mal usuario","correo":"correo-invalido"}); self.assertEqual(status,400)
    def test_10_rechaza_usuario_duplicado(self):
        payload=self.create_user("_duplicado")
        status,_=self.admin.request("/api/usuarios","POST",payload); self.assertEqual(status,409)
    def test_11_logout_invalida_sesion(self):
        client=Client(self.base); self.assertEqual(client.request("/api/login","POST",{"usuario":"admin","password":"Admin123!"})[0],200)
        self.assertEqual(client.request("/api/logout","POST",{})[0],200); self.assertEqual(client.request("/api/me")[0],401)

if __name__=="__main__": unittest.main(verbosity=2)
