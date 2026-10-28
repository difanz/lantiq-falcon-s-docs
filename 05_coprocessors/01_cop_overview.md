# 5.1 SCE / GPE 组成与时钟

Lantiq Falcon（PEB/PEF 98035）片上包含四套独立执行域。GPON 数据通路的报文分类、硬件查表与千兆以太网 PHY 控制分别由专用硬件处理引擎与片上微控制器执行，独立于主核 MIPS 34Kc VPE0 的指令流。

| 执行域 | 处理器核心 / 指令集 | 代码存储位置 | 硬件职责 |
| --- | --- | --- | --- |
| VPE0 | MIPS 34Kc VPE0（大端 MIPS32r2） | 外部 DDR（`0x80002000`） | 主控操作系统、控制面协议栈与硬件配置管理 |
| VPE1 | MIPS 34Kc VPE1（大端 MIPS32r2 + MT ASE） | 独立保留内存窗口（`sfp_i2c_vpe.bin`） | SFP 金手指侧 I2C 从机（A0h/A2h EEPROM）实时响应 |
| SCE (GPE) | 6 颗 64 位 PE + 8 个 16 位 COP | PE 内部代码 RAM（`falcon_gpe_fw.bin`）、COP 内部 CRAM（`tse0.bin`–`tse5.bin`） | GPON 与以太网数据面报文解析、分类、表查找与转发修改 |
| GPHY0 / GPHY1 | 2 颗片上 MCS-51 (8051) | SBS0 RAM（`0x1F204000`，`phy11g.bin`）或片上 ROM | 双路千兆以太网 PHY 链路自协商、物理层训练与内部寄存器控制 |

## 1. SCE / GPE 硬件资源规格

GPON Packet Engine（GPE）内部的分类与微码处理子系统称为 Shared Classification Engine（SCE）。其硬件资源规格如下：

| 资源项 | 硬件规格 | 说明 |
| --- | --- | --- |
| PE 数量 | 6 颗（PE0–PE5） | 全选位掩码 `0x3F` |
| 每颗 PE 硬件线程数 | 8 | 6 颗 PE 共 48 个 PE 硬件线程 |
| 总线程资源宏 | 56 | `ONU_GPE_NUMBER_OF_THREADS`；与 `6 × 8 = 48` 的差额未解释，不能据此推导物理线程或信号槽位 |
| 每颗 PE 代码存储器 | `0x4000` 字节（16 KiB） | 2048 条（2.0 K）64 位指令 |
| 每颗 PE 数据存储器 | `0x3000` 字节（12 KiB） | 1536 个（1.5 K）64 位数据字 |
| PE 主机接口缓冲 | 8 个 32 位字 | 用于主机与 PE 寄存器窗口的数据交换 |
| PE 消息缓冲 | 16 个 32 位字（64 字节） | 对应 1 个 SSB（Shared Segment Buffer）内存段 |
| COP 协处理器总数 | 8 个（COP0–COP7） | `SYS_GPE` 提供 8 路独立时钟与复位门控 |
| 可编程微码 COP 数量 | 6 个（COP0–COP5） | 装载 `tse0.bin`–`tse5.bin` 表搜索微码 |
| LLT 容量 | `0x4800` 项 | Logical Link Table，空指针编码为 `0x7FFF` |

## 2. SBS2 总线上的 GPE 硬件模块映射

GPE 全部硬件模块挂载在 SBS2 系统总线（物理地址 `0x1D000000`–`0x1DFFFFFF`）上，通过 MIPS `KSEG1`（`0xA0000000` + 物理地址）非缓存窗口访问：

