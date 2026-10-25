# Lantiq Falcon (PEB/PEF 98035)

Lantiq Falcon（PEB 98035 / PEF 98035）GPON SoC 硬件架构、寄存器映射、片上外设、微码协处理器及数据/控制通路技术参考手册。

| 硬件执行域 | 核心架构 | 地址空间 / 接口 | 职责 |
|---|---|---|---|
| VPE0 | MIPS 34Kc VPE0（大端 MIPS32r2） | KSEG0/KSEG1，外设总线 `0x1D000000`–`0x1F8803FF` | 主控系统、GPON OMCI/PLOAM 控制面与光路校准 |
| VPE1 | MIPS 34Kc VPE1（MT ASE 共享核） | 独立硬件线程 TC1，共享内存 `0x1F200200` | SFP I2C 双地址从机（`0xA0`/`0xA2`）实时响应 |
| SCE (GPE) | 6 颗 64 位 PE + 8 个 16 位 COP | SBS2 总线 `0x1D400000`–`0x1D7000FF` | GPON/Ethernet 线速报文解析、流表查找（FID/FWD/TAG/TBL/MSF/EXT）与头部重写 |
| GPHY0 / GPHY1 | 2 颗嵌入式 MCS-51 (8051) | 代码重映射至 SBS0 RAM `0x1F204000` 或片上 ROM | 千兆/百兆以太网 PHY 链路训练、自协商与内部寄存器管理 |

## 目录

### [1. 芯片概述与顶层架构](01_overview/README.md)
- [1.1 芯片定位与产品形态](01_overview/01_introduction.md)
- [1.2 顶层架构与处理子系统](01_overview/02_chip_architecture.md)

### [2. 系统架构与全局基础设施](02_system_architecture/README.md)
- [2.1 物理地址映射与总线拓扑](02_system_architecture/01_memory_map.md)
- [2.2 系统控制与状态寄存器](02_system_architecture/02_registers_summary.md)
- [2.3 时钟树、电源门控与复位](02_system_architecture/03_clock_and_reset.md)
- [2.4 中断控制器与向量表](02_system_architecture/04_interrupt_system.md)

### [3. MIPS 34Kc 处理器与多线程子系统](03_cpu_subsystems/README.md)
- [3.1 MIPS 34Kc 核心架构与 VPE0 配置](03_cpu_subsystems/01_vpe0_host_linux.md)
- [3.2 MT ASE 硬件多线程、VPE1 启动与共享内存](03_cpu_subsystems/02_vpe1_sfp_i2c.md)

### [4. 外设控制器与 I/O 接口](04_peripherals_and_io/README.md)
- [4.1 引脚复用 (PADCTRL) 与 GPIO 控制器](04_peripherals_and_io/01_pinctrl_and_gpio.md)
- [4.2 串行通信总线：ASC UART、I2C 与 SSC SPI](04_peripherals_and_io/02_serial_and_buses.md)
- [4.3 通用定时器 (GPTC) 与硬件看门狗 (WDT)](04_peripherals_and_io/03_timers_and_wdt.md)
- [4.4 外部总线单元 (EBU) 与串行闪存状态机 (SFSM)](04_peripherals_and_io/04_flash_and_storage.md)
- [4.5 模数与数模转换器（ADC 与 DAC）](04_peripherals_and_io/05_adc_and_dac.md)

