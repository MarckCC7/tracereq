// main.js

// Menús desplegables (exportar, crear, acciones de fila)
document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-dropdown-toggle]');
    var openMenus = document.querySelectorAll('.dropdown-menu.show');

    if (trigger) {
        var menu = trigger.parentElement.querySelector('.dropdown-menu');
        var wasOpen = menu.classList.contains('show');
        openMenus.forEach(function (m) { m.classList.remove('show'); });
        if (!wasOpen) {
            menu.classList.add('show');
            // Dentro de tablas con scroll el menú se recortaría: se posiciona fijo respecto al botón.
            if (trigger.closest('.table-wrap')) {
                var r = trigger.getBoundingClientRect();
                menu.style.position = 'fixed';
                menu.style.right = 'auto';
                menu.style.left = Math.max(8, r.right - menu.offsetWidth) + 'px';
                var top = r.bottom + 6;
                if (top + menu.offsetHeight > window.innerHeight - 8) top = r.top - menu.offsetHeight - 6;
                menu.style.top = top + 'px';
            }
        }
        return;
    }

    openMenus.forEach(function (menu) {
        if (!menu.parentElement.contains(e.target)) menu.classList.remove('show');
    });
});

window.addEventListener('scroll', function () {
    document.querySelectorAll('.table-wrap .dropdown-menu.show').forEach(function (m) { m.classList.remove('show'); });
}, true);

// Sidebar en pantallas pequeñas
document.addEventListener('click', function (e) {
    if (e.target.closest('[data-nav-toggle]')) document.body.classList.toggle('nav-open');
    else if (e.target.closest('[data-nav-close]')) document.body.classList.remove('nav-open');
});

// Ctrl+K / Cmd+K enfoca la búsqueda global
document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        var input = document.getElementById('global-search');
        if (input) { e.preventDefault(); input.focus(); input.select(); }
    }
    if (e.key === 'Escape') document.body.classList.remove('nav-open');
});

// Ordenar tablas en el cliente: <th data-sort> (usa data-value de la celda si existe)
document.addEventListener('click', function (e) {
    var th = e.target.closest('th[data-sort]');
    if (!th) return;
    var table = th.closest('table');
    var tbody = table.tBodies[0];
    var idx = Array.prototype.indexOf.call(th.parentElement.children, th);
    var asc = !th.classList.contains('asc');
    table.querySelectorAll('th[data-sort]').forEach(function (h) { h.classList.remove('asc', 'desc'); });
    th.classList.add(asc ? 'asc' : 'desc');

    var val = function (row) {
        var cell = row.children[idx];
        var v = cell.getAttribute('data-value');
        return v !== null ? v : cell.textContent.trim();
    };
    var rows = Array.prototype.slice.call(tbody.rows);
    rows.sort(function (a, b) {
        var x = val(a), y = val(b);
        var nx = parseFloat(x), ny = parseFloat(y);
        var cmp = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : x.localeCompare(y, 'es', { numeric: true });
        return asc ? cmp : -cmp;
    });
    rows.forEach(function (r) { tbody.appendChild(r); });
});

// Filtro instantáneo de filas: <input data-table-filter="#idTabla">
document.addEventListener('input', function (e) {
    var sel = e.target.getAttribute('data-table-filter');
    if (!sel) return;
    var q = e.target.value.toLowerCase().trim();
    var table = document.querySelector(sel);
    var shown = 0;
    Array.prototype.forEach.call(table.tBodies[0].rows, function (row) {
        var match = row.textContent.toLowerCase().indexOf(q) !== -1;
        row.style.display = match ? '' : 'none';
        if (match) shown++;
    });
    var counter = document.querySelector('[data-filter-count="' + sel + '"]');
    if (counter) counter.textContent = shown;
});

// Protección CSRF: todo formulario POST lleva el token de la sesión (el servidor rechaza los que no lo traen).
(function () {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (!meta) return;
    var agregar = function (form) {
        if ((form.method || '').toLowerCase() !== 'post' || form.querySelector('input[name="csrf_token"]')) return;
        var input = document.createElement('input');
        input.type = 'hidden'; input.name = 'csrf_token'; input.value = meta.content;
        form.appendChild(input);
    };
    document.querySelectorAll('form').forEach(agregar);
    document.addEventListener('submit', function (e) { agregar(e.target); }, true);
})();
