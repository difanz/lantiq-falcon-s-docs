# Lantiq Falcon (PEB/PEF 98035)

Lantiq Falcon（PEB 98035 / PEF 98035）GPON SoC 集成 MIPS 34Kc 处理器、封包处理引擎、光收发控制器、以太网接口和片上外设。

| 硬件执行域 | 核心架构 | 地址空间 / 接口 | 职责 |
|---|---|---|---|
| VPE0 | MIPS 34Kc VPE0（大端 MIPS32r2） | KSEG0/KSEG1，外设总线 `0x1D000000`–`0x1F8803FF` | 主控运算、中断处理与外设控制 |
| VPE1 | MIPS 34Kc VPE1（MT ASE 共享核） | 硬件线程上下文，共享物理地址空间 | 并行任务执行 |
| SCE (GPE) | 6 个 PE + 8 个 COP（指令与寄存器宽度见第 5 章） | SBS2 总线 `0x1D400000`–`0x1D7000FF` | GPON/Ethernet 线速报文解析、流表查找（FID/FWD/TAG/TBL/MSF/EXT）与头部重写 |
| GPHY0 / GPHY1 | 2 颗嵌入式 MCS-51 (8051) | 代码重映射至 SBS0 RAM 或片上 ROM | 千兆/百兆以太网 PHY 链路训练、自协商与内部寄存器管理 |

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
:caption: 数据流与控制流

08_data_flow/index
09_control_flow/index
```

```{toctree}
:maxdepth: 2
:caption: 板级附录

10_ma5671a_board_reference/index
```
