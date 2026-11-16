#!/usr/bin/env python3
"""运行时基线：导入耗时、RSS、词库构建、处罚决策 p95。

用法：
    QGM_PLUGIN_DIR=/path/to/astrbot_plugin_qq_group_manager python bench_runtime.py
"""

from __future__ import annotations

import json
import os
import pathlib
import statistics
import subprocess
import sys
import time

PLUGIN = pathlib.Path(os.environ.get("QGM_PLUGIN_DIR", "")).resolve()
if not PLUGIN.is_dir():
    raise SystemExit("请设置 QGM_PLUGIN_DIR 指向插件目录")
PKG_ROOT = PLUGIN.parent.parent  # /root/data
MOD = f"plugins.{PLUGIN.name}"


def import_cost():
    code = (
        "import sys,time,resource;"
        f"sys.path.insert(0,{str(PKG_ROOT)!r});"
        f"t=time.perf_counter();import {MOD}.main;"
        "print((time.perf_counter()-t)*1000);"
        "print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.split()
    # 再测一次"框架已加载后，插件自身导入"的增量，避免把 AstrBot 启动算到插件头上
    code2 = (
        "import sys,time,resource;"
        f"sys.path.insert(0,{str(PKG_ROOT)!r});"
        "import astrbot.api.star,astrbot.api.event,astrbot.api.web;"
        f"t=time.perf_counter();import {MOD}.main;"
        "print((time.perf_counter()-t)*1000);"
        "print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)"
    )
    out2 = subprocess.run([sys.executable, "-c", code2], capture_output=True, text=True, check=True).stdout.split()
    return {"import_with_framework_ms": round(float(out[0]), 1),
            "plugin_import_ms": round(float(out2[0]), 1),
            "rss_mb": round(int(out2[1]) / 1024, 1)}


def lexicon_cost():
    sys.path.insert(0, str(PKG_ROOT))
    from plugins.astrbot_plugin_qq_group_manager.qgm.features.lexicon import lexicon as L  # noqa

    t = time.perf_counter()
    mgr = L.LexiconManager(str(PLUGIN / "data" / "_bench"), plugin_dir=str(PLUGIN), logger=None)
    init_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    mgr.hits("刷单返利 加微信")  # 触发首次编译
    first_ms = (time.perf_counter() - t) * 1000
    return {"lexicon_init_ms": round(init_ms, 1), "lexicon_first_compile_ms": round(first_ms, 1)}


def decision_cost(n: int = 20000):
    sys.path.insert(0, str(PKG_ROOT))
    from plugins.astrbot_plugin_qq_group_manager import moderation
    from plugins.astrbot_plugin_qq_group_manager.qgm.features.audit import policy

    settings = dict(moderation.ModerationStore.DEFAULT_SETTINGS)
    verdict = {"violation": True, "severity": "medium", "confidence": 0.9,
               "category": "ads", "from_cache": False}
    rules = [{"id": 1, "name": "广告", "keywords": ["广告"], "seconds": 600}]
    samples = []
    for _ in range(n):
        t = time.perf_counter()
        policy.build_plan(
            verdict=verdict, settings=settings, prior=2, rules=rules, default_seconds=600,
            decide_action=moderation.decide_action, escalate_seconds=moderation.escalate_seconds,
            fmt_duration=lambda s: f"{s}s",
        )
        samples.append((time.perf_counter() - t) * 1000)
    samples.sort()
    return {"decision_p50_ms": round(statistics.median(samples), 3),
            "decision_p95_ms": round(samples[int(len(samples) * 0.95)], 3),
            "decision_p99_ms": round(samples[int(len(samples) * 0.99)], 3)}


if __name__ == "__main__":
    result = {}
    result.update(import_cost())
    result.update(lexicon_cost())
    result.update(decision_cost())
    print(json.dumps(result, ensure_ascii=False, indent=2))
