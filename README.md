# QQ官机群管 · 开发工具（自检 / 基准 / 构建）

这是 [QQ官机群管](https://github.com/Canoe16type/astrbot_plugin_qq_group_manager)（`astrbot_plugin_qq_group_manager`）的**配套开发工具仓库**。

## 这个仓库是什么

- 插件维护者用的**离线自检脚本**：不启动 AstrBot，直接验证审核链路、词库、变体、群规解析、`/管理登记`。
- **基准脚本**：量化误杀率、变体召回率、索引构建耗时，用来确认默认参数没被调坏。
- **构建与预览**：从公开词库生成 `lexicons/`、在没有 AstrBot 的环境里预览面板。

## 这个仓库不是什么

- **不是插件本体**，不能装进 AstrBot；插件请装主仓库。
- **不包含词库数据**（生成结果写回插件目录的 `lexicons/`）。
- **不包含 `check_metadata.py`**：版本/徽章/实测版本校验与插件仓库元数据强绑定，留在主仓库。

## 用法

```bash
git clone https://github.com/Canoe16type/astrbot_plugin_qq_group_manager.git
export QGM_PLUGIN_DIR=/path/to/astrbot_plugin_qq_group_manager   # 工具靠它定位插件

PY=~/.local/share/uv/tools/astrbot/bin/python                     # 用 AstrBot 自带解释器

$PY selftest_lexicon.py           # 词库编译与匹配
$PY selftest_variant.py           # 变体检测（谐音 / 形近 / 插符号）
$PY selftest_mod_integration.py   # 审核链路（无 AstrBot 时自动跳过模型层）
$PY selftest_admin_register.py    # /管理登记 链路
$PY selftest_rule_spec.py         # 群规一行式文本解析
$PY build_lexicons.py             # 从公开词库生成 lexicons/（联网，缓存 7 天）
$PY preview_dashboard.py          # 假后端 + 假数据预览面板（端口 8899）
```

## 基准脚本

| 脚本 | 测什么 |
| --- | --- |
| `bench_fp.py` | 误杀率：正常聊天 / 玩梗 / 学术讨论被误判的比例 |
| `bench_evasion.py` | 变体召回：插符号 / 同音 / 全拼等绕写的检出率 |
| `bench_variant.py` | 变体索引的构建耗时与规模 |

## 约定

- 插件目录用 `QGM_PLUGIN_DIR` 指定；未指定时会在同级目录找 `*qq_group_manager*`（排除本仓库）。
- 跑之前建议清一次插件目录的 `__pycache__`，避免加载旧 pyc。
- 脚本只读插件代码与数据，不会修改插件配置；`build_lexicons.py` 会写 `lexicons/`（预期行为）。

## 许可

同主仓库：MIT。
