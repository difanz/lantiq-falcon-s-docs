# 4.1 引脚复用 (PADCTRL) 与 GPIO 控制器

Falcon 使用 5 个、每组 32 位的 GPIO 编号空间。编号空间不等于封装实际引出的引脚数量；应读取 PADCTRL 的 `AVAIL`，并结合板级连接确认可用性。

本页按原固件对应的 Linux 3.10.49 `drivers/pinctrl/pinctrl-falcon.c`、`drivers/gpio/gpio-falcon.c` 和 dump 设备树核对。GPIO 的输出与中断访问还可在 `kernel.elf` 的 `falcon_gpio_direction_input`（`0x800DCF1C`）、`falcon_gpio_direction_output`（`0x800DCF34`）、`falcon_gpio_set`（`0x800DD7E4`）、`falcon_gpio_irq_type`（`0x800DD180`）核对。下列地址均为物理地址。

## 1.1 端口与控制域

| 端口 | 全局编号空间 | PADCTRL | GPIO | 控制域 | PADCTRL / GPIO 门控位 | 父中断 |
|---|---|---|---|---|---|---|
| 0 | 0–31 | `0x1DB01000` | `0x1D810000` | SYS_ETH | 20 / 16 | IRQ 44 |
| 1 | 32–63 | `0x1E800400` | `0x1E800100` | SYS1 | 20 / 16 | IRQ 45 |
| 2 | 64–95 | `0x1DB02000` | `0x1D810100` | SYS_ETH | 21 / 17 | IRQ 46 |
| 3 | 96–127 | `0x1E800500` | `0x1E800200` | SYS1 | 21 / 17 | IRQ 47 |
| 4 | 128–159 | `0x1E800600` | `0x1E800300` | SYS1 | 22 / 18 | IRQ 48 |

PADCTRL 与 GPIO 是两个独立模块，访问前分别激活其时钟。父中断汇总组内请求；Linux GPIO 子中断编号由 irqdomain 创建，不是直接用 `44 + 引脚编号` 计算。

## 1.2 PADCTRL 寄存器

| 偏移 | 寄存器 | 已核实的用法 |
|---|---|---|
| `4 * p`，`p=0..31` | MUX(p) | 每引脚一个字，复用选择值 0–3 |
| `0x80` | PUEN | 按位使能上拉 |
| `0x84` | PDEN | 按位使能下拉 |
| `0x88` | SRC | 每引脚一位压摆率选择 |
| `0x8C` | DCC | 每引脚一位驱动强度选择；不是每引脚两位的四档 mA 编码 |
| `0xF0` | AVAIL | 封装可用引脚位图；不是 `0x9C` |

旧驱动没有定义 `0x98` 的 PADCTRL 开漏控制寄存器，也未给 DCC 两档对应的具体电流值。本页不为这些地址或电流值补造定义。

## 1.3 原驱动支持的复用矩阵

下表列出 `falcon_mfp[]` 中有依据的条目；`—` 表示该表未提供该功能。选择值 1 为 GPIO。该软件表不是所有封装、所有焊盘的完整硬件复用规格。

| 全局 GPIO | MUX0 | MUX1 | MUX2 | MUX3 |
|---|---|---|---|---|
| 0、6 | RST | GPIO | — | — |
| 1–3 | GPIO | GPIO | — | — |
| 4 | NTR | GPIO | — | — |
| 5 | NTR | GPIO | PPS | — |
| 7–8 | MDIO | GPIO | — | — |
| 9–14 | LED | GPIO | — | — |
| 32–33 | ASC0 | GPIO | — | — |
| 34–36 | SPI | GPIO | — | — |
| 37–38 | SPI CS0 / CS1 | GPIO | — | — |
| 39–40 | I2C | GPIO | — | — |
| 41 | HOSTIF | GPIO | HOSTIF | JTAG |
| 42 | HOSTIF | GPIO | HOSTIF | — |
| 43 | SLIC | GPIO | — | — |
| 44–45 | SLIC | GPIO | PCM | ASC1 |
| 64–87 | MII | GPIO | — | — |
| 88 | PHY | GPIO | — | — |

因此 I2C 组为 GPIO39/40，ASC1 为 GPIO44/45 的 MUX3；不能将 GPIO34/35 写成 I2C，也不能将 GPIO9–12 写成 ASC1。Port 3/4 的完整复用功能不能由地址窗口推导。MA5671A 的具体接线另见[板级引脚映射](../10_ma5671a_board_reference/01_pinmux_and_sfp_mapping.md)。

## 1.4 GPIO 寄存器与中断

| 偏移 | 寄存器 | 行为 |
|---|---|---|
| `0x00` | OUT | 输出数据 |
| `0x04` | IN | 输入采样 |
| `0x08` | DIR | 1=输出、0=输入 |
| `0x18` | EXINTCR0 | 极性选择：0=上升沿/高电平，1=下降沿/低电平 |
| `0x1C` | EXINTCR1 | 双边沿选择，见下表 |
| `0x20` | IRNCR | 捕获状态，写 1 应答 |
| `0x2C` | IRNCFG | 0=边沿，1=电平 |
| `0x30` | IRNRNSET | 写 1 使能引脚中断 |
| `0x34` | IRNENCLR | 写 1 屏蔽引脚中断 |
| `0x40` | OUTSET | 写 1 置高输出位 |
| `0x44` | OUTCLR | 写 1 清低输出位 |
| `0x48` | DIRSET | 写 1 设为输出 |
| `0x4C` | DIRCLR | 写 1 设为输入 |

输出方向切换先通过 OUTSET/OUTCLR 设置电平，再写 DIRSET，避免输出使能后才修改电平。原子置位/清零可避免不同位的读改写丢失；这不等于整个 GPIO 操作序列不需要同步。

| IRNCFG[p] | EXINTCR0[p] | EXINTCR1[p] | 原驱动配置的触发模式 |
|---|---|---|---|
| 0 | 0 | 0 | 上升沿 |
| 0 | 1 | 0 | 下降沿 |
| 0 | 0 | 1 | 双边沿 |
| 1 | 0 | 0 | 高电平 |
| 1 | 1 | 0 | 低电平 |

`falcon_gpio_irq_type` 同时将目标引脚切为输入。中断处理读取 IRNCR、分派组内已挂起位；屏蔽和应答分别写 IRNENCLR 与 IRNCR。
