"""Artfat Resolution — a tiny aspect-ratio resolution picker.

Built for low-base + upscale workflows (Krea 2 / Selfism): pick a ratio, set the
short side of the BASE (small) generation, and get width/height snapped to a
multiple of 32, plus the FINAL upscaled size. No canvas, no dozen buttons — three
controls, four INT outputs.
"""


class ArtfatResolution:
    # portrait-first — the common selfie/insta ratios up top
    RATIOS = {
        "9:16 (tall portrait)": (9, 16),
        "2:3 (portrait)": (2, 3),
        "3:4 (portrait)": (3, 4),
        "1:1 (square)": (1, 1),
        "4:3 (landscape)": (4, 3),
        "3:2 (landscape)": (3, 2),
        "16:9 (wide)": (16, 9),
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aspect_ratio": (list(cls.RATIOS.keys()) + ["Custom"], {"default": "2:3 (portrait)"}),
                "base": ("INT", {
                    "default": 512, "min": 128, "max": 4096, "step": 32,
                    "tooltip": "Short side of the BASE (small) generation. The long side is derived "
                               "from the ratio and snapped to the chosen multiple.",
                }),
                "multiple": (["8", "16", "32", "64"], {
                    "default": "32",
                    "tooltip": "Snap both sides to a multiple of this. 8 = latent minimum; 16/32 = safe "
                               "for Krea 2 / Qwen; 64 = extra-safe for some upscalers.",
                }),
                "custom_ratio_w": ("INT", {
                    "default": 2, "min": 1, "max": 100,
                    "tooltip": "Custom aspect width — used ONLY when aspect_ratio = Custom (e.g. 4 for 4:5).",
                }),
                "custom_ratio_h": ("INT", {
                    "default": 3, "min": 1, "max": 100,
                    "tooltip": "Custom aspect height — used ONLY when aspect_ratio = Custom (e.g. 5 for 4:5).",
                }),
                "upscale": ("FLOAT", {
                    "default": 3.42, "min": 1.0, "max": 8.0, "step": 0.01,
                    "tooltip": "Multiplier for the FINAL (upscaled) width/height outputs. 3.42 = 1.9 x 1.8.",
                }),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT", "INT")
    RETURN_NAMES = ("width", "height", "final_width", "final_height")
    FUNCTION = "get"
    CATEGORY = "artfat"

    @staticmethod
    def _snap(x, m):
        m = int(m)
        return max(m, int(round(x / float(m))) * m)

    def get(self, aspect_ratio, base, multiple, custom_ratio_w, custom_ratio_h, upscale):
        m = int(multiple)
        if aspect_ratio == "Custom":
            rw, rh = max(1, custom_ratio_w), max(1, custom_ratio_h)
        else:
            rw, rh = self.RATIOS[aspect_ratio]
        short = self._snap(base, m)
        long = self._snap(base * max(rw, rh) / float(min(rw, rh)), m)
        # rw <= rh -> portrait/square: the short side is the width
        width, height = (short, long) if rw <= rh else (long, short)
        final_w = self._snap(width * upscale, m)
        final_h = self._snap(height * upscale, m)
        return (width, height, final_w, final_h)


NODE_CLASS_MAPPINGS = {"ArtfatResolution": ArtfatResolution}
NODE_DISPLAY_NAME_MAPPINGS = {"ArtfatResolution": "Artfat Resolution"}
