let aerators=[],events=[],currentUser=null;
const canOperate=()=>currentUser?.permisos.includes("aireacion.operar");
const dateTime=value=>value?new Date(String(value).replace(" ","T")).toLocaleString("es-GT"):"—";

function renderAerators(){
    $("#aeratorCards").innerHTML=aerators.map(item=>`<article class="aerator-card ${item.condicion==='Oxígeno bajo'?'aerator-alert':''}">
        <div class="sensor-head"><div><span class="eyebrow">${safe(item.piscina)}</span><h2>${safe(item.codigo)}</h2></div><span class="sensor-status ${item.encendido?'online':'offline'}">${item.encendido?'Encendido':'Apagado'}</span></div>
        <div class="aerator-reading"><span>Oxígeno actual</span><strong>${item.oxigeno===null?'—':Number(item.oxigeno).toFixed(2)}</strong><small>mg/L</small></div>
        <p class="aerator-condition">${safe(item.condicion)} · Encender &lt; ${Number(item.umbral_enc).toFixed(2)} · Apagar ≥ ${Number(item.umbral_apa).toFixed(2)}</p>
        <div class="aerator-actions"><button class="secondary compact" data-reading="${item.id}">Registrar lectura</button><button class="secondary compact" data-mode="${item.id}">${item.modo}</button><button class="primary compact" data-operate="${item.id}" ${item.modo!=='Manual'?'disabled':''}>${item.encendido?'Apagar':'Encender'}</button></div>
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

$("#newAerator").onclick=()=>{$("#aeratorForm").reset();$("#thresholdOn").value="4.00";$("#thresholdOff").value="5.50";$("#aeratorMessage").textContent="";openDialog($("#aeratorDialog"));};
document.querySelectorAll("dialog .close,dialog .cancel").forEach(button=>button.onclick=()=>closeDialog(button.closest("dialog")));
$("#aeratorForm").onsubmit=async event=>{event.preventDefault();try{await api("/api/aireacion",{method:"POST",body:JSON.stringify({piscina_id:$("#aeratorPool").value,codigo:$("#aeratorCode").value.trim(),umbral_enc:$("#thresholdOn").value,umbral_apa:$("#thresholdOff").value})});closeDialog($("#aeratorDialog"));await load();}catch(error){showMessage($("#aeratorMessage"),error.message);}};
$("#aeratorCards").onclick=async event=>{
    const id=event.target.dataset.reading||event.target.dataset.mode||event.target.dataset.operate;if(!id)return;
    const item=aerators.find(row=>row.id==id);
    if(event.target.dataset.reading){$("#oxygenAerator").value=id;$("#oxygenValue").value=item.oxigeno??"";$("#oxygenMessage").textContent="";openDialog($("#oxygenDialog"));return;}
    if(event.target.dataset.mode){const mode=item.modo==="Manual"?"Automático":"Manual";if(!confirm(`¿Cambiar ${item.codigo} a modo ${mode}?`))return;await api("/api/aireacion/modo",{method:"POST",body:JSON.stringify({aireador_id:id,modo:mode})});await load();return;}
    if(event.target.dataset.operate&&confirm(`¿${item.encendido?'Apagar':'Encender'} ${item.codigo}?`)){await api("/api/aireacion/operar",{method:"POST",body:JSON.stringify({aireador_id:id})});await load();}
};
$("#oxygenForm").onsubmit=async event=>{event.preventDefault();try{await api("/api/aireacion/lectura",{method:"POST",body:JSON.stringify({aireador_id:$("#oxygenAerator").value,oxigeno:$("#oxygenValue").value})});closeDialog($("#oxygenDialog"));await load();}catch(error){showMessage($("#oxygenMessage"),error.message);}};

(async()=>{currentUser=await initSession();$("#newAerator").hidden=!canOperate();await load();})().catch(error=>alert(error.message));
