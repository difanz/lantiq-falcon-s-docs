# 6.8 MPS 与 DFEV0：硬件资源及本板使用边界

Falcon 的 VPE0 与 VPE1 是同一颗 MIPS 34Kc 上的两个虚拟处理单元，不是两颗独立 CPU 核。本机 VPE0 运行 Linux，VPE1 装载 SFP I2C 从机固件。MPS 与 DFEV0 的地址/时钟资源存在，不代表本板正在运行语音业务，也不证明 SFP I2C 固件使用语音邮箱协议。

## 本机设备树能够确认的资源

以下取自原始镜像导出的 `extracted/images/falcon-sfp.dts`，地址已按父总线 `ranges` 换成物理地址：

| 资源 | 物理地址 / 大小 | 可确认的属性 |
| --- | --- | --- |
| `mps@4000` | `0x1D004000 / 0x1000` | compatible 同时列出 `lantiq,mps-falcon` 与 `lantiq,mps-xrx100` |
| MPS 中断 | DT cells `0x9A`、`0x9B`（154、155） | 节点只发布这两路；不能由此宣称全部语音/信号量中断的用途 |
| `mpsmbx@200000` | `0x1F200000 / 0x200` | MPS 的 `lantiq,mbx` phandle 指向这个 512 B 共享区 |

设备树资源声明不提供 FIFO 数据结构、消息位域或 BootROM 执行轨迹。尤其不能因为第二个 compatible 含 `xrx100` 就把 XWAY 的 `MPS_CHIPID (+0x344)` 当作 Falcon 芯片识别寄存器：Falcon 平台代码使用状态块 `0x1E80200C` 读取 CHIPID。

## SYS1 时钟与去激活电源策略

`bsp/modules/onu/drv_onu_reg_sys1.h` 给出以下定义，SYS1 基址为 `0x1EF00000`：

| 寄存器偏移 | 名称 | MPS / DFEV0 |
| --- | --- | --- |
| `0x00` | `CLKS` | 状态：MPS bit 25，DFEV0 bit 24 |
| `0x04 / 0x08` | `CLKEN / CLKCLR` | 时钟开启/关闭，使用同一组位 |
| `0x20 / 0x24 / 0x28 / 0x2C` | `ACTS / ACT / DEACT / RBT` | 激活状态、激活、去激活、复位触发 |
| `0xB4` | `PDCFG` | 设置域去激活时是否切断电源；不是立即关断命令 |

`SYS1 + 0x40` 是 `CPU0CC`，不是 `PDCFG`。没有本机运行时读回证据时，不把 DFEV0 的断电状态写成已验证板级事实。

## 共享区中已见的软件写入

3.10.49 基线的 `kernel/arch/mips/lantiq/falcon/reset.c:machine_restart()` 写入：

| 物理地址 | 软件写入值 | 源码用途 |
| --- | --- | --- |
| `0x1F200020` | `0x4C545100` | reboot magic 1 |
| `0x1F200024` | `0x0051544C` | reboot magic 2 |
| `0x1F200000` | `0` | 清零 Bootreg RVEC |

之后配置看门狗触发重启。这证明 Linux 写入约定；没有 BootROM dump/调用轨迹，不能补写“ROM 检查魔数后跳到 ErrorEPC”或“写 CPU1_BOOT_SIZE 即释放 VPE1”的完整协议。SFP I2C 的真实启动链应沿 `mod_sfp_i2c.ko → vpe1_sw_start` 核对，见 [VPE1 SFP I2C](../03_cpu_subsystems/02_vpe1_sfp_i2c.md)。

## NTR 与语音前端的边界

本地 `bsp/modules/optic/drv_optic_ll_sys_gpon.c` 和 `drv_optic_reg_sys_gpon.h` 提供 `SYS_GPON.VCC` 的 `NTR8KEN`（bit 8）、`NTREN`（bit 7）及 `NTRFS`（bits 2:0）。PMA 的 DLL 复位/断电位也可在光学 PLL 驱动中看到；这些定义不足以证明本板存在外接 SLIC、PCM/ZSI 布线或正在工作的语音 DSP。

本页不提供未验证的 MPS 内部寄存器表、语音 FIFO 布局和 ROM 解密入口。继续分析需要原始 MPS 驱动/ROM 或目标二进制交叉引用；移植树的符号与其他 Lantiq 系列的相似布局不能代替这项证据。
