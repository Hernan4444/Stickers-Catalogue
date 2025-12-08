import os
from PIL import Image

input_folder = "procesadas"
output_folder = "procesadas_jpg"
os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.lower().endswith(".jpg") or filename.lower().endswith(".png"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename.replace(".png", ".jpg"))

        # if os.path.exists(output_path):
        #     print(f"El archivo {output_path} ya existe. Saltando...")
        #     continue

        # Convertir imagen PNG a JPG y guardar en output_path
        with Image.open(input_path) as img:
            img.thumbnail((240, 240))
            # Fondo negro
            background = Image.new("RGB", img.size, (18, 18, 18))
            background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            img = background
            img.save(output_path, "JPEG", quality=65)
