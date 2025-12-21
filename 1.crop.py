from pathlib import Path
from PIL import Image, PngImagePlugin
import numpy as np


def crop_transparent_borders(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    arr = np.array(img)
    alpha = arr[:, :, 3]

    ys, xs = np.where(alpha > 1)
    if len(xs) == 0 or len(ys) == 0:
        return img

    min_x, max_x = xs.min(), xs.max()
    min_y, max_y = ys.min(), ys.max()

    width = max_x - min_x
    height = max_y - min_y
    side = max(width, height)

    center_x = (min_x + max_x) // 2
    center_y = (min_y + max_y) // 2

    half = side // 2
    left = max(center_x - half, 0)
    top = max(center_y - half, 0)
    right = min(left + side, img.width)
    bottom = min(top + side, img.height)

    return img.crop((left, top, right, bottom))


def main():
    in_dir = Path("to_crop")
    out_dir = Path("procesadas")
    out_dir.mkdir(parents=True, exist_ok=True)

    png_paths = sorted(p for p in in_dir.glob("*.png") if p.is_file())

    for src in png_paths:
        with Image.open(src) as im:
            im.load()  # asegura acceso a info
            meta = PngImagePlugin.PngInfo()
            # Copia metadatos de texto si existen
            for k, v in im.info.items():
                if isinstance(v, str) and k not in {"interlace", "gamma", "dpi", "icc_profile"}:
                    meta.add_text(k, v)

            cropped = crop_transparent_borders(im)

            dst = out_dir / src.name
            save_kwargs = {"format": "PNG", "optimize": True, "compress_level": 9, "pnginfo": meta}
            # Preserva DPI si existe
            if "dpi" in im.info and isinstance(im.info["dpi"], tuple):
                save_kwargs["dpi"] = im.info["dpi"]
            # Preserva perfil ICC si existe
            if "icc_profile" in im.info:
                save_kwargs["icc_profile"] = im.info["icc_profile"]

            cropped.save(dst, **save_kwargs)


if __name__ == "__main__":
    main()
