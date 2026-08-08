import unittest
import os
import tempfile
import json
from pathlib import Path
from analyzer import (
    app,
    human_size,
    get_platform_info,
    get_shell_info,
    get_home_folder,
    scan_directory,
)


class TestAnalyzerHelpers(unittest.TestCase):

    def test_human_size(self):
        self.assertEqual(human_size(0), "0.0 B")
        self.assertEqual(human_size(500), "500.0 B")
        self.assertEqual(human_size(1024), "1.0 KB")
        self.assertEqual(human_size(1048576), "1.0 MB")
        self.assertEqual(human_size(1073741824), "1.0 GB")

    def test_platform_info(self):
        info = get_platform_info()
        self.assertIn("os", info)
        self.assertIn("platform", info)
        self.assertIn(info["os"], ["Windows", "macOS", "Linux"])

    def test_shell_info(self):
        shell = get_shell_info()
        self.assertIsInstance(shell, str)
        self.assertTrue(len(shell) > 0)

    def test_home_folder(self):
        home = get_home_folder()
        self.assertTrue(Path(home).exists())

    def test_scan_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dummy files
            file1 = Path(tmpdir) / "test1.txt"
            file2 = Path(tmpdir) / "test2.png"
            file1.write_text("hello world")
            file2.write_bytes(b"\x00" * 2000)

            result = scan_directory(tmpdir, exclude_system=True)
            self.assertNotIn("error", result)
            self.assertEqual(result["total_files"], 2)
            self.assertGreater(result["total_size"], 2000)
            self.assertIn("largest_files", result)
            self.assertIn("ext_breakdown", result)

    def test_scan_directory_non_existent(self):
        result = scan_directory("/path/does/not/exist/123456789")
        self.assertIn("error", result)


class TestAnalyzerAPI(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_index_route(self):
        response = self.app.get("/")
        self.assertEqual(response.status_code, 200)

    def test_platform_route(self):
        response = self.app.get("/platform")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("os", data)
        self.assertIn("shell", data)
        self.assertIn("home", data)

    def test_scan_route_empty_path(self):
        response = self.app.post("/scan", json={"path": ""})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_scan_route_valid_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "sample.doc").write_text("document contents")
            response = self.app.post("/scan", json={"path": tmpdir})
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["total_files"], 1)

    def test_delete_route_no_files(self):
        response = self.app.post("/delete", json={})
        self.assertEqual(response.status_code, 400)

    def test_delete_route_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_to_delete = Path(tmpdir) / "delete_me.tmp"
            file_to_delete.write_text("goodbye")
            path_str = str(file_to_delete)

            response = self.app.post("/delete", json={"files": [path_str]})
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["count_deleted"], 1)
            self.assertEqual(data["count_failed"], 0)
            self.assertFalse(file_to_delete.exists())

    def test_delete_route_directory_safety(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_to_delete = Path(tmpdir) / "subfolder"
            dir_to_delete.mkdir()

            response = self.app.post("/delete", json={"files": [str(dir_to_delete)]})
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["count_deleted"], 0)
            self.assertEqual(data["count_failed"], 1)
            self.assertTrue(dir_to_delete.exists())


if __name__ == "__main__":
    unittest.main()
