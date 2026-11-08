import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image, PngImagePlugin


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "imagenes_png"
PROCESSED_DIR = ROOT / "procesadas"
CSV_PATH = ROOT / "data.csv"
MAX_REQUEST_SIZE = 1024 * 1024
MAX_JOB_OUTPUT = 200_000
SCRIPTS = {
    "upload": "1.subir.py",
    "compress": "2.comprimir.py",
}


def natural_key(value):
    return [(0, int(part)) if part.isdigit() else (1, part.casefold())
            for part in re.split(r"(\d+)", value)]


class CatalogManager:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.source_dir = self.root / "imagenes_png"
        self.processed_dir = self.root / "procesadas"
        self.jpg_dir = self.root / "procesadas_jpg"
        self.csv_path = self.root / "data.csv"

    def read_rows(self):
        with self.csv_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames != ["nombre", "tags"]:
                raise ValueError("data.csv debe tener las columnas nombre,tags.")
            return list(reader)

    def state(self):
        pending = sorted(
            (path.name for path in self.source_dir.iterdir()
             if path.is_file() and path.suffix.lower() == ".png"),
            key=natural_key,
        )
        rows = self.read_rows()
        all_tags = set()
        illustrators = set()
        rows_by_name = self.rows_by_name(rows)
        for row in rows:
            for tag in row["tags"].split(";"):
                tag = tag.strip()
                if not tag:
                    continue
                if tag.casefold().startswith("ilustrador_"):
                    illustrators.add(tag)
                else:
                    all_tags.add(tag)
        processed = self.image_entries(self.processed_dir, ".png", rows_by_name)
        jpgs = self.image_entries(self.jpg_dir, ".jpg", rows_by_name)
        return {
            "pending": pending,
            "pendingCount": len(pending),
            "processed": processed,
            "processedCount": len(processed),
            "jpgs": jpgs,
            "jpgCount": len(jpgs),
            "illustrators": sorted(illustrators, key=natural_key),
            "tags": sorted(all_tags, key=natural_key),
        }

    @staticmethod
    def rows_by_name(rows):
        result = {}
        for row in rows:
            key = row["nombre"].casefold()
            if key in result:
                raise ValueError("data.csv contiene nombres duplicados.")
            result[key] = row
        return result

    def image_entries(self, directory, extension, rows_by_name):
        if not directory.exists():
            return []
        entries = []
        for path in sorted(
            (item for item in directory.iterdir()
             if item.is_file() and item.suffix.lower() == extension),
            key=lambda item: natural_key(item.name),
        ):
            csv_name = path.stem + ".jpg"
            row = rows_by_name.get(csv_name.casefold(), {})
            tags = [tag.strip() for tag in row.get("tags", "").split(";") if tag.strip()]
            illustrator = next(
                (tag[len("ilustrador_"):] for tag in tags
                 if tag.casefold().startswith("ilustrador_")),
                "",
            )
            other_tags = [
                tag for tag in tags
                if not tag.casefold().startswith("ilustrador_")
            ]
            entries.append({
                "filename": path.name,
                "illustrator": illustrator,
                "tags": other_tags,
            })
        return entries

    def image_path(self, mode, filename):
        if not filename or Path(filename).name != filename:
            raise ValueError("Nombre de imagen no válido.")
        directories = {
            "pending": (self.source_dir, ".png"),
            "processed": (self.processed_dir, ".png"),
            "jpg": (self.jpg_dir, ".jpg"),
        }
        if mode not in directories:
            raise ValueError("Carpeta de imágenes no reconocida.")
        directory, extension = directories[mode]
        if Path(filename).suffix.lower() != extension:
            raise ValueError("La extensión de la imagen no coincide con la carpeta.")
        image_path = directory / filename
        if not image_path.is_file():
            raise FileNotFoundError("La imagen seleccionada ya no existe.")
        return image_path

    def validate_stem(self, name):
        if not isinstance(name, str):
            raise ValueError("Escribe un nombre para la imagen.")
        stem = name.strip()
        if stem.lower().endswith((".png", ".jpg", ".jpeg")):
            stem = Path(stem).stem
        if (not stem or len(stem) > 150 or stem in {".", ".."}
                or stem.endswith((".", " "))
                or re.search(r'[<>:"/\\|?*,;\x00-\x1f]', stem)):
            raise ValueError(
                "El nombre no puede estar vacío ni contener caracteres "
                "inválidos, comas o punto y coma."
            )
        if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", stem, re.I):
            raise ValueError("Ese nombre está reservado por Windows.")
        return stem

    def normalize_tags(self, illustrator, tags, require_other_tag):
        if not isinstance(illustrator, str):
            raise ValueError("Indica el ilustrador.")
        illustrator = illustrator.strip()
        if illustrator.casefold().startswith("ilustrador_"):
            illustrator = illustrator[len("ilustrador_"):]
        if not illustrator or re.search(r"[;,\r\n]", illustrator):
            raise ValueError("Indica un único ilustrador sin comas ni punto y coma.")
        normalized_illustrator = "ilustrador_" + illustrator

        if not isinstance(tags, list):
            raise ValueError("La lista de tags no es válida.")
        normalized_tags = [normalized_illustrator]
        seen_tags = {normalized_illustrator.casefold()}
        for tag in tags:
            if not isinstance(tag, str):
                raise ValueError("Cada tag debe ser texto.")
            tag = tag.strip()
            if not tag:
                continue
            if re.search(r"[;,\r\n]", tag):
                raise ValueError("Los tags no pueden contener comas ni punto y coma.")
            if tag.casefold().startswith("ilustrador_"):
                continue
            if tag.casefold() not in seen_tags:
                seen_tags.add(tag.casefold())
                normalized_tags.append(tag)
        if require_other_tag and len(normalized_tags) == 1:
            raise ValueError("Agrega al menos un tag además del ilustrador.")
        return normalized_tags

    def allocate_stem(self, requested_stem, rows):
        occupied = set()
        for directory in (self.processed_dir, self.jpg_dir):
            if directory.exists():
                occupied.update(
                    path.stem.casefold() for path in directory.iterdir()
                    if path.is_file()
                    and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
                )
        occupied.update(
            Path(row["nombre"]).stem.casefold()
            for row in rows
        )

        family_pattern = re.compile(
            r"^" + re.escape(requested_stem.casefold()) + r"_(\d+)$"
        )
        family_suffixes = [
            int(match.group(1))
            for name in occupied
            if (match := family_pattern.match(name))
        ]
        if requested_stem.casefold() not in occupied and not family_suffixes:
            return requested_stem
        largest_suffix = max(
            family_suffixes,
            default=0,
        )
        candidate_number = largest_suffix + 1
        candidate = f"{requested_stem}_{candidate_number}"
        while candidate.casefold() in occupied:
            candidate_number += 1
            candidate = f"{requested_stem}_{candidate_number}"
        return candidate

    def rotated_copy(self, source, degrees):
        image_temp = tempfile.NamedTemporaryFile(
            delete=False, dir=str(source.parent), prefix=".gestor-",
            suffix=source.suffix,
        )
        temp_path = Path(image_temp.name)
        image_temp.close()
        try:
            with Image.open(source) as image:
                image.load()
                rotated = image.rotate(-degrees, expand=True)
                save_kwargs = {}
                if "icc_profile" in image.info:
                    save_kwargs["icc_profile"] = image.info["icc_profile"]
                if "dpi" in image.info:
                    save_kwargs["dpi"] = image.info["dpi"]
                if image.format == "JPEG":
                    if rotated.mode not in {"L", "RGB", "CMYK"}:
                        rotated = rotated.convert("RGB")
                    save_kwargs.update(quality=95, optimize=True)
                elif image.format == "PNG":
                    pnginfo = PngImagePlugin.PngInfo()
                    for key, value in image.info.items():
                        if isinstance(value, str) and key not in {
                            "interlace", "gamma", "dpi", "icc_profile",
                        }:
                            pnginfo.add_text(key, value)
                    if pnginfo:
                        save_kwargs["pnginfo"] = pnginfo
                else:
                    raise ValueError("Solo se pueden rotar imágenes PNG y JPG.")
                rotated.save(temp_path, format=image.format, **save_kwargs)
            return temp_path
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def move_files_and_update_catalog(self, moves, rows, rotation=0):
        temp_path = None
        staged = []
        completed = []
        rotated_files = {}
        committed = False
        cleanup_warnings = []
        try:
            if rotation:
                for source, _destination in moves:
                    rotated_files[source] = self.rotated_copy(source, rotation)

            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", delete=False,
                dir=str(self.root), prefix=".data-", suffix=".tmp",
            ) as temp_file:
                temp_path = Path(temp_file.name)
                writer = csv.writer(temp_file)
                writer.writerow(["nombre", "tags"])
                for row in rows:
                    writer.writerow([row["nombre"], row["tags"]])

            for source, destination in moves:
                if (source.name == destination.name
                        and source not in rotated_files):
                    continue
                backup = source.with_name(".gestor-backup-" + uuid.uuid4().hex)
                source.rename(backup)
                staged.append((backup, source, destination))

            for backup, source, destination in staged:
                payload = rotated_files.get(source, backup)
                payload.rename(destination)
                completed.append((destination, source, backup if payload != backup else None))

            os.replace(str(temp_path), str(self.csv_path))
            temp_path = None
            committed = True
            for _destination, _source, backup in completed:
                if backup is not None:
                    try:
                        backup.unlink()
                    except OSError as error:
                        cleanup_warnings.append(
                            f"No se pudo borrar el respaldo temporal {backup.name}: {error}"
                        )
        except Exception:
            if not committed:
                for destination, source, backup in reversed(completed):
                    if destination.exists():
                        if backup is not None and backup.exists():
                            destination.unlink()
                        else:
                            destination.rename(source)
                for backup, source, _destination in reversed(staged):
                    if backup.exists():
                        backup.rename(source)
            raise
        finally:
            for rotated in rotated_files.values():
                if rotated.exists():
                    rotated.unlink()
            if temp_path and temp_path.exists():
                temp_path.unlink()
        return cleanup_warnings

    def update_image(self, mode, source_name, name, illustrator, tags, rotation=0):
        if mode not in {"pending", "processed", "jpg"}:
            raise ValueError("Carpeta de imágenes no reconocida.")
        if (not isinstance(rotation, int) or isinstance(rotation, bool)
                or rotation not in {0, 90, 180, 270}):
            raise ValueError("La rotación debe ser 0, 90, 180 o 270 grados.")
        source_path = self.image_path(mode, source_name)
        requested_stem = self.validate_stem(name)
        normalized_tags = self.normalize_tags(
            illustrator, tags, require_other_tag=(mode == "pending")
        )
        rows = self.read_rows()
        rows_by_name = self.rows_by_name(rows)
        old_csv_name = source_path.stem + ".jpg"
        old_row = None if mode == "pending" else rows_by_name.get(old_csv_name.casefold())
        if mode != "pending" and old_row is None:
            raise ValueError("No hay un registro correspondiente en data.csv.")

        paired_png = None
        paired_jpg = None
        if mode == "processed":
            paired_png = source_path
            candidate = self.jpg_dir / (source_path.stem + ".jpg")
            if candidate.exists():
                paired_jpg = candidate
        elif mode == "jpg":
            paired_jpg = source_path
            candidate = self.processed_dir / (source_path.stem + ".png")
            if candidate.exists():
                paired_png = candidate

        if mode != "pending" and requested_stem.casefold() == source_path.stem.casefold():
            final_stem = requested_stem
        else:
            final_stem = self.allocate_stem(requested_stem, rows)
        csv_name = final_stem + ".jpg"
        new_row = {"nombre": csv_name, "tags": ";".join(normalized_tags)}
        if old_row is not None:
            old_row["nombre"] = csv_name
            old_row["tags"] = new_row["tags"]
        else:
            rows.append(new_row)

        moves = []
        if mode == "pending":
            moves.append((source_path, self.processed_dir / (final_stem + ".png")))
        else:
            if paired_png is not None:
                moves.append((paired_png, self.processed_dir / (final_stem + ".png")))
            if paired_jpg is not None:
                moves.append((paired_jpg, self.jpg_dir / (final_stem + ".jpg")))

        for source, destination in moves:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if (destination.exists()
                    and destination.name.casefold() != source.name.casefold()):
                raise FileExistsError("Ya existe el archivo destino.")

        warnings = self.move_files_and_update_catalog(moves, rows, rotation)
        return {
            "name": csv_name,
            "tags": normalized_tags,
            "remaining": len(self.state()["pending"]),
            "warnings": warnings,
        }


