const monitorGrid = $("#monitorGrid");
const monitorMessage = $("#monitorMessage");
const refreshButton = $("#refreshMonitor");

function dateTime(value) {
    if (!value) return "Sin lectura";
    return new Date(value).toLocaleString("es-GT", {dateStyle: "medium", timeStyle: "short"});
}

function batteryLabel(value) {
    return ({high: "Alta", middle: "Media", low: "Baja"})[String(value || "").toLowerCase()] || value || "Sin dato";
}

function temperaturePosition(sensor) {
    const minimum = Number(sensor.tempMinC);
    const maximum = Number(sensor.tempMaxC);
    const temperature = Number(sensor.temperaturaC);
    if (![minimum, maximum, temperature].every(Number.isFinite) || maximum <= minimum) return 50;
    return Math.max(0, Math.min(100, (temperature - minimum) * 100 / (maximum - minimum)));
}

function renderSensor(sensor) {
    const online = Boolean(sensor.enLinea);
    const ok = online && String(sensor.estado).toUpperCase() === "OK";
    const humidity = Math.max(0, Math.min(100, Number(sensor.humedadPct) || 0));
    const position = temperaturePosition(sensor);
    return `<article class="sensor-card ${ok ? "sensor-ok" : "sensor-alert"}">
        <div class="sensor-head"><div><span class="eyebrow">Sensor ambiental</span><h2>${safe(sensor.nombre || "Sensor")}</h2></div><span class="sensor-status ${online ? "online" : "offline"}">${online ? safe(sensor.estado || "En línea") : "Sin conexión"}</span></div>
        <div class="sensor-values">
            <div class="sensor-value temperature"><span>Temperatura</span><strong>${safe(sensor.temperaturaC ?? "—")}<small>°C</small></strong><p>Rango ${safe(sensor.tempMinC ?? "—")} a ${safe(sensor.tempMaxC ?? "—")} °C</p></div>
            <div class="sensor-value humidity"><span>Humedad</span><strong>${safe(sensor.humedadPct ?? "—")}<small>%</small></strong><p>Humedad relativa</p></div>
        </div>
        <div class="sensor-scale temperature-scale"><span style="left:${position}%"></span></div>
        <div class="sensor-range"><small>${safe(sensor.tempMinC ?? "—")} °C</small><small>${safe(sensor.tempMaxC ?? "—")} °C</small></div>
        <div class="humidity-track"><span style="width:${humidity}%"></span></div>
        <dl class="sensor-details"><div><dt>Último dato</dt><dd>${safe(dateTime(sensor.ultimoDatoEn))}</dd></div><div><dt>Batería</dt><dd>${safe(batteryLabel(sensor.bateria))}</dd></div><div><dt>Conexión</dt><dd>${online ? "En línea" : "Desconectado"}</dd></div></dl>
    </article>`;
}

async function loadMonitor(force = false, notify = false) {
    const previousText = refreshButton.textContent;
    refreshButton.disabled = true;
    refreshButton.textContent = "Actualizando...";
    monitorMessage.textContent = "";
    try {
        const {monitoreo} = await api(`/api/monitoreo${force ? "?actualizar=1" : ""}`);
        monitorGrid.innerHTML = monitoreo.sensores.map(renderSensor).join("") || '<article class="empty-state">No hay sensores disponibles.</article>';
        const queryTime = new Date().toLocaleTimeString("es-GT", {hour: "2-digit", minute: "2-digit", second: "2-digit"});
        $("#monitorUpdated").textContent = `Consulta realizada a las ${queryTime}`;
        if (notify) {
            showMessage(monitorMessage, "Lectura actualizada correctamente.", true);
            setTimeout(() => {
                if (monitorMessage.textContent.includes("correctamente")) {
                    monitorMessage.textContent = "";
                    monitorMessage.className = "message";
                }
            }, 3500);
        }
    } catch (error) {
        showMessage(monitorMessage, error.message);
    } finally {
        refreshButton.disabled = false;
        refreshButton.textContent = previousText;
    }
}

refreshButton.onclick = () => loadMonitor(true, true);

(async () => {
    await initSession();
    await loadMonitor();
    setInterval(() => loadMonitor(true, false), 60000);
})().catch(error => showMessage(monitorMessage, error.message));
