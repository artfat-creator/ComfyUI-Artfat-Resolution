"""Artfat Resolution v2 — aspect-ratio / manual resolution picker for low-base + upscale workflows.

Three ways to set the size, one node:
  • Preset size  — pick a ready W×H from the dropdown (beginner-friendly)
  • Custom ratio — set ratio_w:ratio_h + base short-side (e.g. 3:1 banners)
  • Manual W×H   — type an exact width/height (no snapping — exact, e.g. 1200×400)

Two upscale stages (1.0 = off) so the outputs match a base → 1st upscale → 2nd upscale
pipeline, and you always see the final file size before rendering. Outputs the base /
mid / final integer sizes, PLUS an empty LATENT and an info string — use whichever you need.
"""

import torch


class ArtfatResolution:
    # Ready sizes (short side from the Selfism resolution table). Label carries the size.
    SIZES = {
        "9:16 tall · 480×832":       (480, 832),
        "2:3 portrait · 512×768":    (512, 768),
        "3:4 portrait · 544×736":    (544, 736),
        "4:5 portrait · 544×680":    (544, 680),
        "1:1 square · 640×640":      (640, 640),
        "4:3 landscape · 736×544":   (736, 544),
        "3:2 landscape · 768×512":   (768, 512),
        "16:9 wide · 832×480":       (832, 480),
    }
    CUSTOM_RATIO = "Custom ratio"
    MANUAL = "Manual W×H"

    LATENT_SD3 = "SD3 / Flux / Krea 2 (16ch)"
    LATENT_SD = "SD1.5 / SDXL (4ch)"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "size": (list(cls.SIZES.keys()) + [cls.CUSTOM_RATIO, cls.MANUAL], {
                    "default": "2:3 portrait · 512×768",
                    "tooltip": "Ready size, or 'Custom ratio' (uses ratio_w/h + base), or 'Manual W×H' (exact).",
                }),
                "base": ("INT", {
                    "default": 512, "min": 128, "max": 8192, "step": 32,
                    "tooltip": "Short side of the BASE gen. Used ONLY in 'Custom ratio' mode.",
                }),
                "ratio_w": ("INT", {
                    "default": 2, "min": 1, "max": 100,
                    "tooltip": "Aspect width — 'Custom ratio' mode only (e.g. 3 for a 3:1 banner).",
                }),
                "ratio_h": ("INT", {
                    "default": 3, "min": 1, "max": 100,
                    "tooltip": "Aspect height — 'Custom ratio' mode only (e.g. 1 for a 3:1 banner).",
                }),
                "manual_w": ("INT", {
                    "default": 1200, "min": 64, "max": 16384, "step": 1,
                    "tooltip": "Exact width — 'Manual W×H' mode only. NOT snapped (kept exact).",
                }),
                "manual_h": ("INT", {
                    "default": 400, "min": 64, "max": 16384, "step": 1,
                    "tooltip": "Exact height — 'Manual W×H' mode only. NOT snapped (kept exact).",
                }),
                "multiple": (["8", "16", "32", "64"], {
                    "default": "32",
                    "tooltip": "Snap base+upscaled sides to a multiple. 16/32 safe for Krea 2 / Qwen. "
                               "Ignored for the exact side in Manual mode.",
                }),
                "upscale_1": ("FLOAT", {
                    "default": 1.0, "min": 1.0, "max": 8.0, "step": 0.01,
                    "tooltip": "1st upscale stage. 1.0 = off (passthrough, exact).",
                }),
                "upscale_2": ("FLOAT", {
                    "default": 1.0, "min": 1.0, "max": 8.0, "step": 0.01,
                    "tooltip": "2nd upscale stage (applied on top of stage 1). 1.0 = off.",
                }),
                "batch_size": ("INT", {
                    "default": 1, "min": 1, "max": 64,
                    "tooltip": "Batch size for the LATENT output.",
                }),
                "latent_type": ([cls.LATENT_SD3, cls.LATENT_SD], {
                    "default": cls.LATENT_SD3,
                    "tooltip": "Channels for the empty LATENT. Krea 2 / Flux / SD3 = 16ch; classic SD = 4ch.",
                }),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT", "INT", "INT", "INT", "LATENT", "STRING")
    RETURN_NAMES = ("width", "height", "mid_width", "mid_height",
                    "final_width", "final_height", "latent", "info")
    FUNCTION = "get"
    CATEGORY = "artfat"

    @staticmethod
    def _snap(x, m):
        m = int(m)
        return max(m, int(round(x / float(m))) * m)

    def _stage(self, dim, up, m):
        # 1.0 = true passthrough (no scaling, no snapping — keeps exact sizes exact)
        return dim if abs(up - 1.0) < 1e-6 else self._snap(dim * up, m)

    def get(self, size, base, ratio_w, ratio_h, manual_w, manual_h,
            multiple, upscale_1, upscale_2, batch_size, latent_type):
        m = int(multiple)

        if size == self.MANUAL:
            width, height = int(manual_w), int(manual_h)          # exact, no snap
        elif size == self.CUSTOM_RATIO:
            rw, rh = max(1, ratio_w), max(1, ratio_h)
            short = self._snap(base, m)
            long = self._snap(base * max(rw, rh) / float(min(rw, rh)), m)
            width, height = (short, long) if rw <= rh else (long, short)
        else:
            width, height = self.SIZES[size]

        mid_w = self._stage(width, upscale_1, m)
        mid_h = self._stage(height, upscale_1, m)
        final_w = self._stage(mid_w, upscale_2, m)
        final_h = self._stage(mid_h, upscale_2, m)

        channels = 16 if latent_type == self.LATENT_SD3 else 4
        latent = {"samples": torch.zeros([int(batch_size), channels, height // 8, width // 8])}

        parts = [f"{width}x{height}"]
        if (mid_w, mid_h) != (width, height):
            parts.append(f"{mid_w}x{mid_h}")
        if (final_w, final_h) != (mid_w, mid_h):
            parts.append(f"{final_w}x{final_h}")
        info = " -> ".join(parts)

        return (width, height, mid_w, mid_h, final_w, final_h, latent, info)


NODE_CLASS_MAPPINGS = {"ArtfatResolution": ArtfatResolution}
NODE_DISPLAY_NAME_MAPPINGS = {"ArtfatResolution": "Artfat Resolution"}
