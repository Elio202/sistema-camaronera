"""Catálogo central de rutas de la API.

El catálogo documenta qué controlador funcional atiende cada recurso. Durante
la refactorización, los manejadores se extraen gradualmente desde
``controllers.application_controller`` sin cambiar las URL públicas.
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
