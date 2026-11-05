let aerators=[],events=[],pools=[],currentUser=null,selectedPoolId=null;
const canOperate=()=>currentUser?.permisos.includes("aireacion.operar");
const dateTime=value=>value?new Date(String(value).replace(" ","T")).toLocaleString("es-GT"):"—";

function defaultPosition(index,total){
    const angle=(-90+(360/Math.max(total,1))*index)*Math.PI/180;
    return {x:50+30*Math.cos(angle),y:50+30*Math.sin(angle)};
}

function renderPond(){
    const pool=pools.find(item=>item.id==selectedPoolId)||pools[0];
    if(!pool){
        $("#pondDiagram").innerHTML='<p class="pond-empty">No hay piscinas disponibles.</p>';
        return;
    }
    selectedPoolId=pool.id;
    $("#pondPool").value=pool.id;
    const items=aerators.filter(item=>item.piscina_id==pool.id);
    const area=Math.round(Number(pool.area_m2||0));
    $("#pondName").textContent=pool.codigo;
    $("#pondArea").textContent=`${area.toLocaleString("es-GT")} m²`;
    $("#pondCount").textContent=`${items.length} aireador${items.length===1?"":"es"}`;
    $("#pondCenterName").textContent=pool.codigo;
    $("#pondCenterArea").textContent=`${area.toLocaleString("es-GT")} m²`;
    $("#pondHelp").textContent=canOperate()?"Arrastra cada equipo para guardar su ubicación real.":"Ubicación registrada de los equipos.";
    const center='<div class="pond-center"><strong id="pondCenterName">'+safe(pool.codigo)+'</strong><span id="pondCenterArea">'+area.toLocaleString("es-GT")+' m²</span></div>';
    const markers=items.map((item,index)=>{
        const fallback=defaultPosition(index,items.length);
        const x=item.pos_x===null?fallback.x:Number(item.pos_x),y=item.pos_y===null?fallback.y:Number(item.pos_y);
        const state=!item.activo?"inactive":item.condicion==="Oxígeno bajo"?"low":item.encendido?"on":"off";
        const oxygen=item.oxigeno===null?"Sin lectura":`${Number(item.oxigeno).toFixed(2)} mg/L`;
        return `<button type="button" class="pond-aerator ${state}" data-pond-aerator="${item.id}" style="left:${x}%;top:${y}%"><span class="pond-aerator-icon">✣</span><b>${safe(item.codigo)}</b><small>${safe(oxygen)}</small></button>`;
    }).join("");
    $("#pondDiagram").innerHTML=center+(markers||'<p class="pond-empty">Esta piscina no tiene aireadores registrados.</p>');
}

function pointInsidePond(event){
    const rect=$("#pondDiagram").getBoundingClientRect();
    let x=(event.clientX-rect.left)*100/rect.width,y=(event.clientY-rect.top)*100/rect.height;
    const dx=x-50,dy=y-50,distance=Math.hypot(dx,dy);
    if(distance>44){x=50+dx*44/distance;y=50+dy*44/distance;}
    return {x:Number(x.toFixed(2)),y:Number(y.toFixed(2))};
}

function renderAerators(){
    $("#aeratorCards").innerHTML=aerators.map(item=>`<article class="aerator-card ${item.condicion==='Oxígeno bajo'?'aerator-alert':''} ${item.activo?'':'aerator-inactive'}">
        <div class="sensor-head"><div><span class="eyebrow">${safe(item.piscina)}</span><h2>${safe(item.codigo)}</h2></div><span class="sensor-status ${item.activo&&item.encendido?'online':'offline'}">${item.activo?(item.encendido?'Encendido':'Apagado'):'Inactivo'}</span></div>
        <div class="aerator-reading"><span>Oxígeno actual</span><strong>${item.oxigeno===null?'—':Number(item.oxigeno).toFixed(2)}</strong><small>mg/L</small></div>
        <p class="aerator-condition">${safe(item.condicion)} · Encender &lt; ${Number(item.umbral_enc).toFixed(2)} · Apagar ≥ ${Number(item.umbral_apa).toFixed(2)}</p>
        <p class="aerator-mode-note">${item.modo==='Automático'?'El sistema enciende o apaga este equipo según la lectura de oxígeno.':'El equipo puede operarse directamente con los botones.'}</p>
        <div class="aerator-actions"><button class="secondary compact" data-reading="${item.id}" ${item.activo?'':'disabled'}>Registrar lectura</button><button class="secondary compact" data-mode="${item.id}" ${item.activo?'':'disabled'}>Cambiar a ${item.modo==='Manual'?'Automático':'Manual'}</button><button class="primary compact" data-operate="${item.id}" ${item.modo!=='Manual'||!item.activo?'disabled':''}>${item.encendido?'Apagar':'Encender'}</button><button class="action" data-edit="${item.id}">Editar</button><button class="action" data-toggle="${item.id}">${item.activo?'Desactivar':'Activar'}</button><button class="action danger-text" data-delete="${item.id}">Eliminar</button></div>
    </article>`).join("")||'<p class="empty-state">No hay aireadores registrados.</p>';
    if(!canOperate()) $("#aeratorCards").querySelectorAll("button").forEach(button=>button.hidden=true);
}

