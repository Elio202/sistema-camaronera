let measurements=[],ranges=[];
let currentUser=null;
const canRegister=()=>currentUser?.permisos.includes("calidad_agua.registrar");
const canEditRanges=()=>currentUser?.permisos.includes("calidad_agua.atender_alertas");

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
        <td>${safe(item.notas||"—")}</td><td>${canRegister()?`<button class="action" data-edit="${item.id}">Editar</button><button class="action danger-text" data-delete="${item.id}">Eliminar</button>`:"—"}</td></tr>`).join("") || '<tr><td colspan="10">No hay mediciones para mostrar.</td></tr>';
}

async function load() {
    const data=await api("/api/calidad");
    measurements=data.mediciones;ranges=data.rangos;
    $("#rangeCards").innerHTML=ranges.map(item => `<article><span>${safe(item.parametro)}</span><strong>${Number(item.minimo).toFixed(2)} – ${Number(item.maximo).toFixed(2)}</strong><small>${safe(item.unidad)}</small>${canEditRanges()?`<button class="action" data-range="${item.id}">Editar rango</button>`:""}</article>`).join("");
    $("#qualityPool").innerHTML=data.piscinas.map(item => `<option value="${item.id}">${safe(item.codigo)}</option>`).join("");
    $("#qualityStaff").innerHTML=data.responsables.map(item => `<option value="${item.id}">${safe(item.codigo_empleado)} · ${safe(item.nombre)}</option>`).join("");
    render();
}

$("#qualitySearch").oninput=render;
$("#qualityState").onchange=render;
function openMeasurement(item=null){
    $("#qualityForm").reset();
    $("#qualityId").value=item?.id||"";$("#qualityDialogTitle").textContent=item?"Editar medición":"Registrar medición";
    $("#qualityDate").value=item?String(item.fecha).replace(" ","T").slice(0,16):localDateTime();
    if(item){$("#qualityPool").value=item.piscina_id;$("#qualityStaff").value=item.resp_id;$("#qualityOxygen").value=item.oxigeno;$("#qualityTemp").value=item.temp;$("#qualityPh").value=item.ph;$("#qualitySalinity").value=item.salinidad;$("#qualityNotes").value=item.notas||"";}
    $("#qualityMessage").textContent="";
    openDialog($("#qualityDialog"));
}
$("#newMeasurement").onclick=()=>openMeasurement();
document.querySelectorAll("dialog .close,dialog .cancel").forEach(button=>button.onclick=()=>closeDialog(button.closest("dialog")));
$("#qualityRows").onclick=async event=>{
    const item=measurements.find(row=>row.id==(event.target.dataset.edit||event.target.dataset.delete));
    if(event.target.dataset.edit)openMeasurement(item);
    if(event.target.dataset.delete&&confirm("¿Eliminar esta medición? Esta acción no se puede deshacer.")){try{await api(`/api/calidad/${item.id}`,{method:"DELETE"});await load();}catch(error){alert(error.message);}}
};
$("#rangeCards").onclick=event=>{
    if(!event.target.dataset.range)return;const item=ranges.find(row=>row.id==event.target.dataset.range);
    $("#rangeId").value=item.id;$("#rangeTitle").textContent=`Editar rango · ${item.parametro}`;$("#rangeMin").value=item.minimo;$("#rangeMax").value=item.maximo;$("#rangeMessage").textContent="";openDialog($("#rangeDialog"));
};
$("#qualityForm").onsubmit=async event=>{
    event.preventDefault();
    try {
        const id=$("#qualityId").value;
        await api(id?`/api/calidad/${id}`:"/api/calidad",{method:id?"PATCH":"POST",body:JSON.stringify({
            piscina_id:$("#qualityPool").value,resp_id:$("#qualityStaff").value,fecha:$("#qualityDate").value,
            oxigeno:$("#qualityOxygen").value,temp:$("#qualityTemp").value,ph:$("#qualityPh").value,
            salinidad:$("#qualitySalinity").value,notas:$("#qualityNotes").value.trim()
        })});
        closeDialog($("#qualityDialog"));
        await load();
    } catch(error) { showMessage($("#qualityMessage"),error.message); }
};
$("#rangeForm").onsubmit=async event=>{event.preventDefault();try{await api(`/api/rangos-calidad/${$("#rangeId").value}`,{method:"PATCH",body:JSON.stringify({minimo:$("#rangeMin").value,maximo:$("#rangeMax").value})});closeDialog($("#rangeDialog"));await load();}catch(error){showMessage($("#rangeMessage"),error.message);}};

(async()=>{
    currentUser=await initSession();
    $("#newMeasurement").hidden=!canRegister();
    await load();
})().catch(error=>alert(error.message));
