let products = [],
    moves = [],
    pools = [],
    staff = [],
    currentUser;
const can = permission => currentUser?.permisos?.includes(permission);
async function load() {
    [products, moves, pools, staff] = await Promise.all([api("/api/productos").then(x => x.productos), api("/api/movimientos").then(x => x.movimientos), api("/api/piscinas").then(x => x.piscinas), api("/api/colaboradores").then(x => x.colaboradores)]);
    render();
    $("#moveProduct").innerHTML = products.filter(x => x.estado).map(x => `<option value="${x.id}">${safe(x.nombre)} (${x.stock_actual} ${x.unidad})</option>`).join("");
    $("#movePool").innerHTML = pools.filter(x => x.estado).map(x => `<option value="${x.id}">${safe(x.codigo_productivo)}</option>`).join("");
    $("#moveStaff").innerHTML = staff.filter(x => x.estado).map(x => `<option value="${x.id}">${safe(x.nombre)}</option>`).join("")
}

function render() {
    $("#productCount").textContent = products.filter(x => x.estado).length;
    $("#lowCount").textContent = products.filter(x => Number(x.stock_actual) <= Number(x.stock_minimo)).length;
    $("#moveCount").textContent = moves.length;
    $("#productRows").innerHTML = products.map(x => `<tr><td>${safe(x.codigo)}</td><td><b>${safe(x.nombre)}</b></td><td>${safe(x.marca)}</td><td>${Number(x.stock_actual).toFixed(2)} ${safe(x.unidad)}</td><td>${Number(x.stock_minimo).toFixed(2)}</td><td><span class="badge ${Number(x.stock_actual)<=Number(x.stock_minimo)?"off":""}">${Number(x.stock_actual)<=Number(x.stock_minimo)?"Stock bajo":"Disponible"}</span></td><td>${can("inventario.registrar") ? `<button class="action danger-text" data-delete-product="${x.id}">Eliminar</button>` : "—"}</td></tr>`).join("");
    $("#moveRows").innerHTML = moves.map(x => `<tr><td>${new Date(x.creado_en).toLocaleString()}</td><td><span class="badge ${x.tipo==="Salida"?"pending":""}">${x.tipo}</span></td><td>${safe(x.producto)}</td><td>${Number(x.cantidad).toFixed(2)} ${safe(x.unidad)}</td><td>${safe(x.piscina||"—")}</td><td>${safe(x.responsable||"—")}</td><td>${can("inventario.registrar") ? `<button class="action danger-text" data-delete-move="${x.id}">Eliminar</button>` : "—"}</td></tr>`).join("")
}

$("#productRows").onclick = async event => {
    if (!event.target.dataset.deleteProduct) return;
    const product = products.find(item => item.id == event.target.dataset.deleteProduct);
    if (!confirm(`¿Eliminar permanentemente el producto ${product.nombre}?`)) return;
    try { await api(`/api/productos/${product.id}`, {method: "DELETE"}); await load(); }
    catch (error) { alert(error.message); }
};

$("#moveRows").onclick = async event => {
    if (!event.target.dataset.deleteMove) return;
    if (!confirm("¿Eliminar este movimiento y recalcular el stock del producto?")) return;
    try { await api(`/api/movimientos/${event.target.dataset.deleteMove}`, {method: "DELETE"}); await load(); }
    catch (error) { alert(error.message); }
};

function toggleType() {
    const exit = $("#moveType").value === "Salida";
    document.querySelectorAll(".exit-field").forEach(x => x.classList.toggle("hidden", !exit));
    document.querySelectorAll(".entry-field").forEach(x => x.classList.toggle("hidden", exit))
}
$("#moveType").onchange = toggleType;
document.querySelectorAll(".close,.cancel").forEach(x => x.onclick = () => x.closest("dialog").close());
$("#newProduct").onclick = () => {
    $("#productForm").reset();
    openDialog($("#productDialog"))
};
$("#newMove").onclick = () => {
    $("#moveForm").reset();
    toggleType();
    openDialog($("#moveDialog"))
};
$("#productForm").onsubmit = async e => {
    e.preventDefault();
    try {
        await api("/api/productos", {
            method: "POST",
            body: JSON.stringify({
                codigo: $("#productCode").value,
                nombre: $("#productName").value,
                marca: $("#productBrand").value,
                unidad: $("#productUnit").value,
                stock_minimo: Number($("#productMin").value)
            })
        });
        $("#productDialog").close();
        load()
    } catch (err) {
        showMessage($("#productMessage"), err.message)
    }
};
$("#moveForm").onsubmit = async e => {
    e.preventDefault();
    const exit = $("#moveType").value === "Salida";
    try {
        await api("/api/movimientos", {
            method: "POST",
            body: JSON.stringify({
                tipo: $("#moveType").value,
                producto_id: $("#moveProduct").value,
                cantidad: Number($("#moveAmount").value),
                piscina_id: exit ? $("#movePool").value : null,
                responsable_id: exit ? $("#moveStaff").value : null,
                lote: exit ? null : $("#moveLot").value,
                fecha_vencimiento: exit ? null : $("#moveExpiry").value,
                observacion: $("#moveNote").value
            })
        });
        $("#moveDialog").close();
        load()
    } catch (err) {
        showMessage($("#moveMessage"), err.message)
    }
};
(async () => {
    currentUser = await initSession();
    await load()
})().catch(err => alert(err.message));
