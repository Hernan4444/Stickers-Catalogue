import os
import csv

# Ruta a la carpeta con las fotos
carpeta_fotos = "procesadas_jpg"

# Ruta al archivo CSV
ruta_csv = "data.csv"

# Leer nombres de archivo desde la carpeta (sin path)
archivos_carpeta = set(os.listdir(carpeta_fotos))

# Leer nombres desde el CSV (solo la primera columna)
archivos_carpeta = set(os.listdir(carpeta_fotos))

# Leer nombres desde el CSV (solo la primera columna)
with open(ruta_csv, newline='', encoding='utf-8') as f:
    lector = csv.reader(f)
    nombres_csv = set(row[0] for row in lector if row)

# Archivos en la carpeta que no están en el CSV
no_en_csv = archivos_carpeta - nombres_csv

# Mostrar resultados
for archivo in sorted(no_en_csv):
    print(archivo)
