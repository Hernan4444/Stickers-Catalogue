import os
import io
from rembg import remove
from PIL import Image

input_folder = "imagenes_png"
output_folder = "procesadas_jpg"
os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.lower().endswith(".jpg"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename.replace(".png", ".jpg"))

        if os.path.exists(output_path):
            continue

        with Image.open(input_path) as img:
            # Convertir temporalmente a JPG en memoria para comprimir
            buffer = io.BytesIO()
            img.convert("RGB").save(buffer, format="JPEG", quality=65)
            buffer.seek(0)
            img_jpg = Image.open(buffer)

            # Eliminar fondo
            img_no_bg = remove(img_jpg)

            # Recorte (crop) basado en alpha
            alpha = img_no_bg.split()[-1]
            bbox = alpha.getbbox()
            if bbox:
                img_no_bg = img_no_bg.crop(bbox)

            # Pegar sobre fondo #121212 y guardar como JPG
            final = Image.new("RGB", img_no_bg.size, (18, 18, 18))  # Color #121212
            final.paste(img_no_bg, mask=img_no_bg.split()[3])
            # Reducir tamaño a 240x240
            final.thumbnail((240, 240))
            final.save(output_path, "JPEG", quality=85)
