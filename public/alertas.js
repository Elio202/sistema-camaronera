let alerts=[],currentUser=null;

function alertDate(value) {
    if (!value) return "—";
    return new Date(value.replace(" ","T")).toLocaleString("es-GT",{dateStyle:"short",timeStyle:"short"});
}

function renderAlerts() {
    const query=$("#alertSearch").value.trim().toLowerCase();
    const module=$("#moduleFilter").value;
    const state=$("#stateFilter").value;
    const level=$("#levelFilter").value;
    const filtered=alerts.filter(item =>
        (!query || [item.titulo,item.descripcion,item.modulo].some(value => String(value).toLowerCase().includes(query))) &&
        (!module || item.modulo===module) && (!state || item.estado===state) && (!level || item.nivel===level));
    $("#alertRows").innerHTML=filtered.map(item => `<tr class="alert-row alert-${safe(item.nivel).toLowerCase()}">
        <td>${safe(alertDate(item.generada_en))}</td><td>${safe(item.modulo)}</td>
        <td class="name-cell"><b>${safe(item.titulo)}</b><small>${safe(item.descripcion)}</small></td>
        <td><span class="badge alert-level">${safe(item.nivel)}</span></td>
        <td><span class="badge alert-state ${item.estado==='Resuelta'?'off':''}">${safe(item.estado)}</span></td>
        <td>${safe(item.atendida_por_nombre || "—")}</td>
        <td>${item.estado==='Pendiente' && currentUser.permisos.includes('alertas.atender')?`<button class="action" data-attend="${item.id}">Marcar atendida</button>`:'—'}</td>
    </tr>`).join("") || '<tr><td colspan="7">No hay alertas que coincidan con los filtros.</td></tr>';
}

async function loadAlerts() {
    const data=await api("/api/alertas");
    alerts=data.alertas;
    $("#pendingAlerts").textContent=data.totales.Pendiente;
    $("#attendedAlerts").textContent=data.totales.Atendida;
    $("#resolvedAlerts").textContent=data.totales.Resuelta;
    const selected=$("#moduleFilter").value;
    const modules=[...new Set(alerts.map(item => item.modulo))].sort();
    $("#moduleFilter").innerHTML='<option value="">Todos los módulos</option>'+modules.map(value => `<option>${safe(value)}</option>`).join("");
    $("#moduleFilter").value=selected;
    renderAlerts();
}

(async () => {
    currentUser=await initSession();
    await loadAlerts();
    ["#alertSearch","#moduleFilter","#stateFilter","#levelFilter"].forEach(selector => $(selector).oninput=renderAlerts);
    $("#alertRows").onclick=async event => {
        const id=event.target.dataset.attend;
        if (!id || !confirm("¿Confirma que esta alerta ya fue atendida?")) return;
        try {
            await api(`/api/alertas/${id}`,{method:"PATCH",body:JSON.stringify({estado:"Atendida"})});
            await loadAlerts();
            showMessage($("#alertMessage"),"La alerta fue marcada como atendida.",true);
        } catch (error) { showMessage($("#alertMessage"),error.message); }
    };
})().catch(error => showMessage($("#alertMessage"),error.message));
