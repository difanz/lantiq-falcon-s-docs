# 9.3 驱动 ioctl 与 VPE1 共享内存

本页按本工作区 **配套源码接口** 说明 ioctl，不声明与原厂二进制 ABI 可混用。`bsp/modules/onu/include/drv_onu_*_interface.h` 定义命令，`drv_onu_*.c` 的 `TE1in/TE1out/TE1inout` 表完成分派，命令号应从宏定义取得。原厂模块属于 Linux 3.10.49，Linux 7.3 必须使用同一构建的移植模块；功能兼容不要求将原厂与重建用户态交叉混用。

主控处理器（VPE0）通过三组管理接口分别控制片上 GPON 数据通路、光物理层模拟前端以及 VPE1 双地址 I2C 从机协处理器：

| 管理接口 / 控制通道 | 管辖的硬件模块与物理地址空间 |
| --- | --- |
| GPON 数据通路与 LAN 控制接口 (`/dev/onu`) | `GTC`（`0x1DC00000`）、`GPE`/`SCE`（`0x1D400000`–`0x1D700000`）、`SSB0`（`0x1F200000`）、`EIM`/`SGMII`/`GPHY`（`0x1D800000`）、`TOD`（`0x1D400500`） |
| 光物理层与电源控制接口 (`/dev/optic`) | `PMA`（`0x1DD00000`）、`FCSIC`（`0x1DD00600` 桥接 BOSA 模拟寄存器）、`DCDC_APD`（`0x1E805000`）、`DCDC_CORE`（`0x1E803000`）、`DCDC_DDR`（`0x1E804000`） |
| SFF-8472 双地址从机接口 (`/dev/sfp_eeprom0..1`) | `I2C` 双地址从机（`0x1E200000`，监听 `0xA0`/`0xA2`）与 `SBS0` VPE1 共享内存（物理 `0x1F200200` / KSEG0 `0x9F200200`） |
| CPU 报文收发通道 (`ICTRLC` / `OCTRLC`) | `ICTRLC0..1`（`0x1D461000`）与 `OCTRLC`（`0x1D441000`）虚拟主机端口（`host`、`lct0`–`lct3`、`exc`、`dbg`、`dbc`） |

```mermaid
flowchart TD
    CTRL["VPE0 控制面"] -->|寄存器与表控制| DEV_ONU["GTC 0x1DC00000 / GPE 0x1D400000 / EIM 0x1D800000"]
    CTRL -->|MMIO 与 FCSI 串行总线| DEV_OPTIC["PMA 0x1DD00000 / FCSIC 0x1DD00600 / DCDC_APD 0x1E805000"]
    CTRL -->|共享内存 0x1F200200| DEV_SFP["VPE1 协处理器与 I2C 从机 0x1E200000"]
```

---

## 1. GPON 与交换数据通路控制功能族 (`/dev/onu`)

数据通路控制接口按硬件子系统划分为 8 个功能族：

| 功能族名称 | `type` (Magic) | 命令来源 | 管辖硬件模块与功能范围 |
| --- | --- | --- | --- |
| **Common** | `0x01` (1) | drv_onu_common_interface.h | 版本、寄存器与 CLI |
| **Event / FIFO** | `0x02` (2) | drv_onu_event_interface.h | 异步事件 FIFO、掩码与读取 |
| **GTC** | `0x03` (3) | drv_onu_gtc_interface.h | GTC、序列号/密码、BIP/FEC、Dying Gasp |
| **GPE** | `0x04` (4) | drv_onu_gpe_interface.h | 微码、队列、调度、计量、T-CONT、GEM、TOD、OMCI |
| **GPE Table** | `0x05` (5) | drv_onu_gpe_tables_interface.h | PE/COP 表、桥接、转发、VLAN 与 ACL |
| **PLOAM** | `0x06` (6) | drv_onu_ploam_interface.h | PLOAM 初始化、状态与消息 |
| **LAN** | `0x07` (7) | drv_onu_lan_interface.h | EIM、SerDes、GPHY、MDIO、PAUSE 与 RMON |
| **PSM** | `0x08` (8) | drv_onu_psm_interface.h | 光模块节能与唤醒 |

### 1.1 核心硬件配置操作

