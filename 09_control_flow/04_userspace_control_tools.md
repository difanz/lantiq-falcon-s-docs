# 9.4 主控初始化与光前端控制

## 数据通路初始化

主控按时钟、复位、微码、缓冲和端口的依赖顺序初始化数据通路。以下配置示例使用六个 PE 与六个 COP，并为 GPON 管理通道、GEM 业务和 UNI 接口建立资源映射：

| 步骤 | 目标硬件模块 | 硬件初始化动作 |
| --- | --- | --- |
| 1. PLOAM 复位 | `GTC` (`0x1DC00000`) | 清空 PLOAM 接收队列，将状态机置于 O1 初始同步态 |
| 2. GTC 配置与激活 | `GTC` (`0x1DC00000`) | 1. 写入 8 字节 GPON 序列号与 10 字节注册密码。<br/>2. 配置 `GTC` SF/SD 误码门限、激光器开启/关断扩展时延与 PLOAM 超时。<br/>3. 解除 `GTC` 硬件复位并使能下行帧同步器与 Dying Gasp 硬件自动发包触发器。 |
| 3. GPHY 固件装载 | `SBS0` (`0x1F204000`)<br/>`SBS0CTRL` (`0x1F080000`) | 将 8051 代码映像写入片上 `SBS0` RAM（物理地址 `0x1F204000`），配置 `GPHY0IMG`/`GPHY1IMG` 重映射基址并释放 `SYS_ETH` 复位 |
| 4. GPE 与微码启动 | `SYS_GPE` (`0x1D700000`)<br/>`PCTRL` (`0x1D600000`)<br/>`PE0`–`PE5` / `COP0`–`COP5`<br/>`FSQM` (`0x1D500000`) | 1. 通过 `SYS_GPE` 使能 GPE 各功能块时钟并执行硬件复位。<br/>2. 暂停 `PE0`–`PE5` 全部 18 台虚拟机（`PCTRL.TCTRL0`），将 64 位分类微码写入 6 颗 PE 的 `PROG[]` 存储器，将 `tse0.bin`–`tse5.bin` 装入 `COP0`–`COP5` 微码 RAM。<br/>3. 按配置的段索引范围建立 `FSQM` 的 `SSB0` 空闲链表，再激活 `MERGE`、`DISP`、`IQM`、`TMU`、`ICTRLG` 与 `OCTRLG`。 |
| 5. 共享缓冲水位设置 | `FSQM` (`0x1D500000`) | 编程 `FSQM` 的 5 级全局空闲段阈值寄存器 `FSQT0`–`FSQT4`（示例值 `1024`、`12288`、`12288`、`12288`、`12288`） |
| 6. EIM 与 UNI 端口激活 | `EIM` (`0x1D800000`)<br/>`SGMII` (`0x1D808C00`)<br/>`SXGMII` (`0x1D808800`) | 1. 激活 `EIM`、`ICTRLL0..3`（`0x1D460000`）与 `OCTRLL0..3`（`0x1D440000`）。<br/>2. 根据接口模式配置 `SGMII`（1 Gbps SGMII / 1000BASE-X）或 `SXGMII`（2.5 Gbps HiSGMII / SerDes）锁相环与自协商寄存器，写入 IEEE 802.3x PAUSE 帧源 MAC 地址。 |


## 光前端控制

`PMA`（`0x1DD00000`）、`FCSIC`（`0x1DD00600`）、BOSA 模拟电路与 `DCDC_APD`（`0x1E805000`）组成光路测量和功率控制通路：

1. 配置收发极性、激光器偏置和调制电流限制、MPD 标定参数以及温度告警门限。
2. 读取 FCSI、MM 测量模块与 APD 电源的就绪状态。
3. MM 采样温度与光功率；控制器依据温度补偿参数更新 BFD、TXBOSA 和 DCDC_APD 工作点。
4. BFD / MPD 双环 APC 在突发发送窗口内采样背光二极管电流，与 P0 / P1 目标值比较，并修正激光器偏置及调制量。

校准参数与测量寄存器见 [光学校准](../07_phy_and_mac/03_laser_calibration.md)，电源启停和锁存顺序见 [DC/DC 转换器](../06_functional_blocks/07_dcdc_converters.md)。
