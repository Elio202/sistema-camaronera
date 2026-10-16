(async () => {
    await initSession();
    const {
        resumen
    } = await api("/api/resumen");
    $("#availablePoolCount").textContent = resumen.piscinas_disponibles;
    $("#activePoolCount").textContent = resumen.piscinas_activas;
    $("#staffCount").textContent = resumen.colaboradores;
    $("#pendingCount").textContent = resumen.pendientes;
    $("#overdueCount").textContent = resumen.vencidas;
    $("#lowCount").textContent = resumen.productos_bajos
})().catch(err => alert(err.message));
