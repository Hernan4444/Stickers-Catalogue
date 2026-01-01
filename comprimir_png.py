import os
from PIL import Image

input_folder = "imagenes_png"
output_folder = "comprimidas"
os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.lower().endswith(".jpg") or filename.lower().endswith(".png"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename.replace(".jpg", ".png"))

        if os.path.exists(output_path):
            print(f"El archivo {output_path} ya existe. Saltando...")
            # continue

        # Convertir imagen aPNG y guardar en output_path
        with Image.open(input_path) as img:
            img.thumbnail((960, 960))
            img.save(output_path, "PNG", quality=85)
