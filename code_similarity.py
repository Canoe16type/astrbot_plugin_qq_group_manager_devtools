#!/usr/bin/env python3
"""代码相似度对比（离线，不上传代码）。

用法：
    python code_similarity.py --a /path/repo_a --b /path/repo_b
    python code_similarity.py --a repo --b repo --json out.json

方法：
1. token 指纹：去注释/空白后取 25-token 滑窗，Jaccard + 最长公共片段定位；
2. 函数指纹：AST 结构归一化（标识符/常量替换为占位符）后 hash，
   统计“结构完全相同”的函数数量（避免逐行看）；
3. 文案指纹：长度 >= 8 的字符串字面量 Jaccard + 共同项。

注意：相似度高 ≠ 抄袭。框架样板、官方接口路径、通用写法会造成重合，
结论必须结合长片段、非通用逻辑与文案人工复核。
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import pathlib
import tokenize
from collections import defaultdict

TOKEN_WINDOW = 25
MIN_STRING = 8
SKIP_DIRS = {".git", "__pycache__", "node_modules", "dist", "build", ".venv", "venv"}
TEST_DIRS = {"tests", "test"}
MIN_STMT = 3          # 太小/样板函数不计入结构指纹


def py_files(root: pathlib.Path, include_tests: bool = False) -> list[pathlib.Path]:
    out = []
    for p in root.rglob("*.py"):
        parts = set(p.parts)
        if parts & SKIP_DIRS:
            continue
        if not include_tests and parts & TEST_DIRS:
            continue
        out.append(p)
    return out


def tokens_of(path: pathlib.Path):
    """返回 (token 文本序列, 每个 token 的 (file,line))；忽略注释/缩进/换行。"""
    src = path.read_text(encoding="utf-8", errors="replace")
    toks, locs = [], []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                            tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING):
                continue
            if tok.type == tokenize.ENDMARKER:
                continue
            toks.append(tok.string)
            locs.append((str(path), tok.start[0]))
    except (tokenize.TokenError, IndentationError):
        return [], []
    return toks, locs


def shingles(toks: list[str], k: int = TOKEN_WINDOW):
    return {hash(tuple(toks[i:i + k])) for i in range(max(0, len(toks) - k + 1))}


class _Norm(ast.NodeTransformer):
    """把标识符/常量替换成占位符，保留控制流与调用结构。"""

    def visit_Name(self, node):
        return ast.copy_location(ast.Name(id="V", ctx=node.ctx), node)

    def visit_arg(self, node):
        return ast.copy_location(ast.arg(arg="A", annotation=None), node)

    def visit_Constant(self, node):
        return ast.copy_location(ast.Constant(value="C"), node)

    def visit_Attribute(self, node):
        self.generic_visit(node)
        return ast.copy_location(ast.Attribute(value=node.value, attr="M", ctx=node.ctx), node)


def function_hashes(path: pathlib.Path) -> dict[str, list[str]]:
    """结构 hash -> [函数名]，用于统计结构相同的函数。"""
    src = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}
    out: dict[str, list[str]] = defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if len(getattr(node, "body", [])) < MIN_STMT:
                continue          # 一行/样板函数不计
            clone = _Norm().visit(ast.parse(ast.unparse(node)))
            dump = ast.dump(clone, include_attributes=False)
            out[hashlib.sha1(dump.encode()).hexdigest()].append(node.name)
    return out


def string_literals(path: pathlib.Path) -> set[str]:
    src = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    vals = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value.strip()
            if len(s) >= MIN_STRING and "\n" not in s:
                vals.add(s)
    return vals


def collect(root: pathlib.Path, include_tests: bool = False):
    all_tokens, all_locs, all_sh, fn, strings = [], [], set(), {}, set()
    per_file = {}
    for p in py_files(root, include_tests):
        toks, locs = tokens_of(p)
        if not toks:
            continue
        all_tokens.extend(toks + ["<EOF>"])
        all_locs.extend(locs + [(str(p), 0)])
        sh = shingles(toks)
        per_file[str(p.relative_to(root))] = len(sh)
        all_sh |= sh
        for h, names in function_hashes(p).items():
            fn.setdefault(h, []).extend(f"{p.relative_to(root)}::{n}" for n in names)
        strings |= string_literals(p)
    return {"tokens": all_tokens, "locs": all_locs, "shingles": all_sh,
            "functions": fn, "strings": strings, "per_file": per_file}


def top_common_windows(a, b, limit=10):
    """找 A 中落在 B 的长 token 序列（贪心扩展），给出文件/行号。"""
    bt = b["tokens"]
    best = []
    seen = set()
    i = 0
    while i < len(a["tokens"]):
        run = 0
        # 以 TOKEN_WINDOW 为最小匹配，能扩多长扩多长
        while i + run < len(a["tokens"]) and run < 400:
            seq = a["tokens"][i:i + run + TOKEN_WINDOW]
            if not seq or tuple(seq) not in _sets(bt):
                break
            run += 1
        if run >= 5:
            key = i
            if key not in seen:
                seen.add(key)
                f, line = a["locs"][i]
                best.append({"file": f, "line": line, "tokens": run + TOKEN_WINDOW})
            i += max(1, run)
        else:
            i += 1
        if len(best) >= limit * 3:
            break
    best.sort(key=lambda x: -x["tokens"])
    return best[:limit]


_WINDOW_CACHE = {}


def _sets(bt):
    key = id(bt)
    if key not in _WINDOW_CACHE:
        _WINDOW_CACHE[key] = {tuple(bt[i:i + TOKEN_WINDOW])
                              for i in range(max(0, len(bt) - TOKEN_WINDOW + 1))}
    return _WINDOW_CACHE[key]


def compare(a_root: pathlib.Path, b_root: pathlib.Path, top=10, include_tests=False) -> dict:
    A, B = collect(a_root, include_tests), collect(b_root, include_tests)
    inter = A["shingles"] & B["shingles"]
    union = A["shingles"] | B["shingles"]
    jac = len(inter) / len(union) if union else 0.0
    common_fn = {h: (A["functions"][h], B["functions"][h])
                 for h in A["functions"].keys() & B["functions"].keys()}
    inter_s, union_s = A["strings"] & B["strings"], A["strings"] | B["strings"]
    return {
        "a_root": str(a_root), "b_root": str(b_root),
        "files": {"a": len(A["per_file"]), "b": len(B["per_file"])},
        "tokens": {"a": len(A["tokens"]), "b": len(B["tokens"])},
        "shingle_jaccard": round(jac, 4),
        "shared_shingles": len(inter),
        "identical_function_structures": len(common_fn),
        "function_examples": list(common_fn.values())[:top],
        "string_jaccard": round(len(inter_s) / len(union_s), 4) if union_s else 0.0,
        "shared_strings": sorted(inter_s)[:top],
        "longest_common_windows": top_common_windows(A, B, top),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--json", default="")
    ap.add_argument("--include-tests", action="store_true", help="默认排除 tests/（测试相似不代表抄袭）")
    args = ap.parse_args()
    res = compare(pathlib.Path(args.a).resolve(), pathlib.Path(args.b).resolve(),
                  args.top, args.include_tests)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
