#!/usr/bin/env python3
"""生成发布用 zip：只打运行时必需文件，排除文档截图 / 测试 / 开发工具。

用法：
    python build_release_zip.py --plugin ../astrbot_plugin_qq_group_manager --ref v1.6.0
    python build_release_zip.py --plugin ... --out /tmp/foo.zip

规则：
- 排除 docs/（含截图）、tests/、tools/、.github/、dist/
- 其余按 git 跟踪文件打包，前缀 astrbot_plugin_qq_group_manager/
- 不生成目录条目（与历史发布包结构一致）
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import zipfile

EXCLUDE_PREFIX = ("docs/", "tests/", "tools/", ".github/", "dist/")
PKG = "astrbot_plugin_qq_group_manager"


def tracked_files(plugin: pathlib.Path, ref: str) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(plugin), "ls-tree", "-r", "--name-only", ref],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plugin", required=True, help="插件仓库目录")
    ap.add_argument("--ref", default="HEAD", help="要打包的 tag / 提交（默认 HEAD）")
    ap.add_argument("--out", default="", help="输出 zip 路径")
    args = ap.parse_args()

    plugin = pathlib.Path(args.plugin).resolve()
    files = [f for f in tracked_files(plugin, args.ref) if not f.startswith(EXCLUDE_PREFIX)]
    out = pathlib.Path(args.out) if args.out else pathlib.Path.cwd() / f"{PKG}-slim.zip"

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            src = plugin / f
            if not src.is_file():
                raise SystemExit(f"缺少文件：{f}（ref={args.ref} 与工作区不一致？）")
            z.write(src, arcname=f"{PKG}/{f}")

    size = out.stat().st_size / 1024
    print(f"打包完成：{out}  {size:.1f} KB  文件 {len(files)} 个（已排除 docs/tests/tools/.github）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
