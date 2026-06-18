/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import {
    Component,
    onWillStart,
    onWillUnmount,
    useState,
    useRef,
    useEffect,
} from "@odoo/owl";

export class CostEstimateDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.currency = { symbol: "$", position: "before" };
        this.charts = {};

        this.monthRef = useRef("monthChart");
        this.stateRef = useRef("stateChart");
        this.structureRef = useRef("structureChart");
        this.categoryRef = useRef("categoryChart");
        this.detailRef = useRef("detailChart");

        this.state = useState({
            loading: true,
            data: null,
            detail: null,
            filters: {
                year: new Date().getFullYear(),
                partner_id: false,
                state: false,
                scope: false,
                architecture: false,
                user_id: false,
            },
        });

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.loadData();
        });

        useEffect(
            () => {
                if (!this.state.loading && this.state.data) {
                    this.renderCharts();
                }
            },
            () => [this.state.data]
        );

        useEffect(
            () => {
                if (this.state.detail) {
                    this.renderDetailChart();
                }
            },
            () => [this.state.detail]
        );

        onWillUnmount(() => this.destroyCharts());
    }

    async loadData() {
        this.state.loading = true;
        const data = await this.orm.call(
            "cost.estimate",
            "retrieve_dashboard_data",
            [this.state.filters]
        );
        this.currency = data.currency;
        this.state.data = data;
        this.state.loading = false;
    }

    onFilterChange(key, value) {
        let v = value;
        if (value === "" || value === "false") {
            v = false;
        } else if (["partner_id", "user_id"].includes(key)) {
            v = parseInt(value);
        } else if (key === "year" && value !== "all") {
            v = parseInt(value);
        }
        this.state.filters[key] = v;
        this.state.detail = null;
        this.loadData();
    }

    async onSelectDetail(value) {
        if (!value) {
            this.state.detail = null;
            return;
        }
        const detail = await this.orm.call("cost.estimate", "get_estimate_detail", [
            parseInt(value),
        ]);
        this.state.detail = detail && detail.id ? detail : null;
    }

    openEstimate(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cost.estimate",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openList() {
        this.action.doAction("software_cost_estimation.action_cost_estimate");
    }

    // ---------------------------------------------------------------- helpers
    formatCurrency(v) {
        const n = new Intl.NumberFormat(undefined, {
            maximumFractionDigits: 0,
        }).format(Math.round(v || 0));
        return this.currency.position === "after"
            ? `${n} ${this.currency.symbol}`
            : `${this.currency.symbol}${n}`;
    }

    formatNumber(v) {
        return new Intl.NumberFormat(undefined, {
            maximumFractionDigits: 0,
        }).format(Math.round(v || 0));
    }

    // ----------------------------------------------------------------- charts
    destroyCharts() {
        Object.values(this.charts).forEach((c) => c && c.destroy());
        this.charts = {};
    }

    get baseOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
        };
    }

    renderCharts() {
        if (!window.Chart || !this.state.data) {
            return;
        }
        this.destroyCharts();
        const c = this.state.data.charts;
        const fmt = (val) => this.formatCurrency(val);

        if (this.monthRef.el) {
            this.charts.month = new window.Chart(this.monthRef.el, {
                type: "bar",
                data: {
                    labels: c.by_month.labels,
                    datasets: [
                        {
                            data: c.by_month.values,
                            backgroundColor: "#378ADD",
                            borderRadius: 4,
                            maxBarThickness: 38,
                        },
                    ],
                },
                options: {
                    ...this.baseOptions,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: { label: (ctx) => fmt(ctx.parsed.y) },
                        },
                    },
                    scales: {
                        y: {
                            ticks: { callback: (v) => this.formatNumber(v) },
                        },
                    },
                },
            });
        }

        if (this.stateRef.el && c.by_state.labels.length) {
            this.charts.state = new window.Chart(this.stateRef.el, {
                type: "doughnut",
                data: {
                    labels: c.by_state.labels,
                    datasets: [
                        {
                            data: c.by_state.values,
                            backgroundColor: c.by_state.colors,
                            borderWidth: 0,
                        },
                    ],
                },
                options: {
                    ...this.baseOptions,
                    cutout: "62%",
                    plugins: {
                        legend: { display: true, position: "bottom" },
                        tooltip: {
                            callbacks: { label: (ctx) => `${ctx.label}: ${fmt(ctx.parsed)}` },
                        },
                    },
                },
            });
        }

        if (this.structureRef.el) {
            this.charts.structure = new window.Chart(this.structureRef.el, {
                type: "doughnut",
                data: {
                    labels: c.cost_structure.labels,
                    datasets: [
                        {
                            data: c.cost_structure.values,
                            backgroundColor: c.cost_structure.colors,
                            borderWidth: 0,
                        },
                    ],
                },
                options: {
                    ...this.baseOptions,
                    cutout: "62%",
                    plugins: {
                        legend: { display: true, position: "bottom" },
                        tooltip: {
                            callbacks: { label: (ctx) => `${ctx.label}: ${fmt(ctx.parsed)}` },
                        },
                    },
                },
            });
        }

        if (this.categoryRef.el && c.by_category.labels.length) {
            this.charts.category = new window.Chart(this.categoryRef.el, {
                type: "bar",
                data: {
                    labels: c.by_category.labels,
                    datasets: [
                        {
                            data: c.by_category.values,
                            backgroundColor: "#1D9E75",
                            borderRadius: 4,
                        },
                    ],
                },
                options: {
                    ...this.baseOptions,
                    indexAxis: "y",
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: { label: (ctx) => fmt(ctx.parsed.x) },
                        },
                    },
                    scales: {
                        x: { ticks: { callback: (v) => this.formatNumber(v) } },
                    },
                },
            });
        }
    }

    renderDetailChart() {
        if (!window.Chart || !this.state.detail || !this.detailRef.el) {
            return;
        }
        if (this.charts.detail) {
            this.charts.detail.destroy();
        }
        const s = this.state.detail.structure;
        this.charts.detail = new window.Chart(this.detailRef.el, {
            type: "doughnut",
            data: {
                labels: s.labels,
                datasets: [{ data: s.values, backgroundColor: s.colors, borderWidth: 0 }],
            },
            options: {
                ...this.baseOptions,
                cutout: "60%",
                plugins: {
                    legend: { display: true, position: "bottom" },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.label}: ${this.formatCurrency(ctx.parsed)}`,
                        },
                    },
                },
            },
        });
    }
}

CostEstimateDashboard.template = "software_cost_estimation.CostEstimateDashboard";

registry.category("actions").add("cost_estimate_dashboard", CostEstimateDashboard);
