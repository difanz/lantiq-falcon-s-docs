# 10.2 板级资源与启动职责

MA5671A 将处理器、64 MiB 内存、SPI NOR、串口、I2C 和 GPON 数据通路组合成单 UNI 的 SFP 设备。板级资源分配如下。

## 启动交接

启动加载器完成基本内存准备、选择镜像并将控制权交给主控处理器。内核镜像加载到 `0x80002000`，镜像前部携带设备描述。板级参数还需传递内存容量、控制台和协处理器保留区，避免主控与 VPE1 使用同一段内存。

## 板级外设资源

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
| GPTC | lantiq,gptc-falcon | `0x1E100E00/0x100` | 设备描述未声明中断 |
| SSC SPI | lantiq,spi-lantiq-ssc，disabled | `0x1E100D00/0x100` | 与启动 NOR 的 sflash 控制器不同 |
| EBU | lantiq,ebu-falcon | `0x18000000/0x100` | 板级设备描述地址 |
| sflash localbus | lantiq,sflash-falcon | `0x10000000/0x04000000` | 控制器窗口 64 MiB，实际 NOR 16 MiB |

完整 PAD/GPIO 表见[引脚映射](01_pinmux_and_sfp_mapping.md)。I2C 节点使用 `lantiq,lantiq-i2c` 控制器配置。

## NOR 分区

| 标签 | Flash 偏移 | 大小 | 说明 |
| --- | --- | --- | --- |
| uboot | `0x000000` | `0x040000` | 启动加载器；设备描述标记只读 |
| uboot_env | `0x040000` | `0x080000` | 冗余启动环境 |
| image0 | `0x0C0000` | `0x740000` | 系统镜像槽 0，7424 KiB |
| image1 | `0x800000` | `0x800000` | 系统镜像槽 1，8192 KiB |

启动时镜像解析器注册 kernel/rootfs/rootfs_data 子分区。MTD 编号随注册顺序变化，各分区按标签、偏移和大小识别。

## 启动职责与依赖

各启动阶段按下列硬件依赖组织。

| 阶段 | 职责 | 后续依赖 |
| --- | --- | --- |
| 存储与环境 | 识别分区、读取板型和环境、准备可写存储 | 镜像选择、网络与校准配置 |
| 校准恢复 | 装入本板光路参数与温度表 | 光模拟前端初始化 |
| 硬件基础 | 时钟、复位、中断和控制通道 | GTC、GPE、光前端 |
| GPON 数据通路 | 激活控制、GPHY/GPE 微码、共享缓冲和队列 | UNI、管理通道与业务转发 |
| SFP 设备服务 | EEPROM、VPE1、DDM 和软控制 | 外部宿主的设备发现与状态读取 |
| 引脚和 UNI | TX_Disable、LOS、串口争用、SerDes 模式 | 电气接口和宿主链路 |
| 管理服务 | OMCI、光校准闭环、本地维护和进程监控 | 管理配置、故障定位与业务运行 |

设备环境项 `gDtiaGentEnable=true` 启用 DTI 维护服务。

## 板型和 MAC 分配

MA5671A 的 SFP 配置使用一个 UNI，管理通道与业务流共享该接口。

设备的基准 MAC 可由启动环境 ethaddr 提供。接口地址的既有派生规则是对 **第 5 个八位组** 加偏移、第 6 个保持不变：本地维护和 UNI0 +0、预留 UNI1 +1、host +2、WAN 管理 +3。各偏移逐字节应用于第 5 个八位组，接口地址须保持唯一。
