let currentUser=null,currentReport=null;
let dashboardData=null;

function displayValue(value) {
    if (value===null || value===undefined || value==="") return "—";
    return String(value);
}

function renderReport(report) {
    currentReport=report;
    $("#reportTitle").textContent=report.titulo;
    $("#resultCount").textContent=`${report.filas.length} ${report.filas.length===1?'registro':'registros'}`;
    $("#periodText").textContent=report.desde || report.hasta
        ? `Período: ${report.desde || 'inicio'} al ${report.hasta || 'hoy'}` : "Todos los registros";
    $("#reportHead").innerHTML=`<tr>${report.columnas.map(column => `<th>${safe(column.titulo)}</th>`).join("")}</tr>`;
    $("#reportRows").innerHTML=report.filas.map(row => `<tr>${report.columnas.map(column => `<td>${safe(displayValue(row[column.campo]))}</td>`).join("")}</tr>`).join("")
        || `<tr><td colspan="${report.columnas.length}" class="empty-state">No existen registros para los filtros seleccionados.</td></tr>`;
}

async function loadReport() {
    const type=$("#reportType").value;
    const from=$("#dateFrom").value;
    const to=$("#dateTo").value;
    if (from && to && from>to) throw new Error("La fecha inicial no puede ser posterior a la fecha final.");
    const params=new URLSearchParams({tipo:type});
    if (from) params.set("desde",from);
    if (to) params.set("hasta",to);
    const data=await api(`/api/reportes?${params}`);
    renderReport(data.reporte);
    showMessage($("#reportMessage"),"");
}

function csvCell(value) {
    return `"${displayValue(value).replaceAll('"','""')}"`;
}

