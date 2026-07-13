# ComfyUI-Artfat-Resolution

A tiny, **elastic** aspect-ratio resolution picker for ComfyUI. Pick a ratio, set the short side of
your **base** (small) generation, and get `width`/`height` snapped to your chosen multiple — plus the
**final** upscaled size. Built for low-base + upscale workflows (Krea 2 / Selfism), but works anywhere.

No canvas, no dozen buttons — a handful of clean controls and a **live readout** that updates in real time.

## Node: **Artfat Resolution**

**Inputs**
- `aspect_ratio` — `9:16`, `2:3`, `3:4`, `1:1`, `4:3`, `3:2`, `16:9`, or **`Custom`**
- `base` — short side of the base generation (the long side is derived from the ratio)
- `multiple` — snap both sides to **8 / 16 / 32 / 64** (8 = latent minimum; 16/32 = safe for Krea 2 / Qwen)
- `custom_ratio_w` / `custom_ratio_h` — your own ratio, used only when `aspect_ratio = Custom`
- `upscale` — multiplier for the final size (`3.42` = 1.9 × 1.8)

**Outputs** — `width`, `height`, `final_width`, `final_height` (all `INT`, snapped to the multiple)

Wire `width`/`height` into an `EmptyLatentImage` for the base pass, and `final_width`/`final_height` into
your upscale target. The node draws `base W × H` and `final W × H` live at the bottom.

## Install
**ComfyUI-Manager → Install via Git URL:**
`https://github.com/artfat-creator/ComfyUI-Artfat-Resolution`

Or clone into `ComfyUI/custom_nodes/` and restart ComfyUI:
```
cd <ComfyUI>/custom_nodes
git clone https://github.com/artfat-creator/ComfyUI-Artfat-Resolution.git
```

No extra Python dependencies.

## License
MIT © artfat-creator