manager = CatalogManager()
jobs = {}
jobs_lock = threading.Lock()


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format_string, *args):
        print("%s - %s" % (self.address_string(), format_string % args))

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Longitud de solicitud no válida.")
        if length <= 0 or length > MAX_REQUEST_SIZE:
            raise ValueError("El contenido de la solicitud está vacío o es demasiado grande.")
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("La solicitud no contiene JSON válido.")
        if not isinstance(data, dict):
            raise ValueError("La solicitud debe ser un objeto JSON.")
        return data

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self.send_static("gestor.html", "text/html; charset=utf-8")
        if parsed.path == "/gestor.css":
            return self.send_static("gestor.css", "text/css; charset=utf-8")
        if parsed.path == "/gestor.js":
            return self.send_static("gestor.js", "text/javascript; charset=utf-8")
        if parsed.path == "/api/state":
            try:
                return self.send_json(200, manager.state())
            except (OSError, ValueError) as error:
                return self.send_json(500, {"error": str(error)})
        if parsed.path == "/api/image":
            try:
                query = parse_qs(parsed.query)
                image_path = manager.image_path(
                    query.get("mode", [""])[0],
                    query.get("name", [""])[0],
                )
                body = image_path.read_bytes()
                self.send_response(200)
                content_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            except (OSError, ValueError) as error:
                self.send_json(404, {"error": str(error)})
            return
        if parsed.path.startswith("/api/jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            with jobs_lock:
                job = jobs.get(job_id)
            if job is None:
                return self.send_json(404, {"error": "No se encontró esa tarea."})
            return self.send_json(200, job.copy())
        self.send_json(404, {"error": "Ruta no encontrada."})

    def send_static(self, filename, content_type):
        body = (ROOT / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self.read_json()
            if parsed.path == "/api/update":
                result = manager.update_image(
                    data.get("mode"),
                    data.get("source"),
                    data.get("name"),
                    data.get("illustrator"),
                    data.get("tags"),
                    data.get("rotation", 0),
                )
                return self.send_json(200, result)
            if parsed.path == "/api/run":
                action = data.get("action")
                if not isinstance(action, str) or action not in SCRIPTS:
                    return self.send_json(400, {"error": "Acción no reconocida."})
                return self.start_job(action)
            self.send_json(404, {"error": "Ruta no encontrada."})
        except (ValueError, FileNotFoundError, FileExistsError) as error:
            self.send_json(400, {"error": str(error)})
        except Exception as error:
            self.log_error("Error procesando solicitud", error)
            self.send_json(500, {"error": str(error)})

    def start_job(self, action):
        with jobs_lock:
            if any(job["status"] == "running" for job in jobs.values()):
                return self.send_json(
                    409, {"error": "Ya hay una tarea de subida o compresión en curso."}
                )
            job_id = uuid.uuid4().hex
            jobs[job_id] = {
                "id": job_id,
                "action": action,
                "script": SCRIPTS[action],
                "status": "running",
                "output": "",
                "exitCode": None,
            }
        threading.Thread(
            target=self.run_script, args=(job_id,), daemon=True
        ).start()
        self.send_json(202, jobs[job_id].copy())

    def run_script(self, job_id):
        with jobs_lock:
            script = jobs[job_id]["script"]
        script_path = ROOT / script
        try:
            if not script_path.is_file():
                raise FileNotFoundError("No se encontró el script " + script)
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3600,
                check=False,
            )
            output = result.stdout[-MAX_JOB_OUTPUT:]
            status = "completed" if result.returncode == 0 else "failed"
            exit_code = result.returncode
        except (OSError, subprocess.TimeoutExpired) as error:
            output = str(error)
            status = "failed"
            exit_code = -1
        except Exception as error:
            self.log_error("Error ejecutando " + script, error)
            output = str(error)
            status = "failed"
            exit_code = -1
        with jobs_lock:
            jobs[job_id].update({
                "status": status,
                "output": output,
                "exitCode": exit_code,
            })

    def log_error(self, message, error):
        print("%s: %s" % (message, error), file=sys.stderr)


def main():
    address = ("127.0.0.1", 8765)
    server = ThreadingHTTPServer(address, RequestHandler)
    url = "http://127.0.0.1:8765/"
    print("Gestor de imágenes disponible en " + url)
    print("Presiona Ctrl+C para cerrar.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando gestor...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
