function dashboardDate(value) {
    return value ? new Date(value).toLocaleString("es-GT", {dateStyle: "short", timeStyle: "short"}) : "—";
}

function dashboardTemperaturePosition(sensor) {
    const minimum = Number(sensor.tempMinC), maximum = Number(sensor.tempMaxC), value = Number(sensor.temperaturaC);
    if (![minimum, maximum, value].every(Number.isFinite) || maximum <= minimum) return 50;
    return Math.max(0, Math.min(100, (value - minimum) * 100 / (maximum - minimum)));
}

const SENSOR_CACHE_KEY="pacificGoldLastMonitor";
function cachedDashboardSensor(){
    try{return JSON.parse(localStorage.getItem(SENSOR_CACHE_KEY)||"null")?.sensores?.[0]||null;}
    catch{return null;}
}

function renderDashboardSensor(sensor,offline=false){
    $("#dashSensorName").textContent = sensor.nombre || "Monitoreo ambiental";
    $("#dashTemperature").textContent = sensor.temperaturaC ?? "—";
    $("#dashHumidity").textContent = sensor.humedadPct ?? "—";
    const online=!offline&&Boolean(sensor.enLinea);
    $("#dashSensorState").textContent = online ? (sensor.estado || "En línea") : "Sin conexión";
    $("#dashSensorState").className = `dashboard-state ${online && String(sensor.estado).toUpperCase() === "OK" ? "ok" : "alert"}`;
    $("#dashSensorRange").textContent = `Rango ${sensor.tempMinC ?? "—"} a ${sensor.tempMaxC ?? "—"} °C`;
    $("#dashSensorTime").textContent = dashboardDate(sensor.ultimoDatoEn);
    $("#dashSensorBattery").textContent = `Batería: ${{high:"alta",middle:"media",low:"baja"}[String(sensor.bateria || "").toLowerCase()] || sensor.bateria || "—"}`;
    $("#dashTempMarker").style.left = `${dashboardTemperaturePosition(sensor)}%`;
}

async function loadDashboardSensor(force = false) {
    const message = $("#dashSensorMessage");
    try {
        const {monitoreo} = await api(`/api/monitoreo${force ? "?actualizar=1" : ""}`);
        const sensor = monitoreo.sensores[0];
        if (!sensor) throw new Error("No hay sensores disponibles.");
        localStorage.setItem(SENSOR_CACHE_KEY,JSON.stringify(monitoreo));
        renderDashboardSensor(sensor);
        message.textContent = "";
    } catch (error) {
        const sensor=cachedDashboardSensor()||{nombre:"Sensor ambiental",temperaturaC:null,humedadPct:null,tempMinC:null,tempMaxC:null,ultimoDatoEn:null,bateria:null};
        renderDashboardSensor(sensor,true);
        showMessage(message,`Sensor desconectado. ${error.message}`);
    }
}

(async () => {
    const user = await initSession();
    const routePermissions = {
        "/piscinas.html": "piscinas.ver",
        "/personal.html": "personal.ver",
        "/inventario.html": "inventario.ver",
        "/alertas.html": "alertas.ver",
        "/aireacion.html": "aireacion.ver",
        "/calidad.html": "calidad_agua.ver",
        "/monitoreo.html": "monitoreo.ver"
    };
    document.querySelectorAll("main a[href]").forEach(link => {
        const route = new URL(link.href, location.origin).pathname;
        const permission = routePermissions[route];
        if (permission && !user.permisos.includes(permission)) link.hidden = true;
    });
    const cardPermissions = {
        availablePoolCount: "piscinas.ver", activePoolCount: "piscinas.ver",
        staffCount: "personal.ver", pendingCount: "personal.ver", overdueCount: "personal.ver",
        lowCount: "inventario.ver", qualityAlertCount: "calidad_agua.ver",
        aeratorOnCount: "aireacion.ver", lowOxygenCount: "aireacion.ver",
        alertCount: "alertas.ver"
    };
    for (const [id, permission] of Object.entries(cardPermissions)) {
        if (!user.permisos.includes(permission)) $("#" + id).closest("a").hidden = true;
    }
    const {
        resumen
    } = await api("/api/resumen");
    $("#availablePoolCount").textContent = resumen.piscinas_disponibles ?? "—";
    $("#activePoolCount").textContent = resumen.piscinas_activas ?? "—";
    $("#staffCount").textContent = resumen.colaboradores ?? "—";
    $("#pendingCount").textContent = resumen.pendientes ?? "—";
    $("#overdueCount").textContent = resumen.vencidas ?? "—";
    $("#lowCount").textContent = resumen.productos_bajos ?? "—";
    $("#qualityAlertCount").textContent = resumen.calidad_fuera ?? "—";
    $("#aeratorOnCount").textContent = resumen.aireadores_encendidos ?? "—";
    $("#lowOxygenCount").textContent = resumen.aireacion_baja ?? "—";
    $("#alertCount").textContent = resumen.alertas_pendientes ?? "—";
    if (user.permisos.includes("monitoreo.ver")) {
        await loadDashboardSensor();
        $("#dashRefreshSensor").onclick = () => loadDashboardSensor(true);
        setInterval(() => loadDashboardSensor(true), 60000);
    } else {
        $("#dashboardMonitor").hidden = true;
    }
})().catch(err => alert(err.message));
