let products = [], moves = [], pools = [], staff = [], currentUser;

const can = permission => currentUser?.permisos?.includes(permission);
const normalize = value => String(value ?? "").toLocaleLowerCase("es");

async function load() {
    const optionsPromise = can("inventario.registrar")
        ? api("/api/inventario-opciones")
        : Promise.resolve({piscinas: [], colaboradores: []});
    const [loadedProducts, loadedMoves, options] = await Promise.all([
        api("/api/productos").then(result => result.productos),
        api("/api/movimientos").then(result => result.movimientos),
        optionsPromise
    ]);
    products = loadedProducts;
    moves = loadedMoves;
    pools = options.piscinas;
    staff = options.colaboradores;
    render();
    $("#moveProduct").innerHTML = products.filter(item => item.estado).map(item =>
        `<option value="${item.id}">${safe(item.nombre)} (${Number(item.stock_actual).toFixed(2)} ${safe(item.unidad)})</option>`
    ).join("");
    $("#movePool").innerHTML = pools.map(item =>
        `<option value="${item.id}">${safe(item.codigo)}</option>`
    ).join("");
    $("#moveStaff").innerHTML = staff.map(item =>
        `<option value="${item.id}">${safe(item.nombre)}</option>`
    ).join("");
}

function render() {
    $("#productCount").textContent = products.filter(item => item.estado).length;
    $("#lowCount").textContent = products.filter(item => item.estado && Number(item.stock_actual) <= Number(item.stock_minimo)).length;
    $("#moveCount").textContent = moves.length;

    const productTerm = normalize($("#productSearch").value);
    const productState = $("#productStateFilter").value;
    const filteredProducts = products.filter(item => {
        const matchesText = [item.codigo, item.nombre, item.marca].some(value => normalize(value).includes(productTerm));
        const low = item.estado && Number(item.stock_actual) <= Number(item.stock_minimo);
        const matchesState = !productState
            || (productState === "active" && item.estado)
            || (productState === "low" && low)
            || (productState === "inactive" && !item.estado);
        return matchesText && matchesState;
    });

    $("#productRows").innerHTML = filteredProducts.map(item => {
        const low = item.estado && Number(item.stock_actual) <= Number(item.stock_minimo);
        const label = !item.estado ? "Inactivo" : low ? "Stock bajo" : "Disponible";
        const actions = can("inventario.registrar")
            ? `<button class="action" data-edit-product="${item.id}">Editar</button><button class="action" data-toggle-product="${item.id}">${item.estado ? "Desactivar" : "Activar"}</button><button class="action danger-text" data-delete-product="${item.id}">Eliminar</button>`
            : "—";
        return `<tr class="${low ? "stock-low-row" : ""}"><td>${safe(item.codigo)}</td><td><b>${safe(item.nombre)}</b></td><td>${safe(item.marca)}</td><td class="${low ? "stock-low-value" : ""}">${Number(item.stock_actual).toFixed(2)} ${safe(item.unidad)}</td><td>${Number(item.stock_minimo).toFixed(2)}</td><td><span class="badge ${!item.estado || low ? "off" : ""}">${label}</span></td><td>${actions}</td></tr>`;
    }).join("") || `<tr><td colspan="7" class="empty-state">No se encontraron productos.</td></tr>`;

    const moveTerm = normalize($("#moveSearch").value);
    const moveType = $("#moveTypeFilter").value;
    const poolType = $("#poolTypeFilter").value;
    const filteredMoves = moves.filter(item =>
        (!moveType || item.tipo === moveType)
        && (!poolType || item.tipo_piscina === poolType)
        && [item.producto, item.piscina, item.tipo_piscina, item.responsable, item.lote, item.observacion].some(value => normalize(value).includes(moveTerm))
    );
    $("#moveRows").innerHTML = filteredMoves.map(item => `<tr><td>${new Date(item.creado_en).toLocaleString()}</td><td><span class="badge ${item.tipo === "Salida" ? "pending" : ""}">${item.tipo}</span></td><td>${safe(item.producto)}</td><td>${Number(item.cantidad).toFixed(2)} ${safe(item.unidad)}</td><td>${safe(item.lote || "—")}</td><td>${item.fecha_vencimiento ? new Date(`${item.fecha_vencimiento}T00:00:00`).toLocaleDateString() : "—"}</td><td>${safe(item.piscina || "—")}</td><td>${item.tipo_piscina ? `<span class="badge ${item.tipo_piscina === "Engorde" ? "pool-type-engorde" : "pool-type-precria"}">${safe(item.tipo_piscina)}</span>` : "—"}</td><td>${safe(item.responsable || "—")}</td><td class="movement-note">${safe(item.observacion || "—")}</td><td>${can("inventario.registrar") ? `<button class="action danger-text" data-delete-move="${item.id}">Eliminar</button>` : "—"}</td></tr>`).join("") || `<tr><td colspan="11" class="empty-state">No se encontraron movimientos.</td></tr>`;
}

