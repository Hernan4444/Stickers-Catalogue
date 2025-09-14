import csv
import natsort

# Ruta al archivo CSV
ruta_csv = "data.csv"

# ordenar archivos CSV por la primera columna alfabéticamente
# La primera fila es el header
with open(ruta_csv, newline='', encoding='utf-8') as f:
    lector = csv.reader(f)
    header = next(lector, None)  # Leer el header
    filas = natsort.natsorted(lector, key=lambda row: row[0] if row else "")

# Guardar el archivo CSV ordenado
with open(ruta_csv, 'w', newline='', encoding='utf-8') as f:
    escritor = csv.writer(f)
    escritor.writerow(header)  # Escribir el header
    escritor.writerows(filas)