function renderEvents(){
    $("#aeratorEvents").innerHTML=events.map(item=>`<tr><td>${dateTime(item.creado)}</td><td><b>${safe(item.aireador)}</b></td><td>${safe(item.piscina)}</td><td>${safe(item.accion)}</td><td>${safe(item.origen)}</td><td>${item.oxigeno===null?'—':Number(item.oxigeno).toFixed(2)+' mg/L'}</td><td>${safe(item.usuario)}</td><td>${safe(item.detalle||'—')}</td></tr>`).join("")||'<tr><td colspan="8">Todavía no hay operaciones registradas.</td></tr>';
}

async function load(){
    const data=await api("/api/aireacion");aerators=data.aireadores;events=data.eventos;pools=data.piscinas;
    $("#aeratorPool").innerHTML=data.piscinas.map(item=>`<option value="${item.id}">${safe(item.codigo)}</option>`).join("");
    const occupiedPools=data.piscinas.filter(pool=>aerators.some(item=>item.piscina_id==pool.id));
    $("#pondPool").innerHTML=occupiedPools.map(item=>`<option value="${item.id}">${safe(item.codigo)} · ${aerators.filter(aerator=>aerator.piscina_id==item.id).length} aireador(es)</option>`).join("");
    if(!selectedPoolId||!occupiedPools.some(item=>item.id==selectedPoolId))selectedPoolId=occupiedPools[0]?.id||null;
    renderPond();renderAerators();renderEvents();
}

function openAerator(item=null){$("#aeratorForm").reset();$("#aeratorId").value=item?.id||"";$("#aeratorDialogTitle").textContent=item?"Editar aireador":"Nuevo aireador";$("#thresholdOn").value=item?.umbral_enc??"4.00";$("#thresholdOff").value=item?.umbral_apa??"5.50";if(item){$("#aeratorPool").value=item.piscina_id;$("#aeratorCode").value=item.codigo;}$("#aeratorMessage").textContent="";openDialog($("#aeratorDialog"));}
$("#newAerator").onclick=()=>openAerator();
$("#pondPool").onchange=event=>{selectedPoolId=Number(event.target.value);renderPond();};
$("#pondDiagram").onpointerdown=event=>{
    const marker=event.target.closest("[data-pond-aerator]");
    if(!marker||!canOperate())return;
    event.preventDefault();
    marker.setPointerCapture(event.pointerId);
    marker.classList.add("dragging");
    const move=moveEvent=>{const point=pointInsidePond(moveEvent);marker.style.left=point.x+"%";marker.style.top=point.y+"%";};
    marker.onpointermove=move;
    marker.onpointerup=async upEvent=>{
        marker.onpointermove=null;marker.onpointerup=null;marker.classList.remove("dragging");
        const point=pointInsidePond(upEvent),item=aerators.find(row=>row.id==marker.dataset.pondAerator);
        try{await api(`/api/aireacion/${item.id}`,{method:"PATCH",body:JSON.stringify({pos_x:point.x,pos_y:point.y})});item.pos_x=point.x;item.pos_y=point.y;}
        catch(error){alert(error.message);renderPond();}
    };
};
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
