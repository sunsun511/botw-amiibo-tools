# BOTW amiibo 工具归档

普通 amiibo 测试文件 + Steam Deck 珍品奖励 MOD，私有归档。

## 下载后使用

- 普通版：`AMIIBO_TEST_V1/link_archer_plain_test.bin`，不安装奖励 MOD 时按游戏原有规则掉落。
- 修改版：把 `AMIIBO_RARE_MOD_V1/DECK_TRANSFER` 整个目录传到 Deck；按其中的 `先看这里.md` 安装，再加载 `amiibo/rare_hub_archer.bin`。
- 两个弓箭林克 bin 身份相同；改变掉落的是 MOD，不是 bin。仅换 bin 不会撤销 MOD，也不会重置每日扫描限制。

## 已确认的实际结果（2026-09-21）

用户报告在 Steam Deck 安装01_core并扫描后成功获得鬼神大剑，基本无问题。属于用户实测反馈，确认核心入口跑通；不能据此认为所有装备、02_collection/03_refill或特殊召唤已逐项验证。

01_core：黄昏弓、鬼神大剑、大鼓隆之剑、鬼神套三件。
02_collection：其他特色收藏27项。
03_refill：特色武器弓盾8项。

阶段需退出模拟器后手动切换。游戏内自动切换、永久去重、武器库存检测未实现。`--owned` 接收人工已获得清单，生成剩余池。

Deck现有目标：`/home/deck/.local/share/suyu/load/01007EF00011E000/botw_mod/romfs`。
安装器备份/恢复只处理008 actorpack和资源大小表，不修改人物模型、存档、固件或keys。

## 重建和离线验证

建议Python 3.10，先在虚拟环境安装 `requirements.txt`。然后在仓库根目录运行：

```sh
python AMIIBO_RARE_MOD_V1/build_mod.py --out rebuilt_transfer
python AMIIBO_RARE_MOD_V1/test_mod.py
```

`source_romfs` 只包含重建所需的15个原奖励actorpack和已有资源大小表，来自本地原MOD，保留于此私有归档。无需原Windows绝对路径或游戏镜像即可重建。第三方资源不作原创授权声明。
旧目录中的README包含历史本机命令；跨电脑重建以上述命令及相对路径为准。

## 归档范围

保存普通版和修改版成品、生成/安装/恢复脚本、物品清单、验证记录和说明。没有上传游戏镜像、密钥、固件、游戏存档、模拟器配置或日志。依赖库、缓存、重复测试文件、重复压缩包不归档。
普通bin为合成模拟器内部plain测试格式，不是实体NFC备份；特殊召唤身份仍有未验证项，详见安装说明。

`ARCHIVE_MANIFEST.json` 记录每个归档文件的SHA256和Git blob SHA，供远端验证及将来下载校验。
