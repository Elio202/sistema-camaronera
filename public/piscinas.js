let items = [], modules = [], user;
const dialog = $("#dialog"), historyDialog = $("#historyDialog"), form = $("#form");
const can = permission => user?.permisos?.includes(permission);

function cycleOptions(item) {
    const next = item.estado_ciclo === "Cancelado"
        ? Number(item.numero_ciclo)
        : Number(item.numero_ciclo || 0) + 1;
    const limit = Math.max(30, next);
    return Array.from({length: limit}, (_, index) => index + 1).map(number =>
        `<option value="${number}" ${number === next ? "selected" : ""}>${number}</option>`).join("");
}

async function load() {
    const [poolData, moduleData] = await Promise.all([api("/api/piscinas"), api("/api/modulos")]);
    items = poolData.piscinas;
    modules = moduleData.modulos;
    $("#modulo").innerHTML = modules.map(item => `<option value="${item.id}">${safe(item.finca)} · ${safe(item.codigo)}</option>`).join("");
    render();
}

function render() {
    const matches = (item, query) => `${item.codigo_productivo} ${item.finca} ${item.modulo} ${item.tipo}`.toLowerCase().includes(query.toLowerCase());
    const editable = can("piscinas.editar");
    $("#total").textContent = items.length;
    $("#active").textContent = items.filter(item => item.estado).length;
    $("#production").textContent = items.filter(item => item.estado_ciclo === "Sembrado").length;
    $("#newItem").hidden = !can("piscinas.crear");
    const selectedState = $("#cycleStateFilter").value;
    const cycleItems = items.filter(item =>
        matches(item, $("#cycleSearch").value) &&
        (!selectedState || item.estado_ciclo === selectedState)
    );
    $("#cycleRows").innerHTML = cycleItems.map(item => {
        const open = ["Sembrado", "Planificado"].includes(item.estado_ciclo);
        const actions = open
            ? `<button class="action" data-harvest="${item.id}" ${editable ? "" : "disabled"}>Cosechar</button><button class="action danger-text" data-cancel-cycle="${item.id}" ${editable ? "" : "disabled"}>Cancelar ciclo</button>`
            : `<button class="action" data-start="${item.id}" ${editable && item.estado ? "" : "disabled"}>Iniciar ciclo</button>`;
        const deleteCycle = editable && item.ciclo_id ? `<button class="action danger-text" data-delete-cycle="${item.ciclo_id}" data-pool="${item.id}">Eliminar ciclo</button>` : "";
        return `<tr><td><b>${safe(item.codigo_productivo)}</b><small class="cell-note">Piscina: ${safe(item.codigo)}</small></td><td>${safe(item.finca)}<small class="cell-note">${safe(item.modulo)}</small></td><td><span class="badge ${open ? "pending" : ""}">${safe(item.estado_ciclo || "Sin ciclo")}</span></td><td><select class="cycle-select" data-cycle-for="${item.id}" ${open || !editable ? "disabled" : ""}>${cycleOptions(item)}</select></td><td>${actions}<button class="action" data-history="${item.id}">Historial</button>${deleteCycle}</td></tr>`;
    }).join("");
    $("#rows").innerHTML = items.filter(item => matches(item, $("#search").value)).map(item =>
        `<tr><td><b>${safe(item.codigo)}</b></td><td>${safe(item.finca)}</td><td>${safe(item.modulo)}</td><td>${safe(item.tipo)}</td><td>${Math.round(Number(item.area_m2))} m²</td><td><span class="badge ${item.estado ? "" : "off"}">${item.estado ? "Activa" : "Inactiva"}</span></td><td><button class="action" data-edit="${item.id}" ${editable ? "" : "disabled"}>Editar</button><button class="action" data-toggle="${item.id}" ${can("piscinas.cambiar_estado") ? "" : "disabled"}>${item.estado ? "Desactivar" : "Activar"}</button>${editable ? `<button class="action danger-text" data-delete-pool="${item.id}">Eliminar</button>` : ""}</td></tr>`).join("");
}

function edit(item = null) {
    form.reset(); $("#formMessage").textContent = ""; $("#itemId").value = item?.id || "";
    $("#dialogTitle").textContent = item ? "Editar piscina" : "Nueva piscina"; $("#codigo").disabled = Boolean(item);
    if (item) {
        $("#codigo").value = item.codigo;
        const selected = modules.find(module => module.codigo === item.modulo && module.finca === item.finca);
        $("#modulo").value = selected?.id || ""; $("#tipo").value = item.tipo; $("#area").value = item.area_m2;
    }
    openDialog(dialog);
}

