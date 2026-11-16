"""ci_static 自身的测试：干净仓库通过、未定义名/密钥/危险调用必须失败。"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "ci_static.py"


def run(plugin: pathlib.Path):
    r = subprocess.run([sys.executable, str(SCRIPT), "--plugin", str(plugin)],
                       capture_output=True, text=True)
    return r.returncode, r.stdout


class CiStaticTest(unittest.TestCase):
    def _write(self, root: pathlib.Path, name: str, body: str):
        (root / name).write_text(body, encoding="utf-8")

    def test_clean_project_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._write(root, "ok.py", "def add(a, b):\n    return a + b\n")
            code, out = run(root)
            self.assertEqual(code, 0, out)

    def test_undefined_name_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._write(root, "bad.py", "def f():\n    return missing_name\n")
            code, out = run(root)
            self.assertEqual(code, 1)
            self.assertIn("未定义名", out)

    def test_hardcoded_secret_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._write(root, "sec.py", 'TOKEN = "ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n')
            code, out = run(root)
            self.assertEqual(code, 1)
            self.assertIn("疑似密钥", out)

    def test_dangerous_call_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._write(root, "danger.py", "eval('1+1')\n")
            code, out = run(root)
            self.assertEqual(code, 1)
            self.assertIn("危险调用", out)

    def test_silent_except_is_reported_but_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._write(root, "quiet.py", "try:\n    x = 1\nexcept Exception:\n    pass\n")
            code, out = run(root)
            self.assertEqual(code, 0, out)
            self.assertIn("完全静默的 except：1", out)


if __name__ == "__main__":
    unittest.main()
