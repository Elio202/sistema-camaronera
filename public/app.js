let users = [],
    roles = [],
    current = null;
const $ = s => document.querySelector(s),
    dialog = $('#userDialog'),
    form = $('#userForm');
document.querySelector('aside nav').innerHTML = '<small>OPERACIÓN</small><a href="/dashboard.html">Panel principal</a><a href="/piscinas.html">Piscinas</a><a href="/personal.html">Personal y actividades</a><a href="/inventario.html">Inventario</a><small>ADMINISTRACIÓN</small><a class="active" href="/app.html">Usuarios</a><a href="/roles.html">Roles y permisos</a>';
async function api(path, options = {}) {
    const r = await fetch(path, {
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        },
        ...options
    });
    if (r.status === 401) {
        location.href = '/login.html';
        throw new Error('Sesión vencida')
    }
    const d = await r.json();
    if (!r.ok) throw new Error(d.error);
    return d
}

function can(p) {
    return current?.permisos.includes(p)
}
async function load() {
    current = (await api('/api/me')).usuario;
    $('#currentName').textContent = current.nombre;
    $('#currentRole').textContent = current.rol;
    $('#avatar').textContent = current.nombre[0].toUpperCase();
    const data = await Promise.all([api('/api/usuarios'), api('/api/roles')]);
    users = data[0].usuarios;
    roles = data[1].roles;
    $('#newUser').hidden = !can('usuarios.crear');
    $('#rol').innerHTML = roles.map(r => `<option value="${r.id}">${r.nombre}</option>`).join('');
    render()
}

function render() {
    const q = $('#search').value.toLowerCase();
    const filtered = users.filter(u => [u.nombre, u.nombre_usuario, u.correo, u.rol].some(x => x.toLowerCase().includes(q)));
    $('#total').textContent = users.length;
    $('#active').textContent = users.filter(u => u.estado).length;
    $('#roleCount').textContent = new Set(users.map(u => u.rol_id)).size;
    $('#userRows').innerHTML = filtered.map(u => `<tr><td class="name-cell"><b>${safe(u.nombre)}</b><small>@${safe(u.nombre_usuario)}</small></td><td>${safe(u.correo)}</td><td>${safe(u.rol)}</td><td><span class="badge ${u.estado?'':'off'}">${u.estado?'Activo':'Inactivo'}</span></td><td>${can('usuarios.editar')?`<button class="action" data-edit="${u.id}">Editar</button>`:''}${can('usuarios.cambiar_estado')?`<button class="action" data-toggle="${u.id}">${u.estado?'Desactivar':'Activar'}</button>`:''}${can('usuarios.editar')&&u.id!==1&&u.id!==current.id?`<button class="action danger-text" data-delete="${u.id}">Eliminar</button>`:''}</td></tr>`).join('') || '<tr><td colspan="5">No se encontraron usuarios.</td></tr>'
}

function safe(v) {
    const d = document.createElement('div');
    d.textContent = v;
    return d.innerHTML
}

function openUser(user = null) {
    form.reset();
    $('#userId').value = user?.id || '';
    $('#dialogTitle').textContent = user ? 'Editar usuario' : 'Nuevo usuario';
    $('#nombreUsuario').disabled = !!user;
    $('#newPassword').required = !user;
    $('#passwordHint').textContent = user ? '(dejar vacío para conservarla)' : '(mínimo 8 caracteres)';
    if (user) {
        $('#nombre').value = user.nombre;
        $('#nombreUsuario').value = user.nombre_usuario;
        $('#correo').value = user.correo;
        $('#rol').value = user.rol_id
    }
    $('#formMessage').textContent = '';
    dialog.showModal()
}
$('#search').oninput = render;
$('#newUser').onclick = () => openUser();
$('#closeDialog').onclick = $('#cancelDialog').onclick = () => dialog.close();
$('#logout').onclick = async () => {
    await api('/api/logout', {
        method: 'POST'
    });
    location.href = '/login.html'
};
$('#userRows').onclick = async e => {
    const edit = e.target.dataset.edit,
        toggle = e.target.dataset.toggle,
        remove = e.target.dataset.delete;
    if (edit) openUser(users.find(u => u.id == edit));
    if (toggle) {
        const u = users.find(u => u.id == toggle);
        if (!confirm(`¿Desea ${u.estado?'desactivar':'activar'} a ${u.nombre}?`)) return;
        await api(`/api/usuarios/${u.id}`, {
            method: 'PATCH',
            body: JSON.stringify({
                estado: u.estado ? 0 : 1
            })
        });
        await load()
    }
    if (remove) {
        const u = users.find(user => user.id == remove);
        if (!confirm(`¿Eliminar permanentemente al usuario ${u.nombre}?`)) return;
        try { await api(`/api/usuarios/${u.id}`, {method: 'DELETE'}); await load(); }
        catch (error) { alert(error.message); }
    }
};
form.onsubmit = async e => {
    e.preventDefault();
    const id = $('#userId').value;
    const payload = {
        nombre: $('#nombre').value.trim(),
        correo: $('#correo').value.trim(),
        rol_id: Number($('#rol').value)
    };
    if (!id) {
        payload.nombre_usuario = $('#nombreUsuario').value.trim();
        payload.password = $('#newPassword').value
    } else if ($('#newPassword').value) payload.password = $('#newPassword').value;
    try {
        await api(id ? `/api/usuarios/${id}` : '/api/usuarios', {
            method: id ? 'PATCH' : 'POST',
            body: JSON.stringify(payload)
        });
        dialog.close();
        await load()
    } catch (err) {
        $('#formMessage').textContent = err.message
    }
};
load().catch(console.error);
