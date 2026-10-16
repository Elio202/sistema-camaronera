const $ = selector => document.querySelector(selector);
if (location.pathname.endsWith('/roles.html')) document.querySelector('aside nav').innerHTML = '<small>OPERACIÓN</small><a href="/dashboard.html">Panel principal</a><a href="/piscinas.html">Piscinas</a><a href="/personal.html">Personal y actividades</a><a href="/inventario.html">Inventario</a><small>ADMINISTRACIÓN</small><a href="/app.html">Usuarios</a><a class="active" href="/roles.html">Roles y permisos</a>';
async function initialize() {
    const response = await fetch('/api/me');
    if (!response.ok) {
        location.href = '/login.html';
        return
    }
    const {
        usuario
    } = await response.json();
    $('#currentName').textContent = usuario.nombre;
    $('#currentRole').textContent = usuario.rol;
    $('#avatar').textContent = usuario.nombre.charAt(0).toUpperCase();
}
$('#logout').onclick = async () => {
    await fetch('/api/logout', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: '{}'
    });
    location.href = '/login.html'
};
initialize().catch(() => location.href = '/login.html');