| 硬件模块 | 物理基址 | 窗口长度 | 硬件功能说明 |
| --- | --- | --- | --- |
| `GPEARB` | `0x1D400100` | `0x100` | TDM 仲裁器，由 16 个端口号寄存器分配访问时隙并统计下行访问次数 |
| `TMU` | `0x1D404000` | `0x1000` | Traffic Management Unit：全局队列调度控制与建在 PPL 上的 PDU 空闲指针表 |
| `IQM` | `0x1D410000` | `0x10000` | Ingress Queue Manager：入队队列配置与队列状态表 |
| `OCTRLG` | `0x1D420000` | `0x10000` | 出口侧全局控制（Egress Port、T-CONT、GTC egress FIFO） |
| `OCTRLL0`–`OCTRLL3` | `0x1D440000`–`0x1D440300` | 各 `0x100` | 出口链路 0–3 控制器 |
| `OCTRLC` | `0x1D441000` | `0x100` | 出口通道控制 |
| `ICTRLG` | `0x1D450000` | `0x10000` | 入口侧全局控制（DMAW 配置、重组超时、PDU 长度上限、接收字节计数） |
| `ICTRLL0`–`ICTRLL3` | `0x1D460000`–`0x1D460600` | 各 `0x200` | 入口链路 0–3 控制器 |
| `ICTRLC0`–`ICTRLC1` | `0x1D461000`–`0x1D461100` | 各 `0x100` | 入口通道控制 0–1 |
| `FSQM` | `0x1D500000` | `0x100000` | Free Segment Queue Manager：输入/输出空闲段队列、阈值及按 LSA 执行 ALLOC/FREE 的消息队列 |
| `PCTRL` | `0x1D600000` | `0x200` | Processor Control：按 Virtual Machine 控制线程启停、单步、断点、线程中断与全局唤醒信号 |
| `LINK0` | `0x1D600200` | `0x100` | 片上互联网络接口 0 |
| `LINK1` | `0x1D600300` | `0x100` | 片上互联网络接口 1 |
| `LINK2` | `0x1D600400` | `0x100` | 片上互联网络接口 2（主机至 COP 协处理器的命令与响应 FIFO 通道） |
| `DISP` | `0x1D600500` | `0x100` | Dispatcher：汇总各 VM 线程的接收请求并通知 IQM 派发报文 |
| `MERGE` | `0x1D600600` | `0x100` | Merger：仲裁并汇聚各 PE 线程发出的报文发送请求 |
| `TBM` | `0x1D600700` | `0x100` | Token Bucket Meter：硬件令牌桶计量表寄存器窗口 |
| `PE0`–`PE5` | `0x1D610000`–`0x1D660000` | 各 `0x10000` | PE0–PE5 各自的 64 KiB 寄存器与程序存储窗口 |
| `SYS_GPE` | `0x1D700000` | `0x100` | GPE 子系统时钟门控、模块激活、复位与硬件休眠控制 |

## 3. GPE 625 MHz 核心时钟硬件使能序列

3.10.49 基线的 `falcon_gpe_enable()` 注释将初始化目标称为 625 MHz；这不是本板时钟测量，也未证明每个 COP 的独立执行频率。主时钟由 `SYS1` 控制块（物理基址 `0x1EF00000`）偏移 `0xBC` 的 `SYS1_INFRAC` 寄存器控制，硬件上电使能流程如下：

1. 读取 `SYS1_INFRAC`（`0x1EF000BC`）的 bit 25；若已为 1，表明 GPE 核心时钟已处于开启状态。
2. 若 bit 25 为 0，先读取芯片状态块偏移 `0x40`（物理地址 `0x1E802040`，`CHIPCONF`），返回值被丢弃；不能由这次读取推断熔丝的具体内容。
3. 将 `SYS1_INFRAC` 的 bit 27:25 修改为 `0b010`（清除 `7 << 25`，置位 bit 26），随后执行 1 µs 软件延迟。
4. 置位 `SYS1_INFRAC` 的 bit 25（`1 << 25`），再执行 1 µs 软件延迟；函数没有验证锁定或读回实际频率。

## 4. `SYS_GPE` 时钟门控与复位激活寄存器 (`0x1D700000`)

`SYS_GPE` 为 GPE 内部各功能模块提供独立的时钟门控与复位控制：

