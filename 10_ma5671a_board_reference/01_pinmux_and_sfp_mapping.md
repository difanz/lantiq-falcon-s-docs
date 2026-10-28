# 10.1 引脚映射与串口模式

本页区分原厂 DTB、启动脚本实际调用与连接器推断。证据为 `extracted/images/falcon-sfp.dts`、`extracted/rootfs/etc/uci-defaults/sfp-pins-preconfig` 与 `bsp/modules/sfp_i2c/sfp_i2c.c`。没有板级原理图或导通记录，软件配置不能单独证明全部金手指到芯片的物理连线。

## GPIO 与 PADCTRL 地址

全局 GPIO 编号为 `bank * 32 + offset`。IRQ 是 DT `interrupts` 原值，并非 Linux 动态分配后的 IRQ 编号。

| Bank | GPIO 范围 | PADCTRL 物理地址 | GPIO 物理地址 | DT interrupts | 时钟域 |
| --- | --- | --- | --- | --- | --- |
| 0 | 0–31 | `0x1DB01000` | `0x1D810000` | 44 | SYS_ETH |
| 1 | 32–63 | `0x1E800400` | `0x1E800100` | 45 | SYS1 |
| 2 | 64–95 | `0x1DB02000` | `0x1D810100` | 46 | SYS_ETH |
| 3 | 96–127 | `0x1E800500` | `0x1E800200` | 47 | SYS1 |
| 4 | 128–159 | `0x1E800600` | `0x1E800300` | 48 | SYS1 |

## SFP 信号与软件绑定

| 信号 | SFP 常规 Pin | 本固件配置 | 证据与限制 |
| --- | --- | --- | --- |
| TX_Fault | 2 | GPIO 2 | 默认配置有该值，但 pin_cfg.sh 实际向 optic 下发禁用值 `255` |
| TX_Disable | 3 | GPIO 1 | `optic optic_pin_cfg_set <tx_disable> 255` 的第一参数 |
| SDA / SCL | 4 / 5 | GPIO 39 / 40 | SFP_I2C_GPIO_SDA/SCL；VPE1 从机 `0xA0/0xA2` 对应 7 位 `0x50/0x51` |
| MOD-DEF(0) | 6 | GPIO 32 | 默认 mod_def=32；脚本中主动拉低的语句被注释 |
| Rate_Select | 7 | ASC0 复用相关 | DT io32/io33 支持 ASC/GPIO；物理连线需实测确认 |
| LOS | 8 | GPIO 5 | 实际调用 `onu onu_los_pin_cfg_set <los>` |
| RD-/RD+ | 12 / 13 | SerDes 模块输出 | 标准 SFP 信号方向，GPIO 配置不能证明具体走线 |
| TD+/TD- | 18 / 19 | SerDes 模块输入 | 同上 |

GPIO 34 是 SFP I2C 驱动写保护控制。GPIO 37/38 由 `fw_env.sh` 的 `i2c-gpio-custom bus0=0,37,38,5` 建立软件 I2C **主机**总线，与 GPIO 39/40 的外部宿主从机通道不同。

## ASC0：DT 能力和实际启动行为

原厂 pinselect-asc0 有四种状态。下表照录 mux/方向，不推断金手指 UART RX/TX：

| 状态 / asc0 环境值 | io32 | io33 | pin_cfg.sh restriction_list |
| --- | --- | --- | --- |
| asc0 / 0 | ASC 组 | ASC 组 | ASC_RX ASC_TX |
| func1 / 1 | mux 1，output 0 | mux 0 | ASC_RX |
| func2 / 2 | mux 0 | mux 1，input 0 | ASC_TX |
| func3 / 3 | mux 1，output 0 | mux 1，input 0 | 空 |

这些节点没有 `lantiq,pull`；不能把 `lantiq,input=<0>` 改写成“输入上拉”。

原厂 `/etc/init.d/pin_cfg.sh` 没有向 sysfs pinselect state 写状态名，`onu_asc0_pin_cfg_set` 调用也被注释。它读取 asc0 生成 restriction list，再过滤带对应 restriction 的 UCI `config pin` 节。SFP 默认是四个匿名 pin 节，各含 name、pin，并非一个 config pins default 节。

apply_pins() 无论环境变量 tx_fault_pin 是否存在，都执行 `optic optic_pin_cfg_set $tx_disable_pin 255`，随后执行 `onu onu_los_pin_cfg_set $los_pin`。它不将四个引脚全部交给 optic，不根据 tx_fault_pin=0 释放 UART，也不主动设置 mod_def 电平。

Linux 7.3 配套 `lantiq-gpon/rootfs/etc/init.d/S63pins` 保留上述实际调用；ASC0 另需结合 S60sfp_eeprom 和 sfp_i2c 工具的 ASC0 ioctl 查看。只改变 asc0 环境变量不能证明外部串口引脚已按 DT 状态切换。
