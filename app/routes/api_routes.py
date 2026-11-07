"""Catálogo central de rutas de la API.

El catálogo documenta los recursos públicos. ``http_routes`` ensambla los
controladores separados por método HTTP sin cambiar las URL de la aplicación.
"""

ROUTE_GROUPS = {
    "autenticacion": ("/api/login", "/api/logout", "/api/me"),
    "usuarios": ("/api/usuarios", "/api/roles", "/api/permisos"),
    "piscinas": ("/api/piscinas", "/api/ciclos", "/api/historial-ciclos"),
    "personal": ("/api/colaboradores", "/api/actividades", "/api/personal-opciones"),
    "inventario": ("/api/productos", "/api/movimientos", "/api/inventario-opciones"),
    "operacion": ("/api/calidad", "/api/aireacion", "/api/alertas"),
    "analitica": ("/api/resumen", "/api/reportes", "/api/dashboard"),
    "monitoreo": ("/api/monitoreo",),
}