### [5. 协处理器与微码架构](05_coprocessors/README.md)
- [5.1 SCE / GPE 组成与时钟](05_coprocessors/01_cop_overview.md)
- [5.2 PE 微架构、虚拟机与 PCTRL](05_coprocessors/02_sce_pe_architecture.md)
- [5.3 PE 64 位指令、寄存器与调试接口](05_coprocessors/03_sce_pe_isa.md)
- [5.4 COP 表搜索协处理器与表结构](05_coprocessors/04_tse_cop_architecture.md)
- [5.5 SCE 硬件功能块详解（FID、FWD、TAG、TBL、MSF、EXT、TBM 与 PE 局部表）](05_coprocessors/05_sce_function_blocks.md)
- [5.6 COP 16 位指令集](05_coprocessors/06_tse_cop_isa.md)
- [5.7 TSE 微码容器与加载器](05_coprocessors/07_tse_firmware_format.md)
- [5.8 TSE 微码固件反汇编逐行详解（`tse0.s` – `tse5.s`）](05_coprocessors/08_tse_firmware_disassembly.md)
- [5.9 GPHY 8051 协处理器架构与中断](05_coprocessors/09_gphy_8051_coprocessor.md)

### [6. 数据通路硬件模块](06_functional_blocks/README.md)
- [6.1 GTC：GPON 传输汇聚](06_functional_blocks/01_gtc_mac.md)
- [6.2 FSQM、SSB0 与 LLT](06_functional_blocks/02_fsqm_and_llt.md)
- [6.3 IQM 入队管理](06_functional_blocks/03_iqm_and_queues.md)
- [6.4 TMU 与 TBM](06_functional_blocks/04_tmu_and_scheduler.md)
- [6.5 DISP 与 MERGE](06_functional_blocks/05_disp_and_merge.md)
- [6.6 TOD 时间同步](06_functional_blocks/06_tod_sync.md)
- [6.7 片上 DC/DC（Core、DDR、APD）](06_functional_blocks/07_dcdc_converters.md)
- [6.8 多处理器子系统（MPS）与语音数字前端（DFEV0）](06_functional_blocks/08_mps_and_dfev0.md)

### [7. PHY 与 MAC 子系统](07_phy_and_mac/README.md)
- [7.1 PMA 与 FCSI 总线](07_phy_and_mac/01_optical_frontend_fcsi.md)
- [7.2 BOSA 收发器控制](07_phy_and_mac/02_bosa_and_laser_control.md)
- [7.3 光学校准表与 DDM](07_phy_and_mac/03_laser_calibration.md)
- [7.4 EIM、SGMII 与 SXGMII](07_phy_and_mac/04_ethernet_mac_and_serdes.md)
- [7.5 片上 PHY11G](07_phy_and_mac/05_gphy_dual_gigabit.md)

### [8. 数据流与表操作](08_data_flow/README.md)
- [8.1 下行接收路径](08_data_flow/01_rx_datapath.md)
- [8.2 上行发送路径](08_data_flow/02_tx_datapath.md)
- [8.3 GPE 表接口与 FID 转发](08_data_flow/03_table_engine_and_rules.md)
- [8.4 Extended VLAN、ACL 与组播](08_data_flow/04_vlan_and_qos_processing.md)
- [8.5 硬件快转闭环、GEM 封装信封、CPU 流量监听与 LCT 管理接口](08_data_flow/05_cpu_tap_and_mgmt_path.md)

### [9. 控制流与协议交互](09_control_flow/README.md)
- [9.1 PLOAM 状态机](09_control_flow/01_ploam_statemachine.md)
- [9.2 OMCI 与 MIB](09_control_flow/02_omci_subsystem.md)
- [9.3 硬件控制域与 VPE1 双地址从机共享内存](09_control_flow/03_driver_ioctl_interfaces.md)
- [9.4 硬件初始化序列、光路闭环校准与 DDM 刷新](09_control_flow/04_userspace_control_tools.md)

### [10. 附录：MA5671A 板级定制](10_ma5671a_board_reference/README.md)
- [10.1 引脚映射与串口模式](10_ma5671a_board_reference/01_pinmux_and_sfp_mapping.md)
- [10.2 falcon-sfp.dts 与启动脚本](10_ma5671a_board_reference/02_dts_and_board_config.md)
- [10.3 U-Boot 环境变量](10_ma5671a_board_reference/03_board_tuning_and_env.md)
