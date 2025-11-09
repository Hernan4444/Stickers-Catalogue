# batch_crop_transparent_pngs.py
# Recorre "to_crop" y guarda salidas en "to_crop_cropped", recortando bordes 100% transparentes.

from pathlib import Path
from PIL import Image, PngImagePlugin


def crop_transparent_borders(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    alpha = img.split()[3]
    bbox = alpha.getbbox()
    if not bbox:
        return img  # totalmente transparente o sin contenido no-transparente
    return img.crop(bbox)


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
