# 10.2 板级资源与启动职责

MA5671A 将处理器、64 MiB 内存、SPI NOR、串口、I2C 和 GPON 数据通路组合成单 UNI 的 SFP 设备。以下表格描述板级资源分配；设备描述中的节点状态与外设是否已进入正常工作状态需要分别判断。

## 启动交接

启动加载器完成基本内存准备、选择镜像并将控制权交给主控处理器。设备的一种内核镜像采用加载地址 0x80002000，并在镜像前部携带设备描述；该地址与镜像内部偏移是镜像格式约定，不是 SoC 对所有操作系统的固定要求。板级参数还需传递内存容量、控制台和协处理器保留区，避免主控与 VPE1 使用同一段内存。

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

完整 PAD/GPIO 表见 [引脚映射](01_pinmux_and_sfp_mapping.md)。I2C 节点虽然有 gpios 属性，compatible 不含 i2c-gpio，不能据此声称自动回退为 GPIO 驱动。

## NOR 分区

| 标签 | Flash 偏移 | 大小 | 说明 |
| --- | --- | --- | --- |
| uboot | `0x000000` | `0x040000` | DT 标记只读；不在 image0 dump 中 |
| uboot_env | `0x040000` | `0x080000` | 不在 image0 dump 中 |
| image0 | `0x0C0000` | `0x740000` | 本次 dump，7424 KiB |
| image1 | `0x800000` | `0x800000` | 不在本次 dump 中，8192 KiB |

启动时镜像解析器还会注册 kernel/rootfs/rootfs_data 子分区，MTD 编号会随注册顺序变化。mtd0..3 不是跨内核可靠标识，应按标签和 geometry 识别。

## 启动职责与依赖

启动管理应按照硬件依赖组织，不把进程启动或配置请求成功当成硬件已经就绪。

| 阶段 | 职责 | 后续依赖 |
| --- | --- | --- |
| 存储与环境 | 识别分区、读取板型和环境、准备可写存储 | 镜像选择、网络与校准配置 |
| 校准恢复 | 装入本板光路参数与温度表 | 光模拟前端初始化 |
| 硬件基础 | 时钟、复位、中断和控制通道 | GTC、GPE、光前端 |
| GPON 数据通路 | 激活控制、GPHY/GPE 微码、共享缓冲和队列 | UNI、管理通道与业务转发 |
| SFP 设备服务 | EEPROM、VPE1、DDM 和软控制 | 外部宿主的设备发现与状态读取 |
| 引脚和 UNI | TX_Disable、LOS、串口争用、SerDes 模式 | 电气接口和宿主链路 |
| 管理服务 | OMCI、光校准闭环、本地维护和进程监控 | 管理配置、故障定位与业务运行 |

DTI 调试服务是可选维护功能，设备环境项 gDtiaGentEnable=true 才启用该服务；正常 GPON 数据转发不以调试端口开放为前提。

## 板型和 MAC 分配

板型参数影响 UNI 数量与本地维护接口。MA5671A 的 SFP 配置为一个 UNI；逻辑维护接口数量不代表额外的物理端口。

设备的基准 MAC 可由启动环境 ethaddr 提供。接口地址的既有派生规则是对 **第 5 个八位组** 加偏移、第 6 个保持不变：本地维护和 UNI0 +0、预留 UNI1 +1、host +2、WAN 管理 +3。这是设备级分配约定，不是 SoC 固有规则，也不是对 48 位 MAC 作整体加法。配置地址时应检查唯一性和字节范围，不假定自动跨字节进位。
