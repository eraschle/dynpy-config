
# python_version_manager/tests/test_site_packages_viewer.py
import unittest
from pathlib import Path

from dynpy import service as ser


class TestSource(unittest.TestCase):

    def test_regex_embed_python(self):
        path = Path("path/to/embed/python-3.9.12-embed-amd64.zip")

        result = ser.PYTHON_PATTERN.match(path.name)
        self.assertIsNotNone(result, path.name)
        if result is None:
            return
        self.assertEqual(result.group("major"), "3")
        self.assertEqual(result.group("minor"), "9")
        self.assertEqual(result.group("tag"), "12")
        self.assertEqual(result.group("arch"), "amd64")

    def test_regex_embed_python_with_char_in_minor(self):
        path = Path("path/to/embed/python-3.9rc.12-embed-amd64.zip")

        result = ser.PYTHON_PATTERN.match(path.name)
        self.assertIsNotNone(result, path.name)
        if result is None:
            return
        self.assertEqual(result.group("major"), "3")
        self.assertEqual(result.group("minor"), "9rc")
        self.assertEqual(result.group("tag"), "12")
        self.assertEqual(result.group("arch"), "amd64")


if __name__ == '__main__':
    unittest.main()