function editProduct(product) {
    $("#productForm").reset();
    $("#productId").value = product.id;
    $("#productCode").value = product.codigo;
    $("#productCode").disabled = true;
    $("#productName").value = product.nombre;
    $("#productBrand").value = product.marca;
    $("#productUnit").value = product.unidad;
    $("#productMin").value = Number(product.stock_minimo);
    $("#productDialogTitle").textContent = "Editar producto";
    showMessage($("#productMessage"), "");
    openDialog($("#productDialog"));
}

$("#productRows").onclick = async event => {
    const editId = event.target.dataset.editProduct;
    const toggleId = event.target.dataset.toggleProduct;
    const deleteId = event.target.dataset.deleteProduct;
    const product = products.find(item => item.id == (editId || toggleId || deleteId));
    if (!product) return;
    if (editId) return editProduct(product);
    if (toggleId) {
        const action = product.estado ? "desactivar" : "activar";
        if (!confirm(`¿Desea ${action} el producto ${product.nombre}?`)) return;
        try {
            await api(`/api/productos/${product.id}`, {method: "PATCH", body: JSON.stringify({estado: !product.estado})});
            await load();
        } catch (error) { alert(error.message); }
        return;
    }
    if (!deleteId || !confirm(`¿Eliminar permanentemente el producto ${product.nombre}?`)) return;
    try {
        await api(`/api/productos/${product.id}`, {method: "DELETE"});
        await load();
    } catch (error) { alert(error.message); }
};

$("#moveRows").onclick = async event => {
    if (!event.target.dataset.deleteMove) return;
    if (!confirm("¿Eliminar este movimiento y recalcular el stock del producto?")) return;
    try {
        await api(`/api/movimientos/${event.target.dataset.deleteMove}`, {method: "DELETE"});
        await load();
    } catch (error) { alert(error.message); }
};

function toggleType() {
    const exit = $("#moveType").value === "Salida";
    document.querySelectorAll(".exit-field").forEach(item => item.classList.toggle("hidden", !exit));
    document.querySelectorAll(".entry-field").forEach(item => item.classList.toggle("hidden", exit));
}

$("#moveType").onchange = toggleType;
$("#productSearch").oninput = render;
$("#productStateFilter").onchange = render;
$("#moveSearch").oninput = render;
$("#moveTypeFilter").onchange = render;
$("#poolTypeFilter").onchange = render;
document.querySelectorAll(".close,.cancel").forEach(item => item.onclick = () => item.closest("dialog").close());

$("#newProduct").onclick = () => {
    $("#productForm").reset();
    $("#productId").value = "";
    $("#productCode").disabled = false;
    $("#productUnit").value = "kg";
    $("#productDialogTitle").textContent = "Nuevo producto";
    showMessage($("#productMessage"), "");
    openDialog($("#productDialog"));
};

$("#newMove").onclick = () => {
    $("#moveForm").reset();
    showMessage($("#moveMessage"), "");
    toggleType();
    openDialog($("#moveDialog"));
};

$("#productForm").onsubmit = async event => {
    event.preventDefault();
    const id = $("#productId").value;
    try {
        await api(id ? `/api/productos/${id}` : "/api/productos", {
            method: id ? "PATCH" : "POST",
            body: JSON.stringify({
                ...(id ? {} : {codigo: $("#productCode").value}),
                nombre: $("#productName").value,
                marca: $("#productBrand").value,
                unidad: $("#productUnit").value,
                stock_minimo: Number($("#productMin").value)
            })
        });
        $("#productDialog").close();
        await load();
    } catch (error) { showMessage($("#productMessage"), error.message); }
};

$("#moveForm").onsubmit = async event => {
    event.preventDefault();
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
        await load();
    } catch (error) { showMessage($("#moveMessage"), error.message); }
};

(async () => {
    currentUser = await initSession();
    $("#newProduct").hidden = !can("inventario.registrar");
    $("#newMove").hidden = !can("inventario.registrar");
    await load();
})().catch(error => alert(error.message));
