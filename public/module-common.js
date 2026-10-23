const $ = selector => document.querySelector(selector);
async function api(path, options = {}) {
    let response;
    try {
        response = await fetch(path, {
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            },
            ...options
        });
    } catch (error) {
        throw new Error("No se pudo conectar con el servidor. Verifica que esté encendido e inténtalo nuevamente.");
    }
    const data = await response.json().catch(() => ({
        error: "Respuesta inválida del servidor."
    }));
    if (response.status === 401) {
        location.href = "/login.html";
        throw new Error("Sesión vencida.")
    }
    if (!response.ok) throw new Error(data.error || "No fue posible completar la operación.");
    return data;
}
async function initSession() {
    const {
        usuario
    } = await api("/api/me");
    $("#currentName").textContent = usuario.nombre;
    $("#currentRole").textContent = usuario.rol;
    $("#avatar").textContent = usuario.nombre[0].toUpperCase();
    const routePermissions = {
        "/piscinas.html": "piscinas.ver",
        "/personal.html": "personal.ver",
        "/inventario.html": "inventario.ver",
        "/alertas.html": "alertas.ver",
        "/app.html": "usuarios.ver",
        "/roles.html": "roles.ver"
    };
    document.querySelectorAll("aside nav a").forEach(link => {
        const route = new URL(link.href, location.origin).pathname;
        const permission = routePermissions[route];
        if (permission && !usuario.permisos.includes(permission)) link.hidden = true;
    });
    const currentPermission = routePermissions[location.pathname];
    if (currentPermission && !usuario.permisos.includes(currentPermission)) {
        location.href = "/dashboard.html";
        throw new Error("No tiene permiso para acceder a este módulo.");
    }
    $("#logout").onclick = async () => {
        await api("/api/logout", {
            method: "POST",
            body: "{}"
        });
        location.href = "/login.html"
    };
    return usuario;
}

function safe(value) {
    const node = document.createElement("div");
    node.textContent = value ?? "";
    return node.innerHTML
}

function showMessage(element, message, ok = false) {
    element.textContent = message;
    element.className = `message ${ok?"success":""}`
}

function openDialog(dialog) {
    dialog.showModal()
}

function closeDialog(dialog) {
    dialog.close()
}
