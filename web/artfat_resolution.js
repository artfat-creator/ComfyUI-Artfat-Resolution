import { app } from "../../scripts/app.js";

// Mirror of the Python compute so the node shows the resulting resolution LIVE.
const SIZES = {
    "9:16 tall · 480×832": [480, 832],
    "2:3 portrait · 512×768": [512, 768],
    "3:4 portrait · 544×736": [544, 736],
    "4:5 portrait · 544×680": [544, 680],
    "1:1 square · 640×640": [640, 640],
    "4:3 landscape · 736×544": [736, 544],
    "3:2 landscape · 768×512": [768, 512],
    "16:9 wide · 832×480": [832, 480],
};
const CUSTOM_RATIO = "Custom ratio";
const MANUAL = "Manual W×H";

function snap(x, m) {
    m = parseInt(m) || 32;
    return Math.max(m, Math.round(x / m) * m);
}

function stage(dim, up, m) {
    return Math.abs(up - 1.0) < 1e-6 ? dim : snap(dim * up, m);
}

function calc(node) {
    const V = (n) => {
        const w = node.widgets && node.widgets.find((w) => w.name === n);
        return w ? w.value : undefined;
    };
    const size = V("size");
    if (size === undefined) return null;
    const m = V("multiple") || "32";
    const up1 = parseFloat(V("upscale_1")) || 1.0;
    const up2 = parseFloat(V("upscale_2")) || 1.0;

    let w, h;
    if (size === MANUAL) {
        w = parseInt(V("manual_w")) || 1200;
        h = parseInt(V("manual_h")) || 400;
    } else if (size === CUSTOM_RATIO) {
        const base = parseInt(V("base")) || 512;
        const rw = Math.max(1, parseInt(V("ratio_w")) || 1);
        const rh = Math.max(1, parseInt(V("ratio_h")) || 1);
        const short = snap(base, m);
        const long = snap((base * Math.max(rw, rh)) / Math.min(rw, rh), m);
        w = rw <= rh ? short : long;
        h = rw <= rh ? long : short;
    } else {
        const s = SIZES[size];
        if (!s) return null;
        w = s[0];
        h = s[1];
    }
    const mw = stage(w, up1, m), mh = stage(h, up1, m);
    const fw = stage(mw, up2, m), fh = stage(mh, up2, m);
    return { w, h, mw, mh, fw, fh };
}

app.registerExtension({
    name: "artfat.resolution.live",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "ArtfatResolution") return;
        // We only PAINT — no size override — so the node stays natively resizable.
        const orig = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function (ctx) {
            orig && orig.apply(this, arguments);
            if (this.flags && this.flags.collapsed) return;
            const r = calc(this);
            if (!r) return;

            // Build the stage chain, skipping stages that don't change the size.
            const lines = [["base", `${r.w} x ${r.h}`, "#7fd3ff"]];
            if (r.mw !== r.w || r.mh !== r.h) lines.push(["mid", `${r.mw} x ${r.mh}`, "#ffd27f"]);
            if (r.fw !== r.mw || r.fh !== r.mh) lines.push(["final", `${r.fw} x ${r.fh}`, "#9ae69a"]);

            ctx.save();
            ctx.font = "12px monospace";
            ctx.textAlign = "center";
            const cx = this.size[0] / 2;
            let y = this.size[1] - 8 - (lines.length - 1) * 14;
            for (const [label, val, color] of lines) {
                ctx.fillStyle = color;
                ctx.fillText(`${label}  ${val}`, cx, y);
                y += 14;
            }
            ctx.restore();
        };
    },
});