async function showHistory(item) {
    const data = await api(`/api/ciclos?piscina_id=${item.id}`);
    $("#historyTitle").textContent = `Historial · ${item.codigo}`;
    $("#historyRows").innerHTML = data.ciclos.length ? data.ciclos.map(cycle => `<tr><td><b>${safe(cycle.codigo_productivo)}</b></td><td>${safe(cycle.estado)}</td><td>${safe(cycle.fecha_siembra || "—")}</td><td>${safe(cycle.fecha_cosecha || "—")}</td></tr>`).join("") : `<tr><td colspan="4">Esta piscina todavía no tiene ciclos.</td></tr>`;
    openDialog(historyDialog);
}

document.querySelectorAll(".tab").forEach(tab => tab.onclick = () => {
    document.querySelectorAll(".tab").forEach(item => item.classList.toggle("active", item === tab));
    $("#cyclesView").classList.toggle("hidden", tab.dataset.view !== "cycles");
    $("#catalogView").classList.toggle("hidden", tab.dataset.view !== "catalog");
});
$("#newItem").onclick = () => edit(); $("#search").oninput = render; $("#cycleSearch").oninput = render;
$("#cycleStateFilter").onchange = render;
document.querySelectorAll("#dialog .close,#dialog .cancel").forEach(button => button.onclick = () => closeDialog(dialog));

$("#cycleRows").onclick = async event => {
    const id = event.target.dataset.start || event.target.dataset.harvest || event.target.dataset.cancelCycle || event.target.dataset.history || event.target.dataset.pool;
    const item = items.find(pool => pool.id == id); if (!item) return;
    try {
        if (event.target.dataset.history) return await showHistory(item);
        if (event.target.dataset.deleteCycle) {
            if (!confirm(`¿Eliminar permanentemente el ciclo ${item.codigo_productivo}?`)) return;
            await api(`/api/ciclos/${event.target.dataset.deleteCycle}`, {method: "DELETE"});
            return await load();
        }
        if (event.target.dataset.start) {
            const number = Number(document.querySelector(`[data-cycle-for="${item.id}"]`).value);
            if (!confirm(`¿Iniciar ${item.codigo}-${number} como ciclo sembrado?`)) return;
            await api("/api/ciclos", {method: "POST", body: JSON.stringify({piscina_id: item.id, numero_ciclo: number})});
        } else if (event.target.dataset.harvest) {
            if (!confirm(`¿Registrar como cosechado el ciclo ${item.codigo_productivo}?`)) return;
            await api(`/api/ciclos/${item.ciclo_id}`, {method: "PATCH", body: JSON.stringify({estado: "Cosechado"})});
        } else if (event.target.dataset.cancelCycle) {
            if (!confirm(`¿Cancelar el ciclo ${item.codigo_productivo}?`)) return;
            await api(`/api/ciclos/${item.ciclo_id}`, {method: "PATCH", body: JSON.stringify({estado: "Cancelado"})});
        }
        await load();
    } catch (error) { alert(error.message); }
};

$("#rows").onclick = async event => {
    const item = items.find(pool => pool.id == (event.target.dataset.edit || event.target.dataset.toggle || event.target.dataset.deletePool));
    if (event.target.dataset.edit) edit(item);
    if (event.target.dataset.toggle && confirm("¿Cambiar el estado de esta piscina?")) {
        await api(`/api/piscinas/${item.id}`, {method: "PATCH", body: JSON.stringify({estado: item.estado ? 0 : 1})}); await load();
    }
    if (event.target.dataset.deletePool && confirm(`¿Eliminar permanentemente la piscina ${item.codigo}?`)) {
        try { await api(`/api/piscinas/${item.id}`, {method: "DELETE"}); await load(); }
        catch (error) { alert(error.message); }
    }
};

form.onsubmit = async event => {
    event.preventDefault(); const id = $("#itemId").value;
    const payload = {codigo: $("#codigo").value, modulo_id: Number($("#modulo").value), tipo: $("#tipo").value, area_m2: Number($("#area").value)};
    try { await api(id ? `/api/piscinas/${id}` : "/api/piscinas", {method: id ? "PATCH" : "POST", body: JSON.stringify(payload)}); closeDialog(dialog); await load(); }
    catch (error) { showMessage($("#formMessage"), error.message); }
};

(async () => { user = await initSession(); await load(); })().catch(error => alert(error.message));
