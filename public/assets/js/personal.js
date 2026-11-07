let staff = [];
let tasks = [];
let pools = [];
let currentUser = null;

const staffDialog = $("#staffDialog");
const taskDialog = $("#taskDialog");

function can(permission) {
    return currentUser?.permisos.includes(permission);
}

function formatDate(value) {
    if (!value) return "—";
    const [year, month, day] = String(value).slice(0, 10).split("-");
    return `${day}/${month}/${year}`;
}

function formatDateTime(value) {
    if (!value) return "—";
    return new Date(String(value).replace(" ", "T")).toLocaleString("es-GT");
}

function formatSchedule(item) {
    if (!item.fecha_inicio) return formatDateTime(item.fecha_fin || item.fecha_limite);
    const start = new Date(String(item.fecha_inicio).replace(" ", "T"));
    const end = new Date(String(item.fecha_fin).replace(" ", "T"));
    const date = start.toLocaleDateString("es-GT");
    const startTime = start.toLocaleTimeString("es-GT", {hour: "2-digit", minute: "2-digit"});
    const endTime = end.toLocaleTimeString("es-GT", {hour: "2-digit", minute: "2-digit"});
    return date + " · " + startTime + " a " + endTime;
}

async function load() {
    const optionsPromise = can("personal.asignar")
        ? api("/api/personal-opciones").then(data => data.piscinas)
        : Promise.resolve([]);
    [staff, tasks, pools] = await Promise.all([
        api("/api/colaboradores").then(data => data.colaboradores),
        api("/api/actividades").then(data => data.actividades),
        optionsPromise
    ]);

    $("#taskStaff").innerHTML = staff
        .filter(item => {
            const position = String(item.puesto || "").trim().toUpperCase();
            return item.estado && (
                position.startsWith("AUXILIAR") ||
                position.startsWith("SUPERVISOR")
            );
        })
        .map(item => `<option value="${item.id}">${safe(item.codigo_empleado)} · ${safe(item.nombre)}</option>`)
        .join("");

    const poolOption = item =>
        `<option value="${item.id}">${safe(item.codigo)} — ${safe(item.estado_ciclo || "Sin ciclo")}</option>`;
    const seededPools = pools.filter(item => item.estado_ciclo === "Sembrado");
    const availablePools = pools.filter(item => item.estado_ciclo !== "Sembrado");
    const seededGroup = seededPools.length
        ? `<optgroup label="Piscinas sembradas">${seededPools.map(poolOption).join("")}</optgroup>`
        : "";
    const availableGroup = availablePools.length
        ? `<optgroup label="Piscinas disponibles">${availablePools.map(poolOption).join("")}</optgroup>`
        : "";
    $("#taskPool").innerHTML =
        '<option value="">Trabajos varios (sin piscina)</option>' + seededGroup + availableGroup;

    renderStaff();
    renderTasks();
}

function renderStaff() {
    const query = $("#staffSearch").value.trim().toLowerCase();
    const filtered = staff.filter(item =>
        [item.codigo_empleado, item.nombre, item.puesto]
            .some(value => String(value || "").toLowerCase().includes(query))
    );

    $("#staffRows").innerHTML = filtered.map(item => {
        const editButton = can("personal.editar")
            ? `<button class="action" data-edit="${item.id}">Editar</button>`
            : "";
        const toggleButton = can("personal.cambiar_estado")
            ? `<button class="action" data-toggle="${item.id}">${item.estado ? "Desactivar" : "Activar"}</button>`
            : "";
        const deleteButton = can("personal.editar")
            ? `<button class="action danger-text" data-delete="${item.id}">Eliminar</button>`
            : "";

        return `<tr>
            <td>${safe(item.codigo_empleado)}</td>
            <td><b>${safe(item.nombre)}</b></td>
            <td>${safe(item.puesto)}</td>
            <td>${formatDate(item.fecha_ingreso)}</td>
            <td>${safe(item.celular || "—")}</td>
            <td><span class="badge ${item.estado ? "" : "off"}">${item.estado ? "Activo" : "Inactivo"}</span></td>
            <td>${editButton}${toggleButton}${deleteButton || (!editButton && !toggleButton ? "—" : "")}</td>
        </tr>`;
    }).join("") || '<tr><td colspan="7">No se encontraron colaboradores.</td></tr>';
}

function renderTasks() {
    const query = $("#taskSearch").value.trim().toLowerCase();
    const filtered = tasks.filter(item =>
        [item.descripcion, item.colaborador, item.piscina, item.estado]
            .some(value => String(value || "").toLowerCase().includes(query))
    );

    $("#taskRows").innerHTML = filtered.map(item => {
        const confirmAction = item.estado !== "Realizada" && can("personal.confirmar")
            ? `<button class="action" data-done="${item.id}">Confirmar</button>`
            : "";
        const deleteAction = can("personal.asignar")
            ? `<button class="action danger-text" data-delete="${item.id}">Eliminar</button>`
            : "";
        const action = confirmAction + deleteAction || "—";

        return `<tr>
            <td>${safe(item.descripcion)}</td>
            <td>${safe(item.colaborador)}</td>
            <td><b>${safe(item.piscina || "Trabajos varios")}</b></td>
            <td>${formatSchedule(item)}</td>
            <td><span class="badge ${item.estado === "Vencida" ? "off" : item.estado === "Pendiente" ? "pending" : ""}">${safe(item.estado)}</span></td>
            <td>${action}</td>
        </tr>`;
    }).join("") || '<tr><td colspan="6">No hay actividades registradas.</td></tr>';
    $("#deleteAllTasks").hidden = !can("personal.asignar") || tasks.length === 0;
}

