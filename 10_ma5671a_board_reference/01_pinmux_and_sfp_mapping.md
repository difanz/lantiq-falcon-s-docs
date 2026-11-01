# 10.1 引脚映射与串口模式

MA5671A 的 GPIO、SFP 控制信号与串口复用配置如下。

## GPIO 与 PADCTRL 地址

全局 GPIO 编号为 `bank * 32 + offset`。表中的 IRQ 为 DT `interrupts` 单元值。

| Bank | GPIO 范围 | PADCTRL 物理地址 | GPIO 物理地址 | DT interrupts | 时钟域 |
| --- | --- | --- | --- | --- | --- |
| 0 | 0–31 | `0x1DB01000` | `0x1D810000` | 44 | SYS_ETH |
| 1 | 32–63 | `0x1E800400` | `0x1E800100` | 45 | SYS1 |
| 2 | 64–95 | `0x1DB02000` | `0x1D810100` | 46 | SYS_ETH |
| 3 | 96–127 | `0x1E800500` | `0x1E800200` | 47 | SYS1 |
| 4 | 128–159 | `0x1E800600` | `0x1E800300` | 48 | SYS1 |

## SFP 信号与软件绑定

| 信号 | SFP 常规 Pin | 设备配置 | 使用限制 |
| --- | --- | --- | --- |
| TX_Fault | 2 | GPIO 2 | 默认映射为 GPIO 2；启动配置未使能输出 |
| TX_Disable | 3 | GPIO 1 | 宿主侧激光关闭控制输入 |
| SDA / SCL | 4 / 5 | GPIO 39 / 40 | VPE1 从机 `0xA0/0xA2` 对应 7 位 `0x50/0x51` |
| MOD-DEF(0) | 6 | GPIO 32 | 映射为 GPIO 32；启动输出状态未确认 |
| Rate_Select | 7 | ASC0 复用相关 | DT io32/io33 支持 ASC/GPIO；物理连线需实测确认 |
| LOS | 8 | GPIO 5 | 由 GPON 控制域管理 |
| RD-/RD+ | 12 / 13 | SerDes 模块输出 | 标准 SFP 接收信号 |
| TD+/TD- | 18 / 19 | SerDes 模块输入 | 同上 |

GPIO 34 用于 SFP I2C 服务的写保护控制。GPIO 37/38 用于板内 I2C 主机通道，与 GPIO 39/40 面向外部宿主的 I2C 从机通道不同。

## ASC0：DT 能力和实际启动行为

ASC0 有四种引脚复用组合，mux 与方向配置如下：

| 状态 / asc0 环境值 | io32 | io33 | 配置限制标签 |
| --- | --- | --- | --- |
| asc0 / 0 | ASC 组 | ASC 组 | ASC_RX ASC_TX |
| func1 / 1 | mux 1，output 0 | mux 0 | ASC_RX |
| func2 / 2 | mux 0 | mux 1，input 0 | ASC_TX |
| func3 / 3 | mux 1，output 0 | mux 1，input 0 | 空 |

表中的 input 0 表示输入方向，上下拉由 PADCTRL 单独配置。

asc0 环境项选择复用组合，配置限制标签协调串口引脚的使用。TX_Fault、TX_Disable、LOS 和模块在位指示分别配置。

串口与 SFP 控制功能复用引脚。切换时需确认引脚方向、电压、上下拉和当前驱动状态。
