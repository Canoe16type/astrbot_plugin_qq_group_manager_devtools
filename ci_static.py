#!/usr/bin/env python3
"""插件静态体检：未定义名、危险调用、硬编码密钥、静默吞错统计。

用法：
    python ci_static.py --plugin /path/to/astrbot_plugin_qq_group_manager

退出码：发现 undefined name / 危险调用 / 密钥特征 → 1；只统计静默 except → 0。
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import re
import subprocess
import sys

BAD_CALLS = ("eval(", "exec(", "os.system(", "subprocess.", "pickle.loads(", "yaml.load(")
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|BEGIN [A-Z ]*PRIVATE KEY)")


def pyflakes_errors(root: pathlib.Path) -> list[str]:
    try:
        import pyflakes  # noqa: F401
    except ImportError:
        return []
    out = subprocess.run([sys.executable, "-m", "pyflakes", str(root)],
                         capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if "undefined name" in l or "redefinition" in l]


def scan_sources(root: pathlib.Path):
    bad_calls, secrets, silent = [], [], []
    for p in sorted(root.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        try:
            src = p.read_text(encoding="utf-8")
        except OSError:
            continue
        if "tests" not in p.parts:          # 测试里允许出现「eval(」字样做断言
            for pat in BAD_CALLS:
                if pat in src:
                    bad_calls.append(f"{p}: {pat}")
        if SECRET_RE.search(src):
            secrets.append(str(p))
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            bad_calls.append(f"{p}: SyntaxError {e}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                body = node.body
                if len(body) == 1 and isinstance(body[0], ast.Pass):
                    silent.append(f"{p}:{node.lineno}")
    return bad_calls, secrets, silent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plugin", required=True)
    args = ap.parse_args()
    root = pathlib.Path(args.plugin).resolve()

    undefined = pyflakes_errors(root)
    bad_calls, secrets, silent = scan_sources(root)

    print(f"未定义名/redefinition：{len(undefined)}")
    for x in undefined[:30]:
        print("  ", x)
    print(f"危险调用/语法错误：{len(bad_calls)}")
    for x in bad_calls[:20]:
        print("  ", x)
    print(f"疑似密钥：{len(secrets)}")
    for x in secrets[:10]:
        print("  ", x)
    print(f"完全静默的 except：{len(silent)}（仅统计，建议热路径补日志）")
    for x in silent[:15]:
        print("  ", x)

    return 1 if (undefined or bad_calls or secrets) else 0


if __name__ == "__main__":
    raise SystemExit(main())
