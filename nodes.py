"""Artfat Resolution v3 — resolution picker + upscale stages + optional image/mask resizer.

Four ways to set the size, one node:
  • Preset size   — pick a ready W×H from the dropdown (beginner-friendly)
  • Custom ratio  — set ratio_w:ratio_h + base short-side (e.g. 3:1 banners)
  • Megapixels    — pick a target area (MP) + an aspect; W×H hit that pixel budget
                    (nearest-`multiple` snap, e.g. 0.98 MP @ 9:16 -> 736×1312)
  • Manual W×H    — type an exact width/height (no snapping — exact, e.g. 1200×400)

Two upscale stages (1.0 = off) so the outputs match a base → 1st upscale → 2nd upscale
pipeline (image OR video upscalers downstream), and you always see the final size before
rendering. Optionally resizes a connected image/mask to the BASE W×H (scale_method + crop).
Outputs the base / mid / final integer sizes, the resized image / mask (passthrough None when
nothing is connected), an empty LATENT and an info string — use whichever you need.
"""

import math

import torch

import comfy.utils


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
    MEGAPIXELS = "Megapixels · aspect"
    MANUAL = "Manual W×H"

    # Named aspects for Megapixels mode. None => use ratio_w:ratio_h.
    ASPECTS = {
        "9:16 portrait":   (9, 16),
        "2:3 portrait":    (2, 3),
        "3:4 portrait":    (3, 4),
        "4:5 portrait":    (4, 5),
        "1:1 square":      (1, 1),
        "5:4 landscape":   (5, 4),
        "4:3 landscape":   (4, 3),
        "3:2 landscape":   (3, 2),
        "16:9 landscape":  (16, 9),
        "21:9 ultrawide":  (21, 9),
        "custom (ratio_w:ratio_h)": None,
    }

    SCALE_METHODS = ["lanczos", "nearest-exact", "bilinear", "area", "bicubic"]

    LATENT_SD3 = "SD3 / Flux / Krea 2 (16ch)"
    LATENT_SD = "SD1.5 / SDXL (4ch)"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "size": (list(cls.SIZES.keys()) + [cls.CUSTOM_RATIO, cls.MEGAPIXELS, cls.MANUAL], {
                    "default": "2:3 portrait · 512×768",
                    "tooltip": "Ready size, 'Custom ratio' (ratio_w/h + base), 'Megapixels · aspect' (MP + aspect), or 'Manual W×H' (exact).",
                }),
                "base": ("INT", {
                    "default": 512, "min": 128, "max": 8192, "step": 32,
                    "tooltip": "Short side of the BASE gen. Used ONLY in 'Custom ratio' mode.",
                }),
                "ratio_w": ("INT", {
                    "default": 2, "min": 1, "max": 100,
                    "tooltip": "Aspect width — 'Custom ratio' mode, or 'Megapixels' with aspect = custom.",
                }),
                "ratio_h": ("INT", {
                    "default": 3, "min": 1, "max": 100,
                    "tooltip": "Aspect height — 'Custom ratio' mode, or 'Megapixels' with aspect = custom.",
                }),
                "megapixels": ("FLOAT", {
                    "default": 1.0, "min": 0.05, "max": 16.0, "step": 0.01,
                    "tooltip": "Target area in megapixels — 'Megapixels · aspect' mode only. W×H hit this pixel budget at the chosen aspect, snapped to 'multiple'.",
                }),
                "mp_aspect": (list(cls.ASPECTS.keys()), {
                    "default": "9:16 portrait",
                    "tooltip": "Aspect for 'Megapixels' mode. 'custom' uses ratio_w:ratio_h.",
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
                    "tooltip": "Snap base+upscaled sides to a multiple. 16/32 safe for Krea 2 / Qwen / H3. "
                               "Ignored for the exact side in Manual mode.",
                }),
                "upscale_1": ("FLOAT", {
                    "default": 1.0, "min": 1.0, "max": 8.0, "step": 0.01,
                    "tooltip": "1st upscale stage (for a downstream image/video upscaler). 1.0 = off (passthrough, exact).",
                }),
                "upscale_2": ("FLOAT", {
                    "default": 1.0, "min": 1.0, "max": 8.0, "step": 0.01,
                    "tooltip": "2nd upscale stage (applied on top of stage 1). 1.0 = off.",
                }),
                "scale_method": (cls.SCALE_METHODS, {
                    "default": "lanczos",
                    "tooltip": "Resampling used ONLY when an image/mask is connected and resized to the BASE W×H.",
                }),
                "crop": (["center", "disabled"], {
                    "default": "center",
                    "tooltip": "Image resize aspect handling. 'center' = cover-crop keeping aspect; 'disabled' = stretch to exact W×H.",
                }),
                "batch_size": ("INT", {
                    "default": 1, "min": 1, "max": 64,
                    "tooltip": "Batch size for the empty LATENT output.",
                }),
                "latent_type": ([cls.LATENT_SD3, cls.LATENT_SD], {
                    "default": cls.LATENT_SD3,
                    "tooltip": "Channels for the empty LATENT. Krea 2 / Flux / SD3 = 16ch; classic SD = 4ch.",
                }),
            },
            "optional": {
                "image": ("IMAGE", {"tooltip": "Optional image to resize to the computed BASE W×H."}),
                "mask": ("MASK", {"tooltip": "Optional mask to resize to the computed BASE W×H."}),
            },
        }

    # mid/final sizes are still COMPUTED (upscale stages) and shown in `info`, but not exposed as
    # separate output sockets (kept off the node edges to declutter).
    RETURN_TYPES = ("INT", "INT", "IMAGE", "MASK", "LATENT", "STRING")
    RETURN_NAMES = ("width", "height", "image", "mask", "latent", "info")
    FUNCTION = "get"
    CATEGORY = "artfat"

    @staticmethod
    def _snap(x, m):
        m = int(m)
        return max(m, int(round(x / float(m))) * m)

    def _stage(self, dim, up, m):
        # 1.0 = true passthrough (no scaling, no snapping — keeps exact sizes exact)
        return dim if abs(up - 1.0) < 1e-6 else self._snap(dim * up, m)

    def _resize_image(self, image, width, height, method, crop):
        # IMAGE is [B, H, W, C] -> resize -> [B, height, width, C]
        s = image[..., :3].movedim(-1, 1)
        s = comfy.utils.common_upscale(s, width, height, method, crop)
        return s.movedim(1, -1)

    def _resize_mask(self, mask, width, height, method, crop):
        # MASK is [B, H, W] -> [B, 1, H, W] -> resize -> [B, height, width]
        m = mask.unsqueeze(1)
        m = comfy.utils.common_upscale(m, width, height, method, crop)
        return m.squeeze(1)

    def get(self, size, base, ratio_w, ratio_h, megapixels, mp_aspect,
            manual_w, manual_h, multiple, upscale_1, upscale_2,
            scale_method, crop, batch_size, latent_type, image=None, mask=None):
        m = int(multiple)

        if size == self.MANUAL:
            width, height = int(manual_w), int(manual_h)          # exact, no snap
        elif size == self.CUSTOM_RATIO:
            rw, rh = max(1, ratio_w), max(1, ratio_h)
            short = self._snap(base, m)
            long = self._snap(base * max(rw, rh) / float(min(rw, rh)), m)
            width, height = (short, long) if rw <= rh else (long, short)
        elif size == self.MEGAPIXELS:
            ar = self.ASPECTS.get(mp_aspect)
            aw, ah = ar if ar else (max(1, ratio_w), max(1, ratio_h))
            total = max(0.01, float(megapixels)) * 1_000_000.0
            width = self._snap(math.sqrt(total * aw / ah), m)     # round-to-multiple (matches the reference)
            height = self._snap(math.sqrt(total * ah / aw), m)
        else:
            width, height = self.SIZES[size]

        mid_w = self._stage(width, upscale_1, m)
        mid_h = self._stage(height, upscale_1, m)
        final_w = self._stage(mid_w, upscale_2, m)
        final_h = self._stage(mid_h, upscale_2, m)

        out_image = self._resize_image(image, width, height, scale_method, crop) if image is not None else None
        out_mask = self._resize_mask(mask, width, height, scale_method, crop) if mask is not None else None

        channels = 16 if latent_type == self.LATENT_SD3 else 4
        latent = {"samples": torch.zeros([int(batch_size), channels, height // 8, width // 8])}

        parts = ["%dx%d" % (width, height)]
        if (mid_w, mid_h) != (width, height):
            parts.append("%dx%d" % (mid_w, mid_h))
        if (final_w, final_h) != (mid_w, mid_h):
            parts.append("%dx%d" % (final_w, final_h))
        info = " -> ".join(parts) + " · %.2f MP" % ((width * height) / 1_000_000.0)

        return (width, height, out_image, out_mask, latent, info)


NODE_CLASS_MAPPINGS = {"ArtfatResolution": ArtfatResolution}
NODE_DISPLAY_NAME_MAPPINGS = {"ArtfatResolution": "Artfat Resolution"}
