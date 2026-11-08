import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from gestor_imagenes import CatalogManager


class CatalogManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "imagenes_png").mkdir()
        (self.root / "procesadas").mkdir()
        (self.root / "procesadas_jpg").mkdir()
        with (self.root / "data.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["nombre", "tags"])
            writer.writerow(["existente.jpg", "ilustrador_demo;Tag"])
        self.manager = CatalogManager(self.root)
        (self.root / "imagenes_png" / "origen.png").write_bytes(b"png")

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_rows(self, rows):
        with (self.root / "data.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["nombre", "tags"])
            writer.writeheader()
            writer.writerows(rows)

    def write_image(self, path, size=(2, 3), color=(255, 0, 0)):
        Image.new("RGB", size, color).save(path)

    def test_saves_tags_moves_image_and_updates_csv(self):
        result = self.manager.update_image(
            "pending", "origen.png", "nuevo_nombre", "artista", ["Tag nuevo"]
        )

        self.assertEqual(result["name"], "nuevo_nombre.jpg")
        self.assertTrue((self.root / "procesadas" / "nuevo_nombre.png").is_file())
        self.assertFalse((self.root / "imagenes_png" / "origen.png").exists())
        rows = self.manager.read_rows()
        self.assertEqual(rows[-1], {
            "nombre": "nuevo_nombre.jpg",
            "tags": "ilustrador_artista;Tag nuevo",
        })

    def test_duplicate_name_gets_next_case_insensitive_suffix(self):
        (self.root / "procesadas" / "EXISTENTE_3.png").write_bytes(b"png")
        (self.root / "procesadas_jpg" / "existente_9.jpg").write_bytes(b"jpg")
        result = self.manager.update_image(
            "pending", "origen.png", "eXiStEnTe", "artista", ["Tag nuevo"]
        )

        self.assertEqual(result["name"], "eXiStEnTe_10.jpg")
        self.assertTrue((self.root / "procesadas" / "eXiStEnTe_10.png").is_file())
        self.assertEqual(self.manager.read_rows()[-1]["nombre"], "eXiStEnTe_10.jpg")

    def test_name_uses_next_suffix_when_only_numbered_variants_exist(self):
        (self.root / "procesadas_jpg" / "Sakura_4.jpg").write_bytes(b"jpg")
        (self.root / "procesadas_jpg" / "SAKURA_9.jpg").write_bytes(b"jpg")

        result = self.manager.update_image(
            "pending", "origen.png", "sakura", "artista", ["Tag nuevo"]
        )

        self.assertEqual(result["name"], "sakura_10.jpg")
        self.assertTrue((self.root / "procesadas" / "sakura_10.png").is_file())

    def test_pending_image_with_existing_source_name_keeps_old_catalog_row(self):
        (self.root / "imagenes_png" / "existente.png").write_bytes(b"new png")

        result = self.manager.update_image(
            "pending", "existente.png", "existente", "artista", ["Tag nuevo"]
        )

        self.assertEqual(result["name"], "existente_1.jpg")
        rows = self.manager.read_rows()
        self.assertEqual(rows[0], {
            "nombre": "existente.jpg",
            "tags": "ilustrador_demo;Tag",
        })
        self.assertEqual(rows[1]["nombre"], "existente_1.jpg")

    def test_updates_processed_png_jpg_and_catalog_row(self):
        (self.root / "procesadas" / "antiguo.png").write_bytes(b"png")
        (self.root / "procesadas_jpg" / "antiguo.jpg").write_bytes(b"jpg")
        rows = self.manager.read_rows()
        rows.append({"nombre": "antiguo.jpg", "tags": "ilustrador_viejo;Tag viejo"})
        self.write_rows(rows)

        result = self.manager.update_image(
            "processed", "antiguo.png", "Nuevo", "artista", ["Tag nuevo"]
        )

        self.assertEqual(result["name"], "Nuevo.jpg")
        self.assertTrue((self.root / "procesadas" / "Nuevo.png").is_file())
        self.assertTrue((self.root / "procesadas_jpg" / "Nuevo.jpg").is_file())
        self.assertFalse((self.root / "procesadas" / "antiguo.png").exists())
        rows_by_name = {row["nombre"]: row["tags"] for row in self.manager.read_rows()}
        self.assertEqual(rows_by_name["Nuevo.jpg"], "ilustrador_artista;Tag nuevo")
        self.assertNotIn("antiguo.jpg", rows_by_name)

    def test_renaming_numbered_variant_to_base_uses_next_family_suffix(self):
        (self.root / "procesadas" / "Madoka_7.png").write_bytes(b"png")
        (self.root / "procesadas_jpg" / "Madoka_7.jpg").write_bytes(b"jpg")
        rows = self.manager.read_rows()
        rows.append({"nombre": "Madoka_7.jpg", "tags": "ilustrador_demo;Tag"})
        self.write_rows(rows)

        result = self.manager.update_image(
            "processed", "Madoka_7.png", "Madoka", "artista", ["Tag nuevo"]
        )

        self.assertEqual(result["name"], "Madoka_8.jpg")
        self.assertTrue((self.root / "procesadas" / "Madoka_8.png").is_file())
        self.assertTrue((self.root / "procesadas_jpg" / "Madoka_8.jpg").is_file())

    def test_updates_jpg_and_matching_processed_png(self):
        (self.root / "procesadas" / "catalogo.png").write_bytes(b"png")
        (self.root / "procesadas_jpg" / "catalogo.jpg").write_bytes(b"jpg")
        rows = self.manager.read_rows()
        rows.append({"nombre": "catalogo.jpg", "tags": "ilustrador_demo;Tag"})
        self.write_rows(rows)

        self.manager.update_image(
            "jpg", "catalogo.jpg", "Catalogo nuevo", "demo", ["Tag actualizado"]
        )

        self.assertTrue((self.root / "procesadas" / "Catalogo nuevo.png").is_file())
        self.assertTrue((self.root / "procesadas_jpg" / "Catalogo nuevo.jpg").is_file())
        self.assertEqual(
            self.manager.read_rows()[-1],
            {"nombre": "Catalogo nuevo.jpg", "tags": "ilustrador_demo;Tag actualizado"},
        )

    def test_editing_same_name_does_not_add_suffix(self):
        (self.root / "procesadas" / "existente.png").write_bytes(b"png")

        result = self.manager.update_image(
            "processed", "existente.png", "EXISTENTE", "demo", ["Tag"]
        )

        self.assertEqual(result["name"], "EXISTENTE.jpg")
        self.assertTrue((self.root / "procesadas" / "EXISTENTE.png").is_file())
        self.assertEqual(len(self.manager.read_rows()), 1)

    def test_requires_an_additional_tag(self):
        with self.assertRaisesRegex(ValueError, "al menos un tag"):
            self.manager.update_image("pending", "origen.png", "nuevo", "artista", [])

        self.assertTrue((self.root / "imagenes_png" / "origen.png").is_file())

    def test_rotates_pending_png_and_saves_it_to_processed(self):
        source = self.root / "imagenes_png" / "origen.png"
        image = Image.new("RGB", (2, 3))
        image.putdata([
            (255, 0, 0), (0, 255, 0),
            (0, 0, 255), (255, 255, 0),
            (255, 0, 255), (0, 255, 255),
        ])
        image.save(source)

        self.manager.update_image(
            "pending", "origen.png", "nuevo", "artista", ["Tag nuevo"], 90
        )

        with Image.open(self.root / "procesadas" / "nuevo.png") as image:
            self.assertEqual(image.size, (3, 2))
            self.assertEqual(image.getpixel((0, 0)), (255, 0, 255))
        self.assertFalse(source.exists())

    def test_rotation_updates_processed_png_and_paired_jpg(self):
        png_path = self.root / "procesadas" / "catalogo.png"
        jpg_path = self.root / "procesadas_jpg" / "catalogo.jpg"
        self.write_image(png_path)
        self.write_image(jpg_path)
        rows = self.manager.read_rows()
        rows.append({"nombre": "catalogo.jpg", "tags": "ilustrador_demo;Tag"})
        self.write_rows(rows)

        self.manager.update_image(
            "processed", "catalogo.png", "catalogo", "demo", ["Tag"], 90
        )

        with Image.open(png_path) as image:
            self.assertEqual(image.size, (3, 2))
        with Image.open(jpg_path) as image:
            self.assertEqual(image.size, (3, 2))

    def test_rejects_non_quarter_turn_rotation(self):
        with self.assertRaisesRegex(ValueError, "0, 90, 180 o 270"):
            self.manager.update_image(
                "pending", "origen.png", "nuevo", "artista", ["Tag nuevo"], 45
            )

        self.assertTrue((self.root / "imagenes_png" / "origen.png").is_file())


if __name__ == "__main__":
    unittest.main()