| 命令标识 | 方向/编码 | `type` / `nr` | 载荷大小 | 硬件配置内容 |
| --- | --- | --- | --- | --- |
| `FIO_GTC_CFG_SET` / `GET` | `_IOW` / `_IOR` | `3` / `1..2` | `sizeof(struct gtc_cfg)` | 配置 `GTC` BIP 阈值、SF/SD 门限、密码、ONU 响应超时与激光器偏移 |
| `FIO_GTC_INIT` | `_IOW` | `3` / `0` | `sizeof(struct gtc_init_data)` | 复位并初始化 `GTC` 下行与上行硬件模块 |
| `FIO_GPE_INIT` | `_IOW` | `4` / `0` | `sizeof(struct gpe_init_data)` | 装载微码、初始化 GPE |
| `FIO_GPE_CFG_SET` / `GET` | `_IOW` / `_IOR` | `4` / `1..2` | `sizeof(struct gpe_cfg)` | 配置 GPE |
| `FIO_GPE_CAPABILITY_GET` | `_IOR` | `4` / `0x61` | `sizeof(struct gpe_capability)` | 读取 GPE 能力 |
| `FIO_GPE_TCONT_SET` / `GET` | `_IOW` / `_IOWR` | `4` / `0x1C..0x1D` | 对应结构体大小 | 配置或读取 T-CONT |
| `FIO_GPE_GEM_PORT_ADD` / `SET` | `_IOWR` / `_IOW` | `4` / `0x04`, `0x5C` | `sizeof(struct gpe_gem_port)` | 配置 GEM 端口 |
| `FIO_GPE_EGRESS_QUEUE_CFG_SET` | `_IOW` | `4` / `0x09` | `sizeof(struct gpe_equeue_cfg)` | 配置出向队列 |
| `FIO_GPE_SCHEDULER_CFG_SET` | `_IOW` | `4` / `0x0E` | `sizeof(struct gpe_scheduler_cfg)` | 配置调度器 |
| `FIO_GPE_TOKEN_BUCKET_SHAPER_CFG_SET` | `_IOW` | `4` / `0x22` | `sizeof(struct gpe_token_bucket_shaper_cfg)` | 配置整形器 |
| `FIO_GPE_METER_CFG_SET` | `_IOW` | `4` / `0x12` | `sizeof(struct gpe_meter_cfg)` | 配置计量器 |
| `FIO_GPE_SHARED_BUFFER_CFG_SET` | `_IOW` | `4` / `0x53` | `sizeof(struct gpe_shared_buffer_cfg)` | 配置全局空闲段门限 |
| `FIO_GPE_OMCI_SEND` | `_IOW` | `4` / `0x24` | `sizeof(struct gpe_omci_msg)` | 通过 CPU 注入通道发送 OMCI |
| `FIO_LAN_PORT_CFG_SET` | `_IOW` | `7` / `3` | `sizeof(struct lan_port_cfg)` | 配置 UNI 端口物理模式、自协商与双工状态 |

完整 32 位值须用目标 MIPS o32 的 ioctl 宏和结构体大小生成；MIPS 的方向位编码不能套用宿主 x86 的常量。`FIO_LAN_CFG_SET` 是另一条命令（nr 1），不能与 `FIO_LAN_PORT_CFG_SET` 混淆。

例如本树 `lantiq-gpon/tests/test_onu_uapi.c` 检查 `FIO_GPE_CAPABILITY_GET == 0x401c0461`。这验证配套接口定义，不表示原厂同名命令必然同值。ONU ioctl 的 arg 还是 `fio_exchange` 包装（含载荷指针、长度和错误字段），并非直接把上表结构体地址传给 ioctl；应使用本树 dev_ctl 包装并检查系统调用与 exchange 错误。

---

## 2. 光物理层与电源控制功能族 (`/dev/optic`)

光物理层接口管理 BOSA/OMU 模拟前端、`FCSIC` 串行总线与三路 DCDC 转换器，按硬件子模块划分为 12 个功能族（`type` 编码 `200`–`211`）：

下表是当前配套 `bsp/modules/optic/include/drv_optic*_interface.h` 的 `OPTIC_*_MAGIC/MAX`，分派由 `drv_optic_ioctl.h:optic_ioctl_entry()` 实现。MAX 表示表长度，包含保留/未实现槽，并非每项均可调用成功；实际拷贝大小以各 `optic_entry` 的 size_in/size_out 为准。

| 子模块名 | `type` (Magic) | 槽位数量 (`nr`) | 管辖的硬件单元与校准环路 |
| --- | --- | --- | --- |
| `optic` | `200` (`0xC8`) | 9 (`0..8`) + CLI (`100`) | 顶层工作模式（BOSA vs OMU）、状态机周期与引脚配置 |
| `goi` | `201` (`0xC9`) | 18 (`0..17`) | GPON Optical Interface 配置、初始化状态、温度告警阈值与查找表加载 |
| `fcsi` | `202` (`0xCA`) | 3 (`0..2`) | `FCSI`（Fast Control Serial Interface）模拟前端寄存器配置与预驱动参数 |
| `mm` | `203` (`0xCB`) | 11 (`0..10`) | Measurement Module 片上 ADC 电压、电流、温度与收发光功率测量 |
| `mpd` | `204` (`0xCC`) | 4 (`0..3`) | Monitor Photodiode 背光监测二极管双环（P0 偏置环 / P1 调制环）TIA 增益、DAC 偏移与闭环参数 |
| `bert` | `205` (`0xCD`) | 11 (`0..10`) | Bit Error Rate Tester 硬件伪随机码（PRBS）发生器与误码率分析器 |
| `omu` | `206` (`0xCE`) | 10 (`0..9`) | Optical Module Unit 外置光模块模式信号检测与激光使能控制 |
| `bosa` | `207` (`0xCF`) | 22 (`0..21`) | Bi-Directional Optical Sub-Assembly 片上直驱激光器偏置电流（`Ibias`）、调制电流（`Imod`）、双环 APC 闭环与 RSSI 接收光功率 |
| `cal` | `208` (`0xD0`) | 68 (`0..67`) | 产线校准与实时温度查找表（`Laser_Ref`、`Vapd`、MPD 校准、RSSI 校准、电流/功率换算系数）读写 |
| `dcdc_apd` | `209` (`0xD1`) | 5 (`0..4`) | `DCDC_APD`（`0x1E805000`）雪崩光电二极管高压升压器目标电压与占空比控制 |
| `ldo` | `210` (`0xD2`) | 3 (`0..2`) | 片上线性稳压器（LDO）使能与状态查询 |
| `event` | `211` (`0xD3`) | 5 (`0..4`) | 光模块过温、欠温、过流、激光器老化告警事件中断状态 |

