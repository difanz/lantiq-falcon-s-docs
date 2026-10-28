# 10.2 falcon-sfp.dts 与启动脚本

本页描述 image0 原厂 Linux 3.10.49 的 DTB 与 OpenWrt 启动链。Linux 7.3 使用移植 DTS、内嵌 initramfs 和 POSIX init 脚本，见 [环境与配套版本](03_board_tuning_and_env.md)。

## 原厂镜像入口

`extracted/images/kernel.bin` 加载地址为 `0x80002000`。文件前 `0x400` 字节是 NOP，`+0x400` 跳往 `0x8000A690`，`+0x408` 为 OWRTDTB:，`+0x410` 是 8160 字节 FDT。kernel_entry 位于文件 `+0x8690`。这是原厂精确布局，不能套用到重编的 7.3 内核；dumps/kernel.elf 是原始镜像的 ELF 包装。

## 原厂 DTB 节点

地址由父总线 ranges 与子节点 reg 相加。IRQ 为 DT 单元原值，ASC 顺序依驱动资源索引解释。

| 节点 | compatible / 状态 | 物理地址 / 大小 | 关键属性 |
| --- | --- | --- | --- |
| CPU | mips,mips34kc | — | CPU/IO/FPI 固定时钟 400/200/100 MHz |
| memory@0 | memory | `0x0/0x04000000` | 64 MiB |
| chosen | — | — | bootargs-append 为 console=ttyLTQ0,115200 init=/etc/preinit |
| ICU | lantiq,icu | `0x1F880200` 起 | 5 段 reg，各 0x28 字节 |
| watchdog | lantiq,wdt | `0x1F8803F0/0x10` | IO clock |
| status | lantiq,status-falcon | `0x1E802000/0x80` | 芯片状态 |
| SYS1 | lantiq,sys1-falcon | `0x1EF00000/0x100` | 时钟控制器 |
| SYS_ETH | lantiq,syseth-falcon | `0x1DB00000/0x100` | GPIO0/2、PAD0/2 时钟 |
| SYS_GPE | lantiq,sysgpe-falcon | `0x1D700000/0x100` | GPE 时钟控制器 |
| ASC0 | lantiq,asc | `0x1E100C00/0x100` | IRQ 104/105/106，line 0 |
| ASC1 | lantiq,asc，disabled | `0x1E100B00/0x100` | IRQ 112/113/114，line 1 |
| I2C | lantiq,lantiq-i2c，okay | `0x1E200000/0x10000` | IRQ 18/19/20/21；gpio1 offset 7/8 |
| GPTC | lantiq,gptc-falcon | `0x1E100E00/0x100` | 原 DT 无 interrupts 属性 |
| SSC SPI | lantiq,spi-lantiq-ssc，disabled | `0x1E100D00/0x100` | 与启动 NOR 的 sflash 控制器不同 |
| EBU | lantiq,ebu-falcon | `0x18000000/0x100` | 原厂节点地址 |
| sflash localbus | lantiq,sflash-falcon | `0x10000000/0x04000000` | 控制器窗口 64 MiB，实际 NOR 16 MiB |

完整 PAD/GPIO 表见 [引脚映射](01_pinmux_and_sfp_mapping.md)。I2C 节点虽然有 gpios 属性，compatible 不含 i2c-gpio，不能据此声称自动回退为 GPIO 驱动。

## NOR 分区

| 标签 | Flash 偏移 | 大小 | 说明 |
| --- | --- | --- | --- |
| uboot | `0x000000` | `0x040000` | DT 标记只读；不在 image0 dump 中 |
| uboot_env | `0x040000` | `0x080000` | 不在 image0 dump 中 |
| image0 | `0x0C0000` | `0x740000` | 本次 dump，7424 KiB |
| image1 | `0x800000` | `0x800000` | 不在本次 dump 中，8192 KiB |

启动时镜像解析器还会注册 kernel/rootfs/rootfs_data 子分区，MTD 编号会随注册顺序变化。mtd0..3 不是跨内核可靠标识，应按标签和 geometry 识别。

## 原厂脚本链

S 序号来自 START；实际启用还取决于 rc.d 链接。完成脚本调用不等于硬件初始化成功。

| 序号 | 脚本 | 职责 |
| --- | --- | --- |
| 40 | fw_env.sh | 从 /proc/mtd 生成环境配置，加载 i2c-dev 与 GPIO37/38 软件 I2C |
| 45 | recover_goi.sh | 从 env goi_config 恢复校准归档 |
| 60 | optic.sh | 加载光驱动，建立设备节点 |
| 61 | onu.sh | PLOAM/GTC、GPHY/GPE 微码和共享缓冲初始化；按校准状态开 GTC watchdog |
| 62 | sfp_eeprom.sh | SFP bank 内容、地址、写保护和 DDM 进程 |
| 63 | pin_cfg.sh | TX_Disable 与 ONU LOS 配置，不直接写 sysfs pinselect |
| 64 | lan.sh | SerDes、EIM、UNI 端口 |
| 65 | lct.sh | mod_onu_netdev、本地维护网络 |
| 85 | omcid.sh | MIB、OMCC version、iop mask；参数为 -d3 -p… -o… -i… -g… -l/tmp/log/debug |
| 87 | load_dti_agent.sh | 仅 env gDtiaGentEnable=true 时启动 gpon_dti_agent -p9000 |
| 89 | load_ocal.sh | 光校准用户态 |
| 97 | monitomcid | OMCI 进程监控 |

omcid.sh 自身不创建 /tmp/omci_pipe，也不直接向 omcid 传递 olt_type。不能把程序内部或其他脚本的行为记成它的命令行。

## 板型与 MAC 派生

`extracted/rootfs/lib/falcon.sh` 优先读 cmdline boardname，再读 cpuinfo machine，最后读 DT model。SFP 返回一个 LAN 端口，LCT 通常为 lct0，但 .hgu/.fttdp 配置会改变结果。

falcon_base_mac_get() 从 cmdline ethaddr 取基准地址，缺失时用源码固定回退值。falcon_mac_get() 偏移加在 **第 5 个八位组**，第 6 个保持不变：lct*/lan/lan0 +0，lan1 +1，host +2，wan +3。这不是 48 位 MAC 整体加法，亦不处理跨字节进位。
