import os
import cloudinary
import cloudinary.uploader
import dotenv

dotenv.load_dotenv()
data = "data.csv"

info = {}
with open(data, "r", encoding="utf-8") as file:
    lines = file.readlines()
    for line in lines:
        nombre, tags = line.strip().split(",")
        tags = tags.split(";")
        info[nombre] = tags

# Configure Cloudinary (replace with your actual credentials)
cloudinary.config(
    cloud_name=os.getenv("cloud_name"),
    api_key=os.getenv("api_key"),
    api_secret=os.getenv("api_secret"),
)


# Desired folder in Cloudinary
target_folder = "Ilustraciones"


images = os.listdir("procesadas")
for image in images:
    if not image.endswith(".png"):
        continue

    name = image.replace(".png", ".jpg")
    if name not in info:
        print(f"El archivo {image} no está en data.csv. Saltando...")
        print("AAA")
        continue

    # Path to the image you want to upload
    image_path = f"procesadas/{image}"

    # Tags to assign to the image
    image_tags = info[name]

    try:
        response = cloudinary.uploader.upload(
            image_path,
            folder=target_folder,
            tags=image_tags,
            unique_filename=False,
            use_filename=True,
            filename_override=name,
        )
        print("Image uploaded successfully:")
        print(f"Public ID: {response['public_id']}")
        print(f"Secure URL: {response['secure_url']}")
        print(f"Tags: {response.get('tags')}")

    except Exception as e:
        print(f"Error uploading image: {e}")
