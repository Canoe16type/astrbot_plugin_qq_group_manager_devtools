"""按实际目录名导入插件模块。

插件目录不一定叫 `astrbot_plugin_qq_group_manager`（GitHub 下 ZIP 会带 `-main` 后缀、
用户也可能改目录名），脚本里写死包名会在这些环境里直接 ImportError。
这里用目录 basename 推导包名，统一走 importlib。

用法（脚本都在 tools/ 下，Python 会自动把脚本目录放进 sys.path）：

    from _plugin_import import BASE, PKG, load
    variant = load("variant")
"""

from __future__ import annotations

import importlib
import os
import sys

# 工具已独立成仓库：优先用 QGM_PLUGIN_DIR 指定插件目录；
# 未指定时尝试同级目录下的 astrbot_plugin_qq_group_manager / 任何 *qq_group_manager*
BASE = os.environ.get("QGM_PLUGIN_DIR") or ""
if not BASE:
    _here = os.path.dirname(os.path.abspath(__file__))
    _parent = os.path.dirname(_here)
    _guess = os.path.join(_parent, "astrbot_plugin_qq_group_manager")
    if os.path.isdir(_guess):
        BASE = _guess
    else:
        for name in os.listdir(_parent):
            if "qq_group_manager" in name and os.path.isdir(os.path.join(_parent, name)) \
                    and not name.endswith("devtools"):
                BASE = os.path.join(_parent, name)
                break
if not BASE or not os.path.isdir(BASE):
    raise SystemExit("找不到插件目录：请设置环境变量 QGM_PLUGIN_DIR 指向 astrbot_plugin_qq_group_manager")
PKG = os.path.basename(BASE)
_PARENT = os.path.dirname(BASE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)


def load(name: str):
    """导入插件内模块，如 load("variant") / load("main")。"""
    return importlib.import_module(f"{PKG}.{name}")
