# Lantiq Falcon (PEB/PEF 98035)

Lantiq Falcon（PEB 98035 / PEF 98035）GPON SoC 硬件架构、寄存器映射、片上外设、微码协处理器及数据/控制通路技术参考手册。

| 硬件执行域 | 核心架构 | 地址空间 / 接口 | 职责 |
|---|---|---|---|
| VPE0 | MIPS 34Kc VPE0（大端 MIPS32r2） | KSEG0/KSEG1，外设总线 `0x1D000000`–`0x1F8803FF` | 主控系统、GPON OMCI/PLOAM 控制面与光路校准 |
| VPE1 | MIPS 34Kc VPE1（MT ASE 共享核） | 独立硬件线程 TC1，共享内存 `0x1F200200` | SFP I2C 双地址从机（`0xA0`/`0xA2`）实时响应 |
| SCE (GPE) | 6 个 PE + 8 个 COP（指令与寄存器宽度见第 5 章） | SBS2 总线 `0x1D400000`–`0x1D7000FF` | GPON/Ethernet 线速报文解析、流表查找（FID/FWD/TAG/TBL/MSF/EXT）与头部重写 |
| GPHY0 / GPHY1 | 2 颗嵌入式 MCS-51 (8051) | 代码重映射至 SBS0 RAM `0x1F204000` 或片上 ROM | 千兆/百兆以太网 PHY 链路训练、自协商与内部寄存器管理 |

本手册区分芯片级能力、原固件实现与 MA5671A 板级连接。原固件基线为 image0 的 Linux 3.10.49 / SFP 7.5.3；恢复源码及 Linux 7.3 移植是对照材料，不构成硬件运行验证。寄存器窗口也不意味着整段空间可供通用内存分配。

```{toctree}
:maxdepth: 2
:caption: 架构与外设

01_overview/index
02_system_architecture/index
03_cpu_subsystems/index
04_peripherals_and_io/index
```

```{toctree}
:maxdepth: 2
:caption: 协处理器与硬件模块

05_coprocessors/index
06_functional_blocks/index
07_phy_and_mac/index
```

```{toctree}
:maxdepth: 2
:caption: 数据流、控制流与板级附录

08_data_flow/index
09_control_flow/index
10_ma5671a_board_reference/index
```
