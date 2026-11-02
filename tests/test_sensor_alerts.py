import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server


class FakeResponse:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return b'{"sent":true}'


class SensorAlertTests(unittest.TestCase):
    def test_detecta_temperatura_fuera_de_rango(self):
        conditions = server.sensor_conditions({
            "nombre": "Bodega", "temperaturaC": -13,
            "tempMinC": -20, "tempMaxC": -15,
            "enLinea": True, "bateria": "middle"
        })
        temperature = next(item for item in conditions if item["type"] == "Temperatura")
        self.assertTrue(temperature["active"])

    def test_controla_repeticion_y_recuperacion(self):
        alert = {"active": True}
        normal = {"active": False}
        self.assertEqual(server.sensor_notice_action(alert, None, "2026-11-02 10:00:00"), "alert")
        self.assertIsNone(server.sensor_notice_action(alert, {"activo": 1, "ult_env": "2026-11-02 11:00:00"}, "2026-11-02 10:00:00"))
        self.assertEqual(server.sensor_notice_action(alert, {"activo": 1, "ult_env": "2026-11-02 09:00:00"}, "2026-11-02 10:00:00"), "alert")
        self.assertEqual(server.sensor_notice_action(normal, {"activo": 1, "ult_env": "2026-11-02 11:00:00"}, "2026-11-02 10:00:00"), "recovery")

    def test_envia_formato_evolution_sin_exponer_clave(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["key"] = request.headers.get("Apikey")
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        with patch.multiple(server,
            EVOLUTION_API_URL="https://evolution.example",
            EVOLUTION_API_KEY="clave-prueba",
            EVOLUTION_INSTANCE="bodega",
            EVOLUTION_NUMBER="50255550000",
            urlopen=fake_urlopen):
            response = server.send_whatsapp("Mensaje de prueba")

        self.assertEqual(response, {"sent": True})
        self.assertEqual(captured["url"], "https://evolution.example/message/sendText/bodega")
        self.assertEqual(captured["key"], "clave-prueba")
        self.assertEqual(captured["body"], {"number": "50255550000", "text": "Mensaje de prueba"})
        self.assertEqual(captured["timeout"], 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
