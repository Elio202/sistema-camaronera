let roles = [], permissions = [], selectedRole = null, user;
const deleteRoleButton = document.createElement("button");
deleteRoleButton.type = "button";
deleteRoleButton.className = "secondary danger-button";
deleteRoleButton.textContent = "Eliminar rol";
document.querySelector(".permission-editor .dialog-actions").prepend(deleteRoleButton);
const labels = {
    usuarios: "Usuarios", roles: "Roles y permisos", piscinas: "Piscinas y ciclos",
    personal: "Personal y actividades", inventario: "Inventario", aireacion: "Aireación",
    calidad_agua: "Calidad del agua", reportes: "Reportes",
    ver: "Ver", crear: "Crear", editar: "Editar", cambiar_estado: "Activar o desactivar",
    registrar: "Registrar", asignar: "Asignar", confirmar: "Confirmar", operar: "Operar",
    atender_alertas: "Atender alertas", exportar: "Exportar"
};
const label = value => labels[value] || value.replaceAll("_", " ");
const canEdit = () => user?.permisos?.includes("roles.editar");

async function load(preferredId) {
    const data = await api("/api/roles-config");
    roles = data.roles; permissions = data.permisos;
    selectedRole = roles.find(role => role.id === preferredId) || roles.find(role => role.id === selectedRole?.id) || roles[0];
    render();
}

function render() {
    $("#roleCount").textContent = roles.length;
    $("#permissionCount").textContent = permissions.length;
    $("#userCount").textContent = roles.reduce((total, role) => total + Number(role.usuarios), 0);
    $("#newRole").hidden = !canEdit();
    $("#roleList").innerHTML = roles.map(role => `<button class="role-item ${selectedRole?.id === role.id ? "active" : ""}" data-role="${role.id}"><b>${safe(role.nombre)}</b><span>${role.usuarios} usuario${role.usuarios == 1 ? "" : "s"}</span></button>`).join("");
    if (!selectedRole) return;
    $("#roleName").value = selectedRole.nombre;
    $("#roleDescription").value = selectedRole.descripcion || "";
    const locked = selectedRole.id === 1 || !canEdit();
    $("#roleName").disabled = locked; $("#roleDescription").disabled = locked; $("#saveRole").hidden = locked;
    deleteRoleButton.hidden = !canEdit() || selectedRole.id <= 5;
    $("#roleWarning").textContent = selectedRole.id === 1 ? "El Administrador tiene acceso total y está protegido contra cambios accidentales." : "";
    const groups = Object.groupBy ? Object.groupBy(permissions, item => item.modulo) : permissions.reduce((result, item) => ((result[item.modulo] ||= []).push(item), result), {});
    $("#permissionGroups").innerHTML = Object.entries(groups).map(([module, entries]) => `<fieldset class="permission-group"><legend>${safe(label(module))}</legend>${entries.map(permission => `<label class="permission-option"><input type="checkbox" value="${permission.id}" ${selectedRole.permisos.includes(permission.id) || selectedRole.id === 1 ? "checked" : ""} ${locked ? "disabled" : ""}><span>${safe(label(permission.funcion))}</span></label>`).join("")}</fieldset>`).join("");
}

$("#roleList").onclick = event => {
    const button = event.target.closest("[data-role]");
    if (!button) return;
    selectedRole = roles.find(role => role.id == button.dataset.role); render();
};

$("#newRole").onclick = async () => {
    const name = prompt("Nombre del nuevo rol:");
    if (!name?.trim()) return;
    try {
        const result = await api("/api/roles-config", {method: "POST", body: JSON.stringify({nombre: name.trim(), descripcion: ""})});
        await load(result.id);
    } catch (error) { alert(error.message); }
};

$("#saveRole").onclick = async () => {
    if (!selectedRole || selectedRole.id === 1) return;
    const payload = {
        nombre: $("#roleName").value.trim(), descripcion: $("#roleDescription").value.trim(),
        permisos: [...document.querySelectorAll("#permissionGroups input:checked")].map(input => Number(input.value))
    };
    try {
        await api(`/api/roles-config/${selectedRole.id}`, {method: "PATCH", body: JSON.stringify(payload)});
        showMessage($("#message"), "Rol y permisos guardados correctamente.", true); await load(selectedRole.id);
    } catch (error) { showMessage($("#message"), error.message); }
};

deleteRoleButton.onclick = async () => {
    if (!selectedRole || selectedRole.id <= 5) return;
    if (!confirm(`¿Eliminar permanentemente el rol ${selectedRole.nombre}?`)) return;
    try { await api(`/api/roles-config/${selectedRole.id}`, {method: "DELETE"}); selectedRole = null; await load(); }
    catch (error) { alert(error.message); }
};

(async () => { user = await initSession(); await load(); })().catch(error => alert(error.message));
