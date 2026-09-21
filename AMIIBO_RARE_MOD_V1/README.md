# Amiibo Rare Reward Hub V1

状态：候选 MOD 已生成，离线验证 PASS，未在游戏内验证；未安装到本机游戏，未连接 Deck。

用户目标：排除普通补给；先收集核心实用装备，再收集特色珍品；防具尽量不重复；保留独立特殊召唤。

交付：`DECK_TRANSFER/` 整个文件夹，无压缩包。安装说明在其中 `先看这里.md`。

## 已实现和边界

- 只覆盖弓箭林克 table 008；使用之前测试身份进入，其他 amiibo 入口保持不变。
- 01_core 六项，02_collection 二十七项，03_refill 八项。
- 所有 Normal/Parasail/Remain 阶段的 BigHit 与 GreatHit 分支均使用各配置白名单。
- Normal RepeatNum=1 且列为空，配合1个宝箱的扣除得到0普通落物；SmallHit次数与概率均为0。
- 独立 AI 名称 `RareRewardHubV1`，不替换共享 AI，避免影响其他卡的召唤/掉落。
- 只使用实际本地原MOD中出现过的33个奖励ID；没有加入梅祖拉假面或剧情物品。
- 自动阶段切换、武器库存检测、永久防具去重 **未实现**；手动切换配置或使用已获得清单生成剩余池。
- 特殊召唤通过独立身份保留；不是随机抽中召唤，也未验证狼的心数。其他卡仍可能出普通物资。

## 本机重新生成

已有 Python 3.10 环境：`../gokuraku_wan_animate_single_test_v1/runtime/.venv/Scripts/python.exe`。
oead 1.2.9.post4 仅安装到本目录 tools_lib，未更改已有虚拟环境的包。Deck安装器只需Python标准库。

```powershell
& '..\gokuraku_wan_animate_single_test_v1\runtime\.venv\Scripts\python.exe' -X utf8 .\build_mod.py
& '..\gokuraku_wan_animate_single_test_v1\runtime\.venv\Scripts\python.exe' -X utf8 .\test_mod.py
```

### 严格按剩余清单生成

复制 `owned.example.json` 为新的 `owned.json`，将已获得的物品ID加入 `obtained`。中文名称对应见 `catalog.json`。

```json
{"obtained":["Weapon_Bow_072","Armor_225_Head"]}
```

```powershell
& '..\gokuraku_wan_animate_single_test_v1\runtime\.venv\Scripts\python.exe' -X utf8 .\build_mod.py --owned .\owned.json --out .\REMAINING_01
```

生成逻辑：有缺失核心→只出缺失核心；否则有缺失收藏→只出缺失收藏；全部集齐→武器补充池。每次用新输出目录，不覆盖旧结果。
新输出目录会自动包含安装器；传输新输出，通过 manifest.json 中实际配置名，例如 `04_remaining_core` 安装。这一步是**根据人工登记重新生成**，不是游戏自动读取进度。每次确认收到物品后再登记。

## 安装及恢复保障

安装器合并目标MOD当前 RSTB，只提高需要的4个资源条目的分配上限，不降低任何已有条目，不覆盖其他条目；保留原文件备份和SHA256。分配上限为保守余量，仍需要游戏内验证。

目标仅008 actorpack和RSTB；源角色资产未编辑。结构与内容回读、跨配置切换、RSTB非目标条目保留、恢复原始字节、重新安装、外部改动拒绝覆盖均通过；`validation.json` 记录结果。
测试使用 `tests/run_*` 独立目录，保留证据，未操作实际模拟器进程。

## 下一步

在 Deck 实际女性角色MOD的romfs安装01_core，用弓箭林克身份扫描一次。确认无普通物资、核心奖励出现且人物MOD仍正常，再进入正常收集。失败时记录提示，不先调整keys/firmware，不盲目修改更多游戏资源。

## 机制与工具参考

- https://zeldamods.org/wiki/Amiibo_drops
- https://zeldamods.org/wiki/AIDef:Action/ItemAmiiboCreateFromDropTable
- https://gist.github.com/leoetlino/a67a874111c1bd97805239f8678e0d00
- https://github.com/MrCheeze/botw-tools/blob/master/amiibo.txt （Archer Link → table008）
- https://github.com/leoetlino/botw-re-notes/blob/master/resource_system.md
- https://github.com/zeldamods/oead
- https://raw.githubusercontent.com/N3evin/AmiiboAPI/master/database/amiibo.json （三种公开角色ID）
