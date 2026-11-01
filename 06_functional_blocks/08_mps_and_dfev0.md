# 6.8 MPS 与 DFEV0

MPS 提供处理域间的消息与共享存储接口，DFEV0 属于语音前端硬件域。VPE0 与 VPE1 共享一颗 MIPS 34Kc 处理器核。

## 地址资源

| 资源 | 物理地址 | 窗口大小 |
| --- | --- | --- |
| MPS 寄存器窗口 | `0x1D004000` | `0x1000` |
| MPS 共享邮箱区 | `0x1F200000` | `0x200`（512 B） |

邮箱区位于 SBS0 地址空间。通信双方通过共享区交换消息，并约定消息格式、FIFO 布局及启动握手。

## SYS1 时钟与电源控制

SYS1 基址为 `0x1EF00000`。

| 寄存器偏移 | 名称 | MPS / DFEV0 |
| --- | --- | --- |
| `0x00` | `CLKS` | 状态：MPS bit 25，DFEV0 bit 24 |
| `0x04 / 0x08` | `CLKEN / CLKCLR` | 时钟开启/关闭，使用同一组位 |
| `0x20 / 0x24 / 0x28 / 0x2C` | `ACTS / ACT / DEACT / RBT` | 激活状态、激活、去激活、复位触发 |
| `0xB4` | `PDCFG` | 设置域去激活时的断电策略 |

`PDCFG` 的策略在域去激活时生效；`CLKS` 与 `ACTS` 分别报告时钟和激活状态。

## NTR 时钟

`SYS_GPON.VCC` 包含 `NTR8KEN`（bit 8）、`NTREN`（bit 7）及 `NTRFS`（bits 2:0），用于 NTR 时钟配置。

VPE1 的执行域与共享内存接口见 [VPE1](../03_cpu_subsystems/02_vpe1_sfp_i2c.md)。
