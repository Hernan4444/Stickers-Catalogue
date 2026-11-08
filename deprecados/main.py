import os
import io
from PIL import Image

input_folder = "imagenes_png"
output_folder = "procesadas_jpg"
os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.lower().endswith(".jpg") or filename.lower().endswith(".png"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename.replace(".png", ".jpg"))

        print(filename.replace(".png", ".jpg"))
        if os.path.exists(output_path):
            continue

        with Image.open(input_path) as img:
            # Convertir temporalmente a JPG en memoria para comprimir
            buffer = io.BytesIO()
            buffer.seek(0)
            img_jpg = Image.open(buffer)

            # Pegar sobre fondo #121212 y guardar como JPG
            final = Image.new("RGB", img_jpg.size, (18, 18, 18))  # Color #121212
            final.paste(img_jpg, mask=img_jpg.split()[-1] if img_jpg.mode == 'RGBA' else None)
            final.convert("RGB").save(buffer, format="JPEG", quality=65)
            # Reducir tamaño a 240x240
            final.thumbnail((240, 240))
            final.save(output_path, "JPEG", quality=85)
