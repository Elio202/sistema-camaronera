(async () => {
    const user = await initSession();
    const routePermissions = {
        "/piscinas.html": "piscinas.ver",
        "/personal.html": "personal.ver",
        "/inventario.html": "inventario.ver",
        "/alertas.html": "alertas.ver"
    };
    document.querySelectorAll("main a[href]").forEach(link => {
        const route = new URL(link.href, location.origin).pathname;
        const permission = routePermissions[route];
        if (permission && !user.permisos.includes(permission)) link.hidden = true;
    });
    const {
        resumen
    } = await api("/api/resumen");
    $("#availablePoolCount").textContent = resumen.piscinas_disponibles;
    $("#activePoolCount").textContent = resumen.piscinas_activas;
    $("#staffCount").textContent = resumen.colaboradores;
    $("#pendingCount").textContent = resumen.pendientes;
    $("#overdueCount").textContent = resumen.vencidas;
    $("#lowCount").textContent = resumen.productos_bajos;
    $("#alertCount").textContent = resumen.alertas_pendientes
})().catch(err => alert(err.message));
