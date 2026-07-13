import { app } from "../../scripts/app.js";

// Mirror of the Python compute so the node shows the resulting resolution LIVE.
const RATIOS = {
    "9:16 (tall portrait)": [9, 16],
    "2:3 (portrait)": [2, 3],
    "3:4 (portrait)": [3, 4],
    "1:1 (square)": [1, 1],
    "4:3 (landscape)": [4, 3],
    "3:2 (landscape)": [3, 2],
    "16:9 (wide)": [16, 9],
};

function snap(x, m) {
    m = parseInt(m) || 32;
    return Math.max(m, Math.round(x / m) * m);
}

function calc(node) {
    const V = (n) => {
        const w = node.widgets && node.widgets.find((w) => w.name === n);
        return w ? w.value : undefined;
    };
    const ar = V("aspect_ratio");
    if (ar === undefined) return null;
    const base = parseInt(V("base")) || 512;
    const m = V("multiple") || "32";
    const up = parseFloat(V("upscale")) || 3.42;
    let rw, rh;
    if (ar === "Custom") {
        rw = Math.max(1, parseInt(V("custom_ratio_w")) || 1);
        rh = Math.max(1, parseInt(V("custom_ratio_h")) || 1);
    } else {
        const r = RATIOS[ar];
        if (!r) return null;
        rw = r[0];
        rh = r[1];
    }
    const short = snap(base, m);
    const long = snap((base * Math.max(rw, rh)) / Math.min(rw, rh), m);
    const w = rw <= rh ? short : long;
    const h = rw <= rh ? long : short;
    return { w, h, fw: snap(w * up, m), fh: snap(h * up, m) };
}

app.registerExtension({
    name: "artfat.resolution.live",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "ArtfatResolution") return;
        // Draw a live readout at the bottom of the node. We only PAINT — no computeSize /
        // size override — so the node stays natively resizable (elastic both ways).
        const orig = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function (ctx) {
            orig && orig.apply(this, arguments);
            if (this.flags && this.flags.collapsed) return;
            const r = calc(this);
            if (!r) return;
            ctx.save();
            ctx.font = "12px monospace";
            ctx.textAlign = "center";
            const cx = this.size[0] / 2;
            ctx.fillStyle = "#7fd3ff";
            ctx.fillText(`base  ${r.w} x ${r.h}`, cx, this.size[1] - 22);
            ctx.fillStyle = "#9ae69a";
            ctx.fillText(`final  ${r.fw} x ${r.fh}`, cx, this.size[1] - 8);
            ctx.restore();
        };
    },
});
