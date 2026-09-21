# Suyu amiibo 最小测试

目标：在 Suyu dev-0de49070e4（2024-04-10）中验证自行构造的未加密 amiibo 文件能否用于《旷野之息》的扫描。

## 文件

- `link_archer_plain_test.bin`：540 字节，Link - Archer 的公开角色编号，模拟器内部未加密 NTAG215File 格式。
- `generate_test.py`：可复现生成脚本；已有不同内容时拒绝覆盖。
- `validation.json`：结构检查和 SHA256。

此文件是合成测试数据，不是从实体卡提取的备份，不是用于写实体 NFC 卡的文件。没有使用或下载 amiibo 密钥。没有游戏存档区、狼林克心数或已注册的 Mii。不要用它替代游戏密钥文件。

## Steam Deck 上测试

1. 只传 `link_archer_plain_test.bin` 到 Deck；例如建立 `/home/deck/Documents/amiibo/` 后放入。无需传脚本，也不用放进 romfs 或 keys。
2. 在游戏中保存当前进度，去有空间的室外位置。
3. 游戏设置启用 amiibo，选中 amiibo 能力，再按使用能力键，让落点圆圈出现。
4. 通过你已映射的“Load Amiibo”快捷键打开文件选择窗口，选中这个 `.bin` 文件并打开。
5. 查看是否识别并掉落物品。具体奖励由游戏进度、随机规则及当前 MOD 决定，此样本不保证指定装备。

若首次成功，先不要反复扫描同一个文件，以免每日次数提示干扰判断。

## 若不成功

- “Game is not looking for nfc tag”：先在游戏中进入 amiibo 等待扫描状态。
- “Not an amiibo / Can't decode amiibo / 数据损坏”：记录原始错误；需要核对该 Suyu 构建的解析差异，不能用“改扩展名”修复。
- 提示注册或昵称：记录提示，此最小样本没有注册 Mii。
- 文件选择器看不见文件：确认 `.bin` 在 Deck 本地且能读取，不是只停留在电脑上。
- 读取成功但无掉落：记录游戏画面及提示，区分每日限制、地点、游戏进度和 MOD 掉落逻辑。

## 验证边界

仅验证文件长度、UID 校验、标签类型及固定字段，并测试截断/字段损坏会被结构验证器拒绝。未启动本地游戏，未连接 Steam Deck，未证实实际掉落成功。

Suyu 的确切提交源码访问返回 403；格式参考来自同源 Yuzu/Eden 的公开实现，上游 Yuzu 2023 年 3 月报告已支持 plain amiibo。不能把上游结构检查等同于该 Suyu 版本实测。

参考链接记录在 validation.json。原来的 XD543 游戏包、MOD、固件、keys、存档均未修改。
