const form = document.querySelector('#loginForm'),
    message = document.querySelector('#message'),
    submit = form.querySelector('button[type=submit]');
fetch('/api/me').then(r => {
    if (r.ok) location.href = '/dashboard.html'
}).catch(() => {});
document.querySelector('#togglePassword').onclick = () => {
    const p = document.querySelector('#password');
    p.type = p.type === 'password' ? 'text' : 'password'
};
form.onsubmit = async e => {
    e.preventDefault();
    message.textContent = '';
    submit.disabled = true;
    submit.firstChild.textContent = 'Validando... ';
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                usuario: form.usuario.value,
                password: form.password.value
            })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        message.className = 'message success';
        message.textContent = 'Acceso correcto. Cargando panel...';
        setTimeout(() => location.href = '/dashboard.html', 450)
    } catch (err) {
        message.className = 'message';
        message.textContent = err.message || 'No fue posible conectar con el sistema.';
        submit.disabled = false;
        submit.firstChild.textContent = 'Ingresar al sistema '
    }
};
