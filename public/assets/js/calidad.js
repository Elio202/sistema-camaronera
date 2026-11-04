let measurements=[];
let currentUser=null;

function localDateTime(date=new Date()) {
    const offset=date.getTimezoneOffset()*60000;
    return new Date(date-offset).toISOString().slice(0,16);
}

function formatDateTime(value) {
    return value ? new Date(String(value).replace(" ","T")).toLocaleString("es-GT") : "—";
}

function render() {
    const query=$("#qualitySearch").value.trim().toLowerCase();
    const state=$("#qualityState").value;
    const rows=measurements.filter(item => (!state || item.estado===state) &&
        [item.piscina,item.responsable,item.estado,item.notas].some(value => String(value||"").toLowerCase().includes(query)));
    $("#qualityRows").innerHTML=rows.map(item => `<tr class="${item.estado==='Fuera de rango'?'quality-warning':''}">
        <td>${formatDateTime(item.fecha)}</td><td><b>${safe(item.piscina)}</b></td><td>${safe(item.responsable)}</td>
        <td>${Number(item.oxigeno).toFixed(2)} mg/L</td><td>${Number(item.temp).toFixed(2)} °C</td>
        <td>${Number(item.ph).toFixed(2)}</td><td>${Number(item.salinidad).toFixed(2)} ppt</td>
        <td><span class="badge ${item.estado==='Fuera de rango'?'off':''}">${safe(item.estado)}</span>${item.fuera_rango?.length?`<small class="quality-detail">${safe(item.fuera_rango.join(', '))}</small>`:""}</td>
        <td>${safe(item.notas||"—")}</td></tr>`).join("") || '<tr><td colspan="9">No hay mediciones para mostrar.</td></tr>';
}

async function load() {
    const data=await api("/api/calidad");
    measurements=data.mediciones;
    $("#rangeCards").innerHTML=data.rangos.map(item => `<article><span>${safe(item.parametro)}</span><strong>${Number(item.minimo).toFixed(2)} – ${Number(item.maximo).toFixed(2)}</strong><small>${safe(item.unidad)}</small></article>`).join("");
    $("#qualityPool").innerHTML=data.piscinas.map(item => `<option value="${item.id}">${safe(item.codigo)}</option>`).join("");
    $("#qualityStaff").innerHTML=data.responsables.map(item => `<option value="${item.id}">${safe(item.codigo_empleado)} · ${safe(item.nombre)}</option>`).join("");
    render();
}

$("#qualitySearch").oninput=render;
$("#qualityState").onchange=render;
$("#newMeasurement").onclick=()=>{
    $("#qualityForm").reset();
    $("#qualityDate").value=localDateTime();
    $("#qualityMessage").textContent="";
    openDialog($("#qualityDialog"));
};
$("#qualityDialog .close").onclick=()=>closeDialog($("#qualityDialog"));
$("#qualityDialog .cancel").onclick=()=>closeDialog($("#qualityDialog"));
$("#qualityForm").onsubmit=async event=>{
    event.preventDefault();
    try {
        await api("/api/calidad",{method:"POST",body:JSON.stringify({
            piscina_id:$("#qualityPool").value,resp_id:$("#qualityStaff").value,fecha:$("#qualityDate").value,
            oxigeno:$("#qualityOxygen").value,temp:$("#qualityTemp").value,ph:$("#qualityPh").value,
            salinidad:$("#qualitySalinity").value,notas:$("#qualityNotes").value.trim()
        })});
        closeDialog($("#qualityDialog"));
        await load();
    } catch(error) { showMessage($("#qualityMessage"),error.message); }
};

(async()=>{
    currentUser=await initSession();
    $("#newMeasurement").hidden=!currentUser.permisos.includes("calidad_agua.registrar");
    await load();
})().catch(error=>alert(error.message));
