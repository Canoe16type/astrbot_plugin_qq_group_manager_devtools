#!/usr/bin/env python3
"""在 devtools 中运行插件仓库的全量测试，不复制测试文件。

用法：
    python run_plugin_tests.py --plugin ../astrbot_plugin_qq_group_manager
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys


def run(plugin: pathlib.Path, args: list[str]) -> int:
    env = os.environ.copy()
    parent = str(plugin.parent)
    env["PYTHONPATH"] = parent + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    print("+", " ".join([sys.executable, *args]))
    return subprocess.call([sys.executable, *args], cwd=str(plugin), env=env)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plugin", default="../astrbot_plugin_qq_group_manager", help="插件仓库目录")
    ap.add_argument("--no-loader", action="store_true", help="跳过 loader 冒烟测试")
    ns = ap.parse_args()
    plugin = pathlib.Path(ns.plugin).expanduser().resolve()
    if not (plugin / "tests").is_dir():
        print(f"找不到 tests/: {plugin}", file=sys.stderr)
        return 2
    rc = run(plugin, ["-m", "unittest", "discover", "-s", "tests"])
    if rc == 0 and not ns.no_loader:
        rc = run(plugin, ["-m", "unittest", "tests.test_loader_harness"])
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
