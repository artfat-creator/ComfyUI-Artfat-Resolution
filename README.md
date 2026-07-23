# ComfyUI-Artfat-Resolution

A tiny, **elastic** resolution picker for ComfyUI built for **low-base + upscale** workflows
(Krea 2 / Selfism), but works anywhere. Three ways to set the size, two upscale stages, and a
**live readout** so you always know the final file size before you render.

No canvas, no dozen buttons — clean controls and a real-time readout.

## Node: **Artfat Resolution**

### Three modes (one `size` dropdown)
- **Preset size** — pick a ready `W×H` (e.g. `2:3 portrait · 512×768`). Beginner-friendly.
- **Custom ratio** — set `ratio_w:ratio_h` + `base` short side (e.g. `3:1` banners).
- **Manual W×H** — type an **exact** `manual_w` / `manual_h`. **Not snapped** — exact stays exact (e.g. `1200×400`).

### Two upscale stages
- `upscale_1`, `upscale_2` — decimal multipliers. **`1.0` = off** (true passthrough, no snapping).
- Outputs the full chain: **base → mid (×up1) → final (×up2)** — matches a two-pass upscale pipeline, so you see the final size up front.

### Other inputs
- `multiple` — snap sides to **8 / 16 / 32 / 64** (16/32 safe for Krea 2 / Qwen). Ignored for the exact side in Manual mode.
- `batch_size` — for the `LATENT` output.
- `latent_type` — `SD3 / Flux / Krea 2 (16ch)` or `SD1.5 / SDXL (4ch)`.

### Outputs
`width`, `height`, `mid_width`, `mid_height`, `final_width`, `final_height` (`INT`), plus a ready
**`LATENT`** (empty, at base size — drop your `EmptyLatentImage`) and an **`info`** string
(`512x768 -> 960x1472 -> 1920x2944`, wire into a text node for a readout / filename).

The node also draws the `base → mid → final` chain live at the bottom.

## Install
**ComfyUI-Manager → Install via Git URL:**
`https://github.com/artfat-creator/ComfyUI-Artfat-Resolution`

Or clone into `ComfyUI/custom_nodes/` and restart ComfyUI:
```
cd <ComfyUI>/custom_nodes
git clone https://github.com/artfat-creator/ComfyUI-Artfat-Resolution.git
```

No extra Python dependencies (uses `torch`, already provided by ComfyUI).

## License
MIT © artfat-creator
