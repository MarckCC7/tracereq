// Renderiza el grafo de dependencias entre requerimientos con vis-network.
// Se usa en la página del grafo y en la vista previa de la matriz ({ mini: true }).
var TraceGrafo = {
    render: function (container, url, opts) {
        opts = opts || {};
        fetch(url)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.nodes.length) {
                    container.innerHTML = '<p style="text-align:center;padding:2rem;color:#94a3b8">Sin requerimientos en este proyecto.</p>';
                    return;
                }
                var lista = data.nodes;
                if (opts.mini) {
                    // En la vista previa solo interesan los requerimientos que participan en alguna relación.
                    var conectados = {};
                    data.edges.forEach(function (e) { conectados[e.from] = conectados[e.to] = true; });
                    lista = lista.filter(function (n) { return conectados[n.id]; });
                    if (!lista.length) {
                        container.innerHTML = '<p style="text-align:center;padding:2rem;color:#94a3b8">Aún no hay relaciones.</p>';
                        return;
                    }
                }
                var nodes = new vis.DataSet(lista.map(function (n) {
                    return Object.assign({}, n, {
                        shape: 'box',
                        color: { background: n.color, border: n.color, highlight: { background: n.color, border: '#0f1d4d' } },
                        font: { color: '#fff', size: opts.mini ? 13 : 14, face: 'Inter, Segoe UI, sans-serif' },
                        borderWidth: 0, margin: opts.mini ? 6 : 11,
                        shapeProperties: { borderRadius: 8 },
                        shadow: { enabled: !opts.mini, color: 'rgba(16,24,64,.18)', size: 8, x: 0, y: 3 }
                    });
                }));
                var edges = new vis.DataSet(data.edges.map(function (e) {
                    return opts.mini ? Object.assign({}, e, { label: undefined }) : e;
                }));
                new vis.Network(container, { nodes: nodes, edges: edges }, {
                    layout: { improvedLayout: true },
                    physics: { stabilization: { iterations: 150 } },
                    interaction: { hover: true, zoomView: !opts.mini, dragView: !opts.mini },
                    edges: {
                        width: 1.6,
                        smooth: { type: 'curvedCW', roundness: 0.2 },
                        font: { size: 11, face: 'Inter, Segoe UI, sans-serif', strokeWidth: 3, strokeColor: '#fff' }
                    }
                });
            });
    }
};
