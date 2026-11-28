#!/usr/bin/env python3
"""记录查询缓存基准：合成 1k/5k/10k 条判定记录，测冷/热查询与详情。"""
from __future__ import annotations

import argparse
import importlib
import pathlib
import sys
import time
from types import SimpleNamespace


def load_query(plugin: pathlib.Path):
    sys.path.insert(0, str(plugin.parent.parent))
    return importlib.import_module(
        "plugins.astrbot_plugin_qq_group_manager.qgm.features.records.query"
    )


def host(n: int):
    rows = [{
        "id": i, "group": "g", "target": f"u{i}", "target_name": f"成员{i}",
        "created_at": i, "executed": True, "action": "mute", "reason": "基准",
    } for i in range(1, n + 1)]
    return SimpleNamespace(
        mod=SimpleNamespace(list_verdicts=lambda group="", limit=10**9: rows),
        _mute_history={"g": []}, _recall_history={"g": []},
        _plugin_data_dir=lambda: "/tmp/nonexistent-qgm-bench",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plugin", default="../astrbot_plugin_qq_group_manager")
    ap.add_argument("--sizes", default="1000,5000,10000")
    ap.add_argument("--page-size", type=int, default=50)
    ns = ap.parse_args()
    q = load_query(pathlib.Path(ns.plugin).resolve())
    print(f"page_size={ns.page_size}")
    for n in [int(x) for x in ns.sizes.split(",") if x.strip()]:
        h = host(n)
        t0 = time.perf_counter()
        rows, total = q.query_page(h, group="g", page=1, per_page=ns.page_size)
        cold = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        q.query_page(h, group="g", page=2, per_page=ns.page_size)
        warm = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        item = q.get(h, f"V{n // 2}", group="g")
        detail = (time.perf_counter() - t0) * 1000
        print(
            f"n={n:<6} cold={cold:8.2f}ms warm={warm:8.2f}ms "
            f"detail={detail:8.2f}ms rows={len(rows)} total={total} hit={bool(item)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