function exportCsv() {
    if (!currentReport || !currentReport.filas.length) return showMessage($("#reportMessage"),"No hay registros para exportar.");
    const lines=[currentReport.columnas.map(column => csvCell(column.titulo)).join(";")];
    currentReport.filas.forEach(row => lines.push(currentReport.columnas.map(column => csvCell(row[column.campo])).join(";")));
    const blob=new Blob(["\ufeff"+lines.join("\r\n")],{type:"text/csv;charset=utf-8"});
    const link=document.createElement("a");
    link.href=URL.createObjectURL(blob);
    link.download=`${currentReport.tipo}_${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
}

function renderChart(selector,items,type="doughnut") {
    const container=$(selector);
    if (!items.length) {
        container.innerHTML='<p class="empty-state">No hay datos para el período seleccionado.</p>';
        return;
    }
    const colors=["#176ec1","#009a91","#e3a329","#cf5555","#7456b8"];
    container.innerHTML='<canvas></canvas><div class="chart-legend"></div>';
    container.querySelector(".chart-legend").innerHTML=items.map((item,index) => `<span><i style="background:${colors[index%colors.length]}"></i>${safe(item.etiqueta)} <b>${safe(displayValue(item.valor))}</b></span>`).join("");
    const canvas=container.querySelector("canvas"),context=canvas.getContext("2d");
    const width=Math.max(300,container.clientWidth),height=210,ratio=window.devicePixelRatio || 1;
    canvas.width=width*ratio;canvas.height=height*ratio;canvas.style.width=`${width}px`;canvas.style.height=`${height}px`;context.scale(ratio,ratio);
    const values=items.map(item => Number(item.valor));
    if (type==="columns") {
        const maximum=Math.max(1,...values),left=36,bottom=180,chartHeight=145,gap=24;
        const barWidth=Math.min(90,(width-left-20-gap*(items.length+1))/items.length);
        context.strokeStyle="#cbd9df";context.beginPath();context.moveTo(left,15);context.lineTo(left,bottom);context.lineTo(width-10,bottom);context.stroke();
        items.forEach((item,index) => {
            const x=left+gap+(barWidth+gap)*index,barHeight=values[index]/maximum*chartHeight,y=bottom-barHeight;
            context.fillStyle=colors[index%colors.length];context.beginPath();context.roundRect(x,y,barWidth,barHeight,[8,8,0,0]);context.fill();
            context.fillStyle="#092f3b";context.font="bold 13px Arial";context.textAlign="center";context.fillText(displayValue(item.valor),x+barWidth/2,Math.max(12,y-7));
            context.font="12px Arial";context.fillText(item.etiqueta,x+barWidth/2,bottom+20);
        });
    } else {
        const total=values.reduce((sum,value) => sum+value,0),centerX=width/2,centerY=100,radius=78,inner=47;
        let angle=-Math.PI/2;
        items.forEach((item,index) => {
            const next=angle+(values[index]/Math.max(1,total))*Math.PI*2;
            context.beginPath();context.arc(centerX,centerY,radius,angle,next);context.arc(centerX,centerY,inner,next,angle,true);context.closePath();context.fillStyle=colors[index%colors.length];context.fill();angle=next;
        });
        context.fillStyle="#092f3b";context.textAlign="center";context.font="bold 25px Arial";context.fillText(total,centerX,centerY+5);
        context.fillStyle="#687d86";context.font="12px Arial";context.fillText("Total",centerX,centerY+24);
    }
}

function fillDashboardFilters(data) {
    const farm=$("#dashFarm").value,module=$("#dashModule").value;
    $("#dashFarm").innerHTML='<option value="">Todas las fincas</option>'+data.fincas.map(item => `<option value="${item.id}">${safe(item.nombre)}</option>`).join("");
    $("#dashFarm").value=farm;
    const modules=data.modulos.filter(item => !farm || String(item.finca_id)===farm);
    $("#dashModule").innerHTML='<option value="">Todos los módulos</option>'+modules.map(item => `<option value="${item.id}">${safe(item.codigo)}</option>`).join("");
    $("#dashModule").value=modules.some(item => String(item.id)===module)?module:"";
}

function renderDashboard(data) {
    dashboardData=data; fillDashboardFilters(data);
    const metrics=data.metricas;
    $("#kpiPools").textContent=metrics.piscinas;
    $("#kpiAvailable").textContent=metrics.disponibles;
    $("#kpiSeeded").textContent=metrics.sembradas;
    $("#kpiStaff").textContent=metrics.colaboradores;
    $("#kpiStock").textContent=metrics.stock_bajo;
    $("#kpiAlerts").textContent=metrics.alertas;
    $("#kpiQuality").textContent=metrics.calidad_fuera;
    $("#kpiAerators").textContent=metrics.aireadores_enc;
    renderChart("#cycleChart",data.ciclos);
    renderChart("#activityChart",data.actividades);
    renderChart("#movementChart",data.movimientos,"columns");
    renderChart("#alertChart",data.alertas);
    renderChart("#qualityChart",data.calidad);
    renderChart("#aerationChart",data.aireacion);
}

async function loadDashboard() {
    const from=$("#dashFrom").value,to=$("#dashTo").value;
    if (from && to && from>to) throw new Error("La fecha inicial no puede ser posterior a la fecha final.");
    const params=new URLSearchParams();
    if (from) params.set("desde",from); if (to) params.set("hasta",to);
    if ($("#dashFarm").value) params.set("finca",$("#dashFarm").value);
    if ($("#dashModule").value) params.set("modulo",$("#dashModule").value);
    const data=await api(`/api/reportes-dashboard?${params}`);
    renderDashboard(data.dashboard);
    showMessage($("#dashboardMessage"),"");
}

(async () => {
    currentUser=await initSession();
    const canExport=currentUser.permisos.includes("reportes.exportar");
    $("#exportCsv").hidden=!canExport;
    $("#printReport").hidden=!canExport;
    $("#reportFilters").onsubmit=async event => {
        event.preventDefault();
        try { await loadReport(); }
        catch (error) { showMessage($("#reportMessage"),error.message); }
    };
    $("#reportType").onchange=() => {
        const catalog=$("#reportType").value==="piscinas";
        $("#dateFrom").disabled=catalog;
        $("#dateTo").disabled=catalog;
    };
    $("#exportCsv").onclick=exportCsv;
    $("#printReport").onclick=() => currentReport?.filas.length ? window.print() : showMessage($("#reportMessage"),"No hay registros para imprimir.");
    $("#reportType").onchange();
    document.querySelectorAll("[data-report-view]").forEach(button => button.onclick=() => {
        document.querySelectorAll("[data-report-view]").forEach(item => item.classList.toggle("active",item===button));
        $("#reportDashboard").classList.toggle("hidden",button.dataset.reportView!=="dashboard");
        $("#reportDetail").classList.toggle("hidden",button.dataset.reportView!=="detail");
    });
    $("#dashboardFilters").onsubmit=async event => { event.preventDefault(); try { await loadDashboard(); } catch(error) { showMessage($("#dashboardMessage"),error.message); } };
    $("#dashFarm").onchange=() => dashboardData && fillDashboardFilters(dashboardData);
    await Promise.all([loadDashboard(),loadReport()]);
})().catch(error => {
    showMessage($("#dashboardMessage"),error.message);
    showMessage($("#reportMessage"),error.message);
});