---

## 3. VPE0–VPE1 双地址 I2C 从机共享内存契约 (`0x1F200200`)

VPE1 协处理器与主控 VPE0 通过位于 `SBS0` 的固定共享内存区（物理地址 `0x1F200200`，KSEG0 虚拟地址 `0x9F200200`，总长 `0x7AC` = 1964 字节）交换 SFF-8472 双地址（`0xA0`/`0xA2`）EEPROM 数据与状态。

### 3.1 共享内存布局 (`0x1F200200`, 1964 B)

共享内存区包含两个对称的 976 字节 EEPROM 银行结构（`Bank 0` 对应从地址 `0xA0`，`Bank 1` 对应从地址 `0xA2`）及 12 字节全局控制尾：

| 字节偏移 | 字段名称 | 大小 | 硬件与协处理器交互说明 |
| --- | --- | --- | --- |
| `+0x000` | `bank[0].current_offset` | 1 B | 当前 I2C 偏移 |
| `+0x001` | `bank[0].eeprom` | 640 B | EEPROM 镜像 |
| `+0x281` | `bank[0].wp_mask` | 256 B | 逐字节写保护掩码 |
| `+0x381` | `bank[0].write_events` | 32 B | 256 位写事件 bitmap |
| `+0x3A1` | `bank[0].read_events` | 32 B | 256 位读事件 bitmap |
| `+0x3C1` | `status_flag` / `addr` / `notify_flag` | 各 1 B | 状态、从机地址与通知使能 |
| `+0x3C4` | `access_code` | 4 B | 访问码 |
| `+0x3C8` | `reserved` | 4 B | 保留 |
| `+0x3CC` | `access_mode` | 4 B | 访问模式 |
| `+0x3D0`–`+0x79F` | `bank[1]` (`0xA2` DDM 区) | 976 B | 结构与 `bank[0]` 相同，存放 SFF-8472 `0xA2` 诊断监控值、阈值、软控制位与扩展页 |
| `+0x7A0` | `sda_gpio` | 4 B | I2C SDA 绑定的 GPIO 编号（缺省 `39`） |
| `+0x7A4` | `scl_gpio` | 4 B | I2C SCL 绑定的 GPIO 编号（缺省 `40`） |
| `+0x7A8` | `processing_enabled` | 4 B | VPE1 从机事务处理总使能标志（`1` = 运行，`0` = 挂起） |

布局依据 `bsp/modules/sfp_i2c/sfp_i2c.c` 的 `struct sfp_i2c_bank` 和 `sfp_i2c_init()` 中的偏移断言。`i2c_eeprom_wr_get()` / `i2c_eeprom_rd_get()` 按位读取并清除事件；这里没有写事务计数器，不能按 32 位计数器轮询。`0xA0`/`0xA2` 是 8 位地址表示，对应总线 7 位地址 `0x50`/`0x51`。

---

## 4. CPU 虚拟端口映射 (`ICTRLC` ↔ `OCTRLC`)

GPE 的 CPU 收发通道（`ICTRLC0..1` `0x1D461000` 与 `OCTRLC` `0x1D441000`）在控制面映射为 8 个逻辑端口：

| 端口编号 (`port_num`) | 接口名称 | 硬件映射与报文收发用途 |
| --- | --- | --- |
| `0` | `host` | OMCI `IP Host Config Data`（ME 134）关联的三层协议栈接口（DHCP / TR-069 / 远程管理） |
| `1`–`4` | `lct0`–`lct3` | Local Craft Terminal 本地维护终端接口，分别绑定 UNI 端口 `0`–`3`（匹配 `CONSTANTS` 表本地 MAC 的管理流量） |
| `5` | `exc` | GPE 捕获异常报文接口（IGMP / MLD / ARP / 802.1X 等） |
| `6` / `7` | `dbg` / `dbc` | 硬件调试捕获与控制接口 |