| 字节偏移 | 寄存器名 | 访问属性 | 硬件行为 |
| --- | --- | --- | --- |
| `0x00` | `CLKS` | RO | 反映各硬件域当前的实际时钟开启状态 |
| `0x04` | `CLKEN` | WO | 写 1 开启对应硬件域的时钟 |
| `0x08` | `CLKCLR` | WO | 写 1 关断对应硬件域的时钟 |
| `0x20` | `ACTS` | RO | 反映各硬件域当前的激活（非复位）状态 |
| `0x24` | `ACT` | WO | 写 1 激活对应硬件域并解除复位 |
| `0x28` | `DEACT` | WO | 写 1 将对应硬件域置入复位停用态（硬件自动强制关断其时钟） |
| `0x2C` | `RBT` | WO | 写 1 对选中硬件域触发一次复位脉冲 |
| `0xB4` | `PDCFG` | R/W | 配置模块停用（deactivation）时是否移除该域电源 |
| `0xB8` | `SSCFG` | R/W | 硬件自动休眠/唤醒触发源选择 |
| `0xBC` | `SST` | R/W | 硬件休眠定时器 |
| `0xC0`–`0xC8` | `SDS` / `SDSET` / `SDCLR` | RO / WO | 硬件休眠请求生效时自动关断时钟的目标域掩码 |

`CLKS`、`CLKEN`、`CLKCLR`、`ACTS`、`ACT`、`DEACT`、`RBT` 共用同一套位域映射：

| 位 | 掩码 | 域名 | 所属硬件模块 |
| --- | --- | --- | --- |
| 31–24 | `0xFF000000` | `COP7` … `COP0` | SCE 表搜索协处理器 7 … 0 |
| 23–22 | — | — | 保留 |
| 21–16 | `0x003F0000` | `PE5` … `PE0` | SCE 处理单元 5 … 0 |
| 15–14 | — | — | 保留 |
| 13 | `0x00002000` | `ARB` | GPEARB 总线仲裁器 |
| 12 | `0x00001000` | `FSQM` | 空闲段队列管理器 |
| 11 | `0x00000800` | `TMU` | 流量管理单元 |
| 10 | `0x00000400` | `MRG` | MERGE 发送汇聚器 |
| 9 | `0x00000200` | `DISP` | DISP 任务分发器 |
| 8 | `0x00000100` | `IQM` | 入队管理器 |
| 7 | `0x00000080` | `CPUE` | CPU Egress 接口逻辑 |
| 6 | `0x00000040` | `CPUI` | CPU Ingress 接口逻辑 |
| 5 | `0x00000020` | `GPONE` | GPON (GTC) Egress 接口逻辑 |
| 4 | `0x00000010` | `GPONI` | GPON (GTC) Ingress 接口逻辑 |
| 3–0 | `0x0000000F` | `LAN3` … `LAN0` | LAN3 … LAN0 接口逻辑 |

SCE 与 COP 的硬件上电初始化顺序如下：

1. 向 `SYS_GPE.CLKEN` 与 `SYS_GPE.ACT` 置位 `PE0`–`PE5`（`0x003F0000`）、`MRG`（`0x00000400`）与 `DISP`（`0x00000200`）。
2. 向 `MERGE.CTRL` 置位 `INITSTART` 启动汇聚器内部 RAM 自检清零，轮询 `MERGE.CTRL.INITDONE` 置 1。
3. 向 `SYS_GPE.RBT` 写入 `0xFF000000` 复位 `COP7`–`COP0`，再通过 `CLKEN` 与 `ACT` 置位 `0xFF000000` 开启全部 8 个 COP 时钟，通过 `LINK2` 将微码与表配置装入 COP0–COP5。
4. 按序复位各颗 PE（`SYS_GPE.ACT` / `RBT` bit `16 + idx`），向每颗 PE 的代码与数据窗口装入 64 位固件，最后在 `PCTRL` 中使能线程中断与虚拟机调度。

## 本地依据与适用范围

`bsp/modules/onu/include/drv_onu_resource_gpe.h`、`drv_onu_reg_base.h`、`drv_onu_reg_sys_gpe.h`；时钟流程取 `kernel` 的 `linux-3.10.49:arch/mips/lantiq/falcon/sysctrl.c:falcon_gpe_enable()`。

上述 `bsp/` 路径按本次审计的 `linux-3.10.49` 基线读取，属于源码/静态固件证据；不将 `linux-7.3` 移植结果或未上板验证的解释当作原固件运行事实。