function openStaff(item = null) {
    $("#staffForm").reset();
    $("#staffMessage").textContent = "";
    $("#staffId").value = item?.id || "";
    $("#staffTitle").textContent = item ? "Editar colaborador" : "Nuevo colaborador";
    $("#staffCode").disabled = Boolean(item);

    if (item) {
        $("#staffCode").value = item.codigo_empleado;
        $("#staffName").value = item.nombre;
        $("#staffPosition").value = item.puesto;
        $("#staffStartDate").value = String(item.fecha_ingreso || "").slice(0, 10);
        $("#staffPhone").value = item.celular || "";
    }

    openDialog(staffDialog);
}

document.querySelectorAll(".tab").forEach(button => {
    button.onclick = () => {
        document.querySelectorAll(".tab").forEach(item => item.classList.remove("active"));
        document.querySelectorAll(".tab-panel").forEach(item => item.classList.add("hidden"));
        button.classList.add("active");
        $("#" + button.dataset.tab).classList.remove("hidden");
    };
});

document.querySelectorAll(".close,.cancel").forEach(button => {
    button.onclick = () => closeDialog(button.closest("dialog"));
});

$("#staffSearch").oninput = renderStaff;
$("#taskSearch").oninput = renderTasks;
$("#newStaff").onclick = () => openStaff();
$("#newTask").onclick = () => {
    $("#taskForm").reset();
    $("#taskMessage").textContent = "";
    const start = new Date();
    start.setMinutes(Math.ceil(start.getMinutes() / 30) * 30, 0, 0);
    const end = new Date(start.getTime() + 60 * 60 * 1000);
    const localValue = date => {
        const offset = date.getTimezoneOffset() * 60000;
        return new Date(date.getTime() - offset).toISOString().slice(0, 16);
    };
    $("#taskStart").value = localValue(start);
    $("#taskEnd").value = localValue(end);
    openDialog(taskDialog);
};

$("#staffRows").onclick = async event => {
    const item = staff.find(row =>
        row.id == event.target.dataset.edit || row.id == event.target.dataset.toggle || row.id == event.target.dataset.delete
    );

    if (event.target.dataset.edit) openStaff(item);

    if (event.target.dataset.toggle && confirm("¿Cambiar el estado del colaborador?")) {
        await api(`/api/colaboradores/${item.id}`, {
            method: "PATCH",
            body: JSON.stringify({estado: item.estado ? 0 : 1})
        });
        await load();
    }
    if (event.target.dataset.delete && confirm(`¿Eliminar permanentemente a ${item.nombre}?`)) {
        try { await api(`/api/colaboradores/${item.id}`, {method: "DELETE"}); await load(); }
        catch (error) { alert(error.message); }
    }
};

$("#taskRows").onclick = async event => {
    if (event.target.dataset.done && confirm("¿Confirmar la actividad como realizada?")) {
        await api(`/api/actividades/${event.target.dataset.done}`, {
            method: "PATCH",
            body: JSON.stringify({estado: "Realizada"})
        });
        await load();
    }
    if (event.target.dataset.delete) {
        const item = tasks.find(row => row.id == event.target.dataset.delete);
        if (!confirm(`¿Eliminar permanentemente la actividad "${item.descripcion}"?`)) return;
        await api(`/api/actividades/${item.id}`, {method: "DELETE"});
        await load();
    }
};

$("#deleteAllTasks").onclick = async () => {
    if (!confirm(`¿Eliminar permanentemente las ${tasks.length} actividades registradas?`)) return;
    if (!confirm("Esta acción no se puede deshacer. ¿Deseas continuar?")) return;
    try {
        const result = await api("/api/actividades", {method: "DELETE"});
        alert(`Se eliminaron ${result.eliminadas} actividades.`);
        await load();
    } catch (error) {
        alert(error.message);
    }
};

$("#staffForm").onsubmit = async event => {
    event.preventDefault();
    const id = $("#staffId").value;
    const payload = {
        codigo_empleado: $("#staffCode").value.trim(),
        nombre: $("#staffName").value.trim(),
        puesto: $("#staffPosition").value.trim(),
        fecha_ingreso: $("#staffStartDate").value,
        celular: $("#staffPhone").value.trim()
    };

    try {
        await api(id ? `/api/colaboradores/${id}` : "/api/colaboradores", {
            method: id ? "PATCH" : "POST",
            body: JSON.stringify(payload)
        });
        closeDialog(staffDialog);
        await load();
    } catch (error) {
        showMessage($("#staffMessage"), error.message);
    }
};

$("#taskForm").onsubmit = async event => {
    event.preventDefault();

    try {
        await api("/api/actividades", {
            method: "POST",
            body: JSON.stringify({
                colaborador_id: $("#taskStaff").value,
                piscina_id: $("#taskPool").value || null,
                descripcion: $("#taskDescription").value.trim(),
                fecha_inicio: $("#taskStart").value,
                fecha_fin: $("#taskEnd").value
            })
        });
        closeDialog(taskDialog);
        await load();
    } catch (error) {
        showMessage($("#taskMessage"), error.message);
    }
};

(async () => {
    currentUser = await initSession();
    $("#newStaff").hidden = !can("personal.crear");
    $("#newTask").hidden = !can("personal.asignar");
    await load();
})().catch(error => alert(error.message));
