# 2.4 中断控制器与向量表

Falcon 的 ICU 包含 IM0–IM4 五组、每组 32 条外设输入，汇总到 MIPS CP0 的 IP2–IP6。ICU 物理基址为 `0x1F880200`，KSEG1 地址为 `0xBF880200`。

本页区分 CP0 中断输入、ICU 硬件编号（hwirq）与 Linux 分配的虚拟 IRQ。原 3.10 平台常以 `8 + 32 * k + b` 编号 ICU 的第 `k` 组第 `b` 位；移植后的 Linux irqdomain 可以分配不同的虚拟 IRQ，不能把硬件编号当作跨版本固定的 `/proc/interrupts` 行号。

## 4.1 CP0 与 ICU 级联

```mermaid
flowchart LR
    DEV["外设源状态与使能"] --> ICU["IM0–IM4，每组32位"]
    ICU --> CP0["CP0 IP2–IP6"]
    CP0 --> DISPATCH["读取IOSR并分派hwirq"]
```

| CP0 输入 | 原平台编号 | 用途 |
|---|---|---|
| IP0、IP1 | 0、1 | 软件中断；是否用于 IPI 取决于内核配置 |
| IP2–IP6 | 2–6 | IM0–IM4 级联输入 |
| IP7 | 7 | 原平台 CP0 Count/Compare 定时器中断 |

VPE1 运行独立裸机固件并不意味着原系统以 Linux SMP 的 IPI 方式交换 SFP 数据；其共享内存协议另见[多线程与 VPE1](../03_cpu_subsystems/02_vpe1_sfp_i2c.md)。

## 4.2 ICU 寄存器组

组 `k` 的物理基址为 `0x1F880200 + k * 0x28`，`k=0..4`。dump 设备树逐组提供五个 `0x28` 字节资源。

| 组 | 物理基址 | CP0 输入 | hwirq 范围 |
|---|---|---|---|
| IM0 | `0x1F880200` | IP2 | 8–39 |
| IM1 | `0x1F880228` | IP3 | 40–71 |
| IM2 | `0x1F880250` | IP4 | 72–103 |
| IM3 | `0x1F880278` | IP5 | 104–135 |
| IM4 | `0x1F8802A0` | IP6 | 136–167 |

| 组内偏移 | 名称 | 原驱动用法 |
|---|---|---|
| `0x00` | ISR | 状态；向目标位写 1 应答 |
| `0x08` | IER | 使能；读改写目标位以屏蔽/恢复 |
| `0x10` | IOSR | 读取已输出的挂起位，分派外设中断 |
| `0x18` | IRSR | 原始状态寄存器定义 |
| `0x20` | IMR | 模式寄存器定义 |

`linux-3.10.49:arch/mips/lantiq/irq.c` 的 `ltq_mask_and_ack_irq` 先清 IER 位，再向 ISR 写相同位。ICU 的应答不能代替外设内部源状态清除；具体源的应答时序由外设 ISR 决定。

## 4.3 有本地依据的外设映射

下表按 dump 的 `extracted/images/falcon-sfp.dts` 与恢复驱动列出已确认资源，不声称覆盖全部 160 条输入。未列出的中断不能按模块排列顺序猜测。原 `mod_onu.ko` 在 Ghidra 的 `onu_irq_apply_mask`（`0x0005C05C`）遍历地址 `0x000B5220` 的 8 项、每项 24 字节描述符；其首字依次为 `101, 102, 82, 84, 91, 54, 86, 92`，与下表 ONU 驱动宏一致。

| hwirq | ICU 组/位 | 来源 | 依据 |
|---|---|---|---|
| 18、19、20、21 | IM0/10–13 | I2C Last Burst、Burst、Error、Protocol | dump DT `i2c@200000` 的 `interrupt-names` |
| 22、23、24 | IM0/14–16 | SSC TX、RX、Error | dump DT `spi@100D00` 的命名与编号；DT 列表顺序为 RX、TX、ERR |
| 44–48 | IM1/4–8 | GPIO0–4 | dump DT 各 gpio 节点 |
| 54 | IM1/14 | TOD | `drv_onu_linux.c` 的 FALCON_IRQ_TOD |
| 55、56、57 | IM1/15–17 | PMA_200M、PMA_TX、PMA_RX | `drv_optic_ll_int.h`；BOSA IRQ 表使用 TX、RX |
| 82 | IM2/10 | IQM | `drv_onu_linux.c` 的 FALCON_IRQ_IQM |
| 84 | IM2/12 | TMU | 同文件 FALCON_IRQ_TMU |
| 86 | IM2/14 | LINK1 | 同文件 FALCON_IRQ_LINK1 |
| 91、92 | IM2/19–20 | CONFIG_BREAK、CONFIG | 同文件对应宏 |
| 101、102 | IM2/29–30 | GTC_DS、GTC_US | 同文件对应宏 |
| 104、105、106 | IM3/0–2 | ASC0 TX、RX、Error | dump DT `serial@100C00` |
| 112、113、114 | IM3/8–10 | ASC1 TX、RX、Error | dump DT `serial@100B00` |
| 154、155 | IM4/18–19 | MPS 两条中断资源 | dump DT `mps@4000` |

这里的模块源名不等于“已在板上启用”。例如 optic 的 OMU GPIO 中断还依赖 `gpio_to_irq`，不具有通用的固定硬件编号。GPTC 没有在该 dump DT 中声明可据以确认的通道 IRQ；不得把猜测的 126–131 当作本板已验证映射。

## 4.4 外设内部的中断源

多种外设有 IRNCR（捕获/应答）、IRNICR（注入控制）和 IRNEN（使能）一类寄存器，但偏移、读写属性、屏蔽与锁存关系须按具体模块核对。不能将一套通称强行套用到 I2C、GPIO、GTC 或其他全部模块。例如 GPIO 的中断模式由 IRNCFG 选择，IRNENSET/CLR 提供原子使能控制，详见[GPIO 寄存器表](../04_peripherals_and_io/01_pinctrl_and_gpio.md)。
