let aerators=[],events=[],currentUser=null;
const canOperate=()=>currentUser?.permisos.includes("aireacion.operar");
const dateTime=value=>value?new Date(String(value).replace(" ","T")).toLocaleString("es-GT"):"—";

function renderAerators(){
    $("#aeratorCards").innerHTML=aerators.map(item=>`<article class="aerator-card ${item.condicion==='Oxígeno bajo'?'aerator-alert':''} ${item.activo?'':'aerator-inactive'}">
        <div class="sensor-head"><div><span class="eyebrow">${safe(item.piscina)}</span><h2>${safe(item.codigo)}</h2></div><span class="sensor-status ${item.activo&&item.encendido?'online':'offline'}">${item.activo?(item.encendido?'Encendido':'Apagado'):'Inactivo'}</span></div>
        <div class="aerator-reading"><span>Oxígeno actual</span><strong>${item.oxigeno===null?'—':Number(item.oxigeno).toFixed(2)}</strong><small>mg/L</small></div>
        <p class="aerator-condition">${safe(item.condicion)} · Encender &lt; ${Number(item.umbral_enc).toFixed(2)} · Apagar ≥ ${Number(item.umbral_apa).toFixed(2)}</p>
        <div class="aerator-actions"><button class="secondary compact" data-reading="${item.id}" ${item.activo?'':'disabled'}>Registrar lectura</button><button class="secondary compact" data-mode="${item.id}" ${item.activo?'':'disabled'}>${item.modo}</button><button class="primary compact" data-operate="${item.id}" ${item.modo!=='Manual'||!item.activo?'disabled':''}>${item.encendido?'Apagar':'Encender'}</button><button class="action" data-edit="${item.id}">Editar</button><button class="action" data-toggle="${item.id}">${item.activo?'Desactivar':'Activar'}</button><button class="action danger-text" data-delete="${item.id}">Eliminar</button></div>
    </article>`).join("")||'<p class="empty-state">No hay aireadores registrados.</p>';
    if(!canOperate()) $("#aeratorCards").querySelectorAll("button").forEach(button=>button.hidden=true);
}

function renderEvents(){
    $("#aeratorEvents").innerHTML=events.map(item=>`<tr><td>${dateTime(item.creado)}</td><td><b>${safe(item.aireador)}</b></td><td>${safe(item.piscina)}</td><td>${safe(item.accion)}</td><td>${safe(item.origen)}</td><td>${item.oxigeno===null?'—':Number(item.oxigeno).toFixed(2)+' mg/L'}</td><td>${safe(item.usuario)}</td><td>${safe(item.detalle||'—')}</td></tr>`).join("")||'<tr><td colspan="8">Todavía no hay operaciones registradas.</td></tr>';
}

async function load(){
    const data=await api("/api/aireacion");aerators=data.aireadores;events=data.eventos;
    $("#aeratorPool").innerHTML=data.piscinas.map(item=>`<option value="${item.id}">${safe(item.codigo)}</option>`).join("");
    renderAerators();renderEvents();
}

function openAerator(item=null){$("#aeratorForm").reset();$("#aeratorId").value=item?.id||"";$("#aeratorDialogTitle").textContent=item?"Editar aireador":"Nuevo aireador";$("#thresholdOn").value=item?.umbral_enc??"4.00";$("#thresholdOff").value=item?.umbral_apa??"5.50";if(item){$("#aeratorPool").value=item.piscina_id;$("#aeratorCode").value=item.codigo;}$("#aeratorMessage").textContent="";openDialog($("#aeratorDialog"));}
$("#newAerator").onclick=()=>openAerator();
document.querySelectorAll("dialog .close,dialog .cancel").forEach(button=>button.onclick=()=>closeDialog(button.closest("dialog")));
$("#aeratorForm").onsubmit=async event=>{event.preventDefault();try{const id=$("#aeratorId").value;await api(id?`/api/aireacion/${id}`:"/api/aireacion",{method:id?"PATCH":"POST",body:JSON.stringify({piscina_id:$("#aeratorPool").value,codigo:$("#aeratorCode").value.trim(),umbral_enc:$("#thresholdOn").value,umbral_apa:$("#thresholdOff").value})});closeDialog($("#aeratorDialog"));await load();}catch(error){showMessage($("#aeratorMessage"),error.message);}};
$("#aeratorCards").onclick=async event=>{
    const id=event.target.dataset.reading||event.target.dataset.mode||event.target.dataset.operate||event.target.dataset.edit||event.target.dataset.toggle||event.target.dataset.delete;if(!id)return;
    const item=aerators.find(row=>row.id==id);
    if(event.target.dataset.edit){openAerator(item);return;}
    if(event.target.dataset.toggle){if(!confirm(`¿${item.activo?'Desactivar':'Activar'} ${item.codigo}?`))return;await api(`/api/aireacion/${id}`,{method:"PATCH",body:JSON.stringify({activo:!item.activo})});await load();return;}
    if(event.target.dataset.delete){if(!confirm(`¿Eliminar permanentemente ${item.codigo}?`))return;try{await api(`/api/aireacion/${id}`,{method:"DELETE"});await load();}catch(error){alert(error.message);}return;}
    if(event.target.dataset.reading){$("#oxygenAerator").value=id;$("#oxygenValue").value=item.oxigeno??"";$("#oxygenMessage").textContent="";openDialog($("#oxygenDialog"));return;}
    if(event.target.dataset.mode){const mode=item.modo==="Manual"?"Automático":"Manual";if(!confirm(`¿Cambiar ${item.codigo} a modo ${mode}?`))return;await api("/api/aireacion/modo",{method:"POST",body:JSON.stringify({aireador_id:id,modo:mode})});await load();return;}
    if(event.target.dataset.operate&&confirm(`¿${item.encendido?'Apagar':'Encender'} ${item.codigo}?`)){await api("/api/aireacion/operar",{method:"POST",body:JSON.stringify({aireador_id:id})});await load();}
};
$("#oxygenForm").onsubmit=async event=>{event.preventDefault();try{await api("/api/aireacion/lectura",{method:"POST",body:JSON.stringify({aireador_id:$("#oxygenAerator").value,oxigeno:$("#oxygenValue").value})});closeDialog($("#oxygenDialog"));await load();}catch(error){showMessage($("#oxygenMessage"),error.message);}};

(async()=>{currentUser=await initSession();$("#newAerator").hidden=!canOperate();await load();})().catch(error=>alert(error.message));
