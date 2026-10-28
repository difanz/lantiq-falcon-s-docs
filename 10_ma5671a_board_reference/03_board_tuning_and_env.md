# 10.3 U-Boot 环境与现代配套

环境项的用途可以从原厂脚本确定，但本次 image0 dump 不包含 U-Boot 和 uboot_env。以下描述接口与 geometry，不给出本板注册凭证、MAC、校准数据或可直接刷写的命令。

## 环境 geometry

DT 将 uboot_env 放在 Flash `0x040000`，长度 `0x080000`。原厂 `extracted/rootfs/etc/init.d/fw_env.sh` 按 /proc/mtd 的标签查找设备：env size 固定 `0x10000`，erase size 取 /proc/mtd；冗余副本位于分区大小的一半。它只在配置不存在时生成，不能认为每次启动都会校验或更新已有配置。

当该分区 erasesize 为 `0x10000` 时，结果为：

```text
# device          relative offset   env size   erase size
/dev/<env-mtd>    0x0               0x10000    0x10000
/dev/<env-mtd>    0x40000           0x10000    0x10000
```

两个环境块绝对位置是 `0x040000`、`0x080000`，各 **64 KiB**；512 KiB 分区不是两个 256 KiB 环境块。块大小包含格式头。设备编号必须由标签解析，不能固定使用 mtd1。

现代 `lantiq-gpon/rootfs/etc/init.d/S20uboot_env` 更严格：只接受唯一 uboot_env、分区大小 `0x80000`、erasesize `0x10000`，再原子生成这两行配置；不匹配便返回错误。它还以受限权限缓存环境，不能把缓存全文加入公开诊断或文档。

## 环境变量与使用者

| 项 | 原厂使用者 | 行为 |
| --- | --- | --- |
| sgmii_mode | lib/falcon.sh、lan.sh | 选择 UNI SerDes 模式；sfp_eeprom.sh 的 bitrate_config 调用已注释 |
| asc0 | lib/falcon.sh、pin_cfg.sh，其他 SFP 控制路径 | 0–3；pin_cfg.sh 中只生成限制列表，见引脚页 |
| tx_fault_pin | pin_cfg.sh | 两个分支发送同一 optic 命令，不能当作启用 TX_Fault 的开关 |
| nSerial / nPassword | onu.sh | PLOAM 序列号/密码；参数格式以工具解析器为准，不展示单板值 |
| nDyingGaspEnable | onu.sh / gpon 配置 | gtc_dying_gasp_cfg_set；不是所有配置都直接来自 env |
| olt_type | lib/falcon.sh、onu.sh | env 优先，缺失再读 UCI gpon；用于 GPE 初始化 |
| ploam_emergency_stop_state | lib/falcon.sh、onu.sh | 传给 gtccs 的紧急停止标志 |
| goi_calibrated | lib/falcon.sh、onu.sh | 校准状态影响 GTC watchdog |
| goi_config | recover_goi.sh、goi_store_uboot.sh | 校准归档，不等同于 /etc/config/goi_config 的配置内容 |
| mib_file | omcid.sh | env 指向的 /etc/mibs 文件存在才采用，否则使用 UCI/default |
| omci_iop_mask | omcid.sh | env 优先，否则 UCI/default，传给 -i |
| gDtiaGentEnable | load_dti_agent.sh | 必须为 true 才开 DTI TCP 9000 |

## sgmii_mode 的真实参数

原厂 lan.sh 的 decode_sgmii_mode() 以 gpon_lan_phy_sgmii() 组合 mux、mode、speedmode 与 autoneg_mode，不能简化成一个 2–6 的“模式编号”。mux 固定为 4；speedmode 是三个命令参数。

| env 值/别名 | mode | speedmode | autoneg_mode |
| --- | --- | --- | --- |
| 1 / sgmii | 3 (SGMII) | 0 0 0 | 1 |
| 2 / sgmii_fast | 3 | 1 0 5 | 0 |
| 3 / serdes | 14 (TBI_SERDES) | 1 0 4 | 3 |
| 4 / serdes_noaneg | 14 | 1 0 4 | 0 |
| 5 / sgmii_fast_auto | 15 (TBI_AUTODETECT) | 1 0 5 | 3 |
| 未设置/不识别 | 15 | 0 0 0 | 3 |

未设置与值 5 的 speedmode 不同，不能写成完全等价。原厂 sfp_eeprom.sh 定义的 bitrate_config() 会对 2/5 写 Byte12=25，其他写 10，但 boot() 中该调用已注释，所以不能据此说启动时一定更新 EEPROM 速率。Byte12 也不是实际测得的链路速度；链路协商结果需要硬件验证。

## 校准归档

原厂 goi_store_uboot.sh 依据 /etc/goiupgrade.conf 打包三张 CSV 表、etc/optic/goi_age、etc/config/goi_config，以 uuencode -m 转成文本，再把换行换成 @ 写入 env goi_config。recover_goi.sh 在 .goi_recovered 缺失时逆向解码恢复。这是本板校准保全机制，通用镜像不能替代每块板自己的校准内容。

## 现代配套与启动验证

原厂模块/用户态是 Linux 3.10.49 + uClibc 的二进制基准。还原源码 linux-3.10.49 分支用于对照；Linux 7.3 则必须配套 kernel/、worktrees/linux-7.3/bsp、lantiq-gpon/ 的 linux-7.3 分支、目标工具链与打包配置。模块 ABI、动态加载器和共享库依赖均须匹配，不应混用原厂 ko 与 7.3 内核。

7.3 DTS 用 reserved-memory 保留物理 `0x03F00000` 起的 1 MiB 给 VPE1。kernel/arch/mips/lantiq/falcon/vpe.c 会校验命令行请求是否落在保留区，vpe1_get_load_addr() 返回用于复制和启动的 KSEG0 地址，不能统称为物理地址。内核向 VPE1 传递的 a3 是启动环境 memsize 对应的总字节数，不是 Linux 扣除保留区后的容量。旧版的 vpe1_wdog 参数不能据此推断当前 7.3 存在已启用的 VPE watchdog。

现代 init 的主要顺序为 S20uboot_env、S30goi_recover、S40modules、S50optic、S55onu、S60sfp_eeprom、S63pins、S65network、S68ssb_check、S80daemons。它使用 falcon.conf、defaults 和 runtime.conf，由 functions.sh 读配置；不是原厂 rc.common/UCI 脚本的直接运行环境。

审阅一个镜像时先对 image-manifest.json 的 kernel_source_commit、bsp_source_commit、userspace_source_commit、dirty 标志和文件哈希与实际源码/产物作对应。现有 build/linux-7.3-bootfix 的 manifest 固定记录 kernel a5f4a8726、BSP eec206a、userspace 0759787，它是历史构建，不能证明后续源码修正已打包。编译、静态 ABI/布局检查、镜像解包可验证配套结构；串口完整启动、根文件系统切换、VPE1 外部 I2C 事务、光路校准、UNI 链路和 OLT O5/OMCI 业务仍需板上分别验证。本工作区这些构建记录不提供已完成实机启动的证明。
