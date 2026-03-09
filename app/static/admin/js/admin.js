(function () {
    function useFallback(value, fallback) {
        return Array.isArray(value) && value.length ? value : fallback;
    }

    function defaultLabels(days) {
        var list = [];
        for (var i = days - 1; i >= 0; i -= 1) {
            list.push("D-" + i);
        }
        return list;
    }

    function initLineChart(canvasId, labels, datasets) {
        var canvas = document.getElementById(canvasId);
        if (!canvas || !window.Chart) {
            return;
        }

        new window.Chart(canvas, {
            type: "line",
            data: {
                labels: labels,
                datasets: datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: "#d9e4ff",
                        },
                    },
                },
                scales: {
                    x: {
                        ticks: { color: "#b9c7e8", maxRotation: 0, autoSkip: true },
                        grid: { color: "rgba(147, 173, 212, 0.14)" },
                    },
                    y: {
                        ticks: { color: "#b9c7e8", precision: 0 },
                        grid: { color: "rgba(147, 173, 212, 0.14)" },
                    },
                },
            },
        });
    }

    function parseJSONScript(id) {
        var el = document.getElementById(id);
        if (!el) return {};
        try {
            return JSON.parse(el.textContent || "{}");
        } catch (err) {
            console.error("Invalid JSON in script#" + id, err);
            return {};
        }
    }

    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            var msg = form.getAttribute("data-confirm") || "Are you sure?";
            if (!window.confirm(msg)) {
                event.preventDefault();
            }
        });
    });

    var analytics = parseJSONScript("chartData");
    if (document.getElementById("adminVisitorsChart") && window.Chart) {
        var labels = useFallback(analytics.labels, defaultLabels(14));
        var visitors = useFallback(analytics.visitors, [18, 24, 30, 28, 35, 38, 44, 41, 49, 53, 57, 54, 61, 68]);
        var projects = useFallback(analytics.new_projects, [1, 0, 2, 1, 3, 2, 2, 4, 3, 2, 3, 5, 4, 6]);
        var reports = useFallback(analytics.reports, [0, 1, 0, 1, 2, 0, 1, 1, 2, 1, 1, 0, 2, 1]);

        initLineChart("adminVisitorsChart", labels, [
            {
                label: "Visitors per Day",
                data: visitors,
                borderColor: "#5ea0ff",
                backgroundColor: "rgba(94, 160, 255, 0.14)",
                fill: true,
                tension: 0.34,
            },
        ]);

        initLineChart("adminProjectsChart", labels, [
            {
                label: "Projects Uploaded",
                data: projects,
                borderColor: "#4fdaaf",
                backgroundColor: "rgba(79, 218, 175, 0.12)",
                fill: true,
                tension: 0.3,
            },
        ]);

        initLineChart("adminReportsChart", labels, [
            {
                label: "Reports Trend",
                data: reports,
                borderColor: "#ff7b91",
                backgroundColor: "rgba(255, 123, 145, 0.1)",
                fill: true,
                tension: 0.32,
            },
        ]);
    }

    var dashboardChartData = parseJSONScript("dashboardChartData");
    if (document.getElementById("adminDashboardPreviewChart") && window.Chart) {
        var dLabels = useFallback(dashboardChartData.labels, defaultLabels(7));
        var dVisitors = useFallback(dashboardChartData.visitors, [22, 28, 25, 35, 38, 44, 49]);
        var dProjects = useFallback(dashboardChartData.new_projects, [1, 2, 1, 3, 2, 4, 3]);
        var dReports = useFallback(dashboardChartData.reports, [0, 1, 0, 1, 1, 2, 1]);

        initLineChart("adminDashboardPreviewChart", dLabels, [
            {
                label: "Visitors",
                data: dVisitors,
                borderColor: "#5ea0ff",
                backgroundColor: "rgba(94, 160, 255, 0.1)",
                fill: true,
                tension: 0.35,
            },
            {
                label: "Projects",
                data: dProjects,
                borderColor: "#4fdaaf",
                backgroundColor: "rgba(79, 218, 175, 0.1)",
                fill: false,
                tension: 0.3,
            },
            {
                label: "Reports",
                data: dReports,
                borderColor: "#ff7b91",
                backgroundColor: "rgba(255, 123, 145, 0.1)",
                fill: false,
                tension: 0.3,
            },
        ]);
    }
    document.querySelectorAll(".settings-v2-copy").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var text = btn.getAttribute("data-copy-value") || "";
            var targetId = btn.getAttribute("data-copy-target") || "";
            if (!text && targetId) {
                var source = document.getElementById(targetId);
                if (source) text = (source.textContent || "").trim();
            }
            if (!text) return;

            var write = function () {
                if (window.navigator && window.navigator.clipboard && window.navigator.clipboard.writeText) {
                    return window.navigator.clipboard.writeText(text);
                }
                return Promise.reject(new Error("Clipboard API unavailable"));
            };

            write().then(function () {
                var old = btn.textContent;
                btn.textContent = "Copied";
                window.setTimeout(function () {
                    btn.textContent = old;
                }, 1000);
            }).catch(function () {
                btn.textContent = "Copy";
            });
        });
    });
})();


