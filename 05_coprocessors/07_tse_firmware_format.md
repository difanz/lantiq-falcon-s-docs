# 5.7 TSE 微码容器与加载器

`tse0.bin`–`tse5.bin` 采用按记录组织的二进制容器格式。容器内封装了 16 位微码指令、表配置寄存器初值（`TABLE10`–`TABLE72`）、自定义匹配寄存器初值（`CUSTOM0`–`CUSTOM7`）、导出函数入口表、符号名字符串表以及注释段。

## 1. 记录格式 (`type` 0–9)

容器由多条记录顺序拼接而成。每条记录以 1 字节 `type` 和 1 字节 `length` 开头，后跟 `length` 字节载荷：

| 字节偏移 | 长度 | 字段名 | 说明 |
| --- | --- | --- | --- |
| `0` | 1 B | `type` | 记录类型（`0`、`1`–`3`、`5`、`7`–`9`） |
| `1` | 1 B | `length` | 后续载荷字节数 |
| `2` | `length` B | `payload` | 按 `type` 解析的地址、数据与末尾 1 字节校验和 |

各记录类型的结构与解析规则如下：

| `type` | 记录类别 | 载荷结构与解析行为 |
| --- | --- | --- |
| `0` | 文件头记录 | 跳过 `length` 字节。六份映像均为 3 字节载荷 `00 00 fc` |
| `1`、`2`、`3` | 数据记录 | 大端地址占 `type + 1` 字节（2、3、4 字节），数据长度为 `length - type - 2` 字节，最后 1 字节为校验和。六份映像的数据记录全部为 `type = 3`（4 字节大端地址） |
| `5` | 记录计数记录 | 跳过 `length` 字节。六份映像均为 3 字节载荷：前 2 字节为本文件 `type = 3` 记录的大端条数（`tse0` `0x001f`=31、`tse1` `0x0025`=37、`tse2` `0x0019`=25、`tse3`/`tse5` `0x001b`=27、`tse4` `0x0013`=19），第 3 字节与计数低字节之和等于 `0xFC` |
| `7`、`8`、`9` | 结束记录 | 取载荷前 `length - 1` 字节按大端拼出复位入口 PC，忽略末字节校验和并终止解析。六份映像均为 `07 05 00 00 00 00 fa`（入口 PC = 0，`0x05 + 0xfa = 0xFF`） |

### 1.1 8 位累加校验和 (`0xFF`)

对于 `type = 1, 2, 3` 的数据记录（除 `0x4000`–`0xBFFF` 数据窗口外），`length` 字节、全部地址字节、全部数据字节与末尾校验字节按无符号 8 位相加，低 8 位结果恒等于 `0xFF`（`type` 字节不计入累加）：

```
(length + sum(address_bytes) + sum(data_bytes) + checksum) & 0xFF == 0xFF
```

以 `tse0.bin` 第一条代码记录为例：

```
03 15  00 00 00 00  e010 a010 0305 7000 a088 0005 e010 7340  02
```

- `type = 0x03`，`length = 0x15`（21 字节）。
- 4 字节大端地址：`0x00000000`。
- 16 字节代码（8 条半字指令，首条 `0xe010` 为 `settab 2`），各字节之和为 `0x5E8`。
- 校验字节：`0x02`（`(0x15 + 0x00 + 0x5E8 + 0x02) & 0xFF = 0xFF`）。

## 2. 逻辑地址窗口与硬件索引换算

`type = 3` 记录中的 32 位地址落在 `0x0000`–`0xFFFF` 的 8 个逻辑窗口内：

| 窗口名称 | 地址范围 | 提交粒度与装载行为 | 六份映像中的内容 |
| --- | --- | --- | --- |
| 代码 (`CODE`) | `0x0000`–`0x3FFF` | 字节地址为奇数时提交 1 个大端 `uint16_t` 半字，写目标为 `addr & ~1` | `tse0`–`tse3`、`tse5` 含微码；记录可不按地址升序排列（`tse1` 的 PC 0 位于文件后部单独一条 2 字节记录中） |
| 数据 (`DATA`) | `0x4000`–`0xBFFF` | 按 4 字节大端字通过表 7 写入 COP 表存储器 | 未使用 |
| 表配置 (`TABLE`) | `0xC000`–`0xDFFF` | 地址低 2 位为 `3` 时提交 1 个大端 `uint32_t` 配置字 | 每份映像含表 0（16 字节全 0）及表 1–6 配置（每表 16 字节） |
| 符号名 (`NAMES`) | `0xE000`–`0xEFFF` | NUL 分隔的 ASCII 字符串流 | 与导出窗口中的函数项按出现顺序一一配对 |
| 全局配置 (`GLOBAL`) | `0xF000`–`0xF3FF` | 仅校验累加和，不写硬件 | 未使用 |
| 自定义配置 (`CUSTOM`) | `0xF400`–`0xF7FF` | 地址低 2 位为 `3` 时提交 1 个大端 `uint32_t` 字 | 六份映像相同（8 个 32 位字） |
| 接口导出 (`INTERFACE`) | `0xF800`–`0xFBFF` | 连续的 `uint16_t id` + `uint16_t byte_addr`，以 `id = 0, addr = 0` 结束 | 导出微码入口点 |
| 注释 (`COMMENT`) | `0xFC00`–`0xFFFF` | NUL 分隔的元数据字符串 | `TOOL`、`TITLE`、`VERSION`、`AUTHOR`、`DESCRIPTION` |

向硬件 COP 装载 `CODE`、`TABLE`、`GLOBAL`、`CUSTOM` 窗口时，通过 `LINK2` 发送 `table = 0`、`cmd = WRITE (2)` 的 `LINKC1` 消息。10 位寄存器索引 `index` 由窗口地址低 10 位（`address & 0x3FF`）移位并或上 2 位空间编码生成：

| 目标窗口 | 空间编码 (`[9:8]`) | 10 位 `index` 计算公式 | 地址映射示例 |
| --- | --- | --- | --- |
| `TABLE` | `0` (`0x000`) | `((address & 0x3FF) >> 2) \| (0 << 8)` | `0xC010` → `0x004` (`COPLINK_COP_TABLE10`) |
| `GLOBAL` | `1` (`0x100`) | `((address & 0x3FF) >> 2) \| (1 << 8)` | `0xF004` → `0x101` (`COPLINK_COP_GLOBAL1`) |
| `CODE` | `2` (`0x200`) | `((address & 0x3FF) >> 1) \| (2 << 8)` | `0x0000` → `0x200` (`COPLINK_COP_CRAM + 0`) |
| `CUSTOM` | `3` (`0x300`) | `((address & 0x3FF) >> 2) \| (3 << 8)` | `0xF400` → `0x300` (`COPLINK_COP_CUSTOM0`) |

代码窗口中的字节地址右移 1 位即指令 PC。导出记录中的 `byte_addr` 同样为字节地址，右移 1 位后得到 `LINKC1` `EXEC` 命令使用的 7 位微码入口 PC（`func_addr = byte_addr >> 1`）。

## 3. `CUSTOM0`–`CUSTOM7` 寄存器定义与初值

`COPLINK_COP_CUSTOM0`–`CUSTOM7`（内部索引 `0x300`–`0x307`）提供 `CUSTOM` 匹配模式下的以太网类型（EtherType）与外层 TPID 硬件比较值。六份微码容器的 `0xF400` 窗口均包含相同的 8 个 32 位初值，运行期再按 Extended VLAN 规则写入协议常量：

| 寄存器 | 内部索引 | 微码容器初值 | 位域定义 | Extended VLAN 运行期配置 |
| --- | --- | --- | --- | --- |
| `CUSTOM0` | `0x300` | `0x00000000` | bit 31:16：A1x 为 `FID`，A2x 为 `TPID`；bit 1：`XTRUE`（置 X 条件恒真）；bit 0：`DEFRULE`（激活默认规则） | `TPID = 0x8100` (`CVLAN`)，`DEFRULE = 1` |
| `CUSTOM1` | `0x301` | `0xFFFF0000` | bit 15:0：`ETY1`（EtherType 1） | `ETY1 = 0x0800` (`IPV4`) |
| `CUSTOM2` | `0x302` | `0xFFFF0000` | bit 15:0：`ETY2`（EtherType 2） | `ETY2 = 0x8863` (`PPPOE_DISC`) |
| `CUSTOM3` | `0x303` | `0xFFFF0000` | bit 15:0：`ETY3`（EtherType 3） | `ETY3 = 0x0806` (`ARP`) |
| `CUSTOM4` | `0x304` | `0xFFFF0000` | bit 15:0：`ETY4`（EtherType 4） | `ETY4 = 0x86DD` (`IPV6`) |
| `CUSTOM5` | `0x305` | `0x00000000` | bit 31:16：`ETY_MASK`；bit 15:0：`ETY5`（EtherType 5） | `0x00000000` |
| `CUSTOM6` | `0x306` | `0x00000000` | bit 31:16：`SPARE1_MASK`；bit 15:0：`SPARE1` | `0x00000000` |
| `CUSTOM7` | `0x307` | `0x00000000` | bit 31:16：`SPARE2_MASK`；bit 15:0：`SPARE2` | `0x00000000` |

## 4. 微码导出函数表 (`0xF800` 与 `0xE000` 窗口)

每个协处理器最多支持 10 个导出标签，全局标签表共 26 个槽位（编号 `0`–`25`）。六份微码映像导出的全部 16 个微码入口点如下：

| 所属微码 | 导出编号 (`id`) | 映像内符号名 (`0xE000` 窗口) | 接口宏名 | 字节地址 (`byte_addr`) | 入口 PC (`byte_addr >> 1`) |
| --- | --- | --- | --- | --- | --- |
| `tse0.bin` (COP0) | 10 | `IF_FID_LOOKUP_MC` | `IF_FID_LOOKUP` | `0x0000` | 0 |
| `tse0.bin` (COP0) | 25 | `IF_FID_LOOKUP_UC` | — | `0x000c` | 6 |
| `tse0.bin` (COP0) | 18 | `IF_ETHFILT_SEARCHW` | `IF_ETHFILT_SEARCHW` | `0x0038` | 28 |
| `tse0.bin` (COP0) | 24 | `IF_ACL_SEARCH_3` | — | `0x0040` | 32 |
| `tse1.bin` (COP1) | 1 | `IF_FWD_AGE` | `IF_FWD_AGE` | `0x0000` | 0 |
| `tse1.bin` (COP1) | 2 | `IF_FWD_FORWARD` | `IF_FWD_FORWARD` | `0x0002` | 1 |
| `tse1.bin` (COP1) | 3 | `IF_FWD_RELEARN` | `IF_FWD_RELEARN` | `0x0018` | 12 |
| `tse1.bin` (COP1) | 4 | `IF_FWD_ADD` | `IF_FWD_ADD` | `0x0034` | 26 |
| `tse1.bin` (COP1) | 5 | `IF_FWD_REMOVE` | `IF_FWD_REMOVE` | `0x0072` | 57 |
| `tse2.bin` (COP2) | 6 | `IF_TAG_FILTER` | `IF_TAG_FILTER` | `0x0000` | 0 |
| `tse2.bin` (COP2) | 22 | `IF_ACL_SEARCH_1` | — | `0x0020` | 16 |
| `tse3.bin` (COP3) | 7 | `IF_IPV6_REDUCE` | `IF_IPV6_FORWARD` | `0x0000` | 0 |
| `tse3.bin` (COP3) | 15 | `IF_IPV6HASH_SEARCHR` | `IF_IPV6HASH_SEARCHR` | `0x000c` | 6 |
| `tse3.bin` (COP3) | 23 | `IF_ACL_SEARCH_2` | — | `0x0014` | 10 |
| `tse5.bin` (COP5) | 9 | `IF_VLAN_TRANSLATE` | `IF_VLAN_TRANSLATE` | `0x0000` | 0 |
| `tse5.bin` (COP5) | 21 | `IF_ACL_SEARCH_0` | — | `0x0014` | 10 |

`tse4.bin`（COP4）仅包含 `id = 0, addr = 0` 的结束项，无微码入口导出。接口定义中另保留但未在六份映像中导出的编号为：8 (`IF_IPV4_SEARCH`)、11 (`IF_FID_SEARCH`)、12 (`IF_UPGEM_SEARCHR`)、13 (`IF_FID_GET_PREVIOUS`)、14 (`IF_FID_REMOVE`)、16 (`IF_FIDHASH_SEARCHR`)、17 (`IF_IPV4_SEARCHW`)。

## 5. 注释段结构 (`0xFC00` 窗口)

每份微码的 `0xFC00` 窗口存放 NUL 分隔的键值对字符串（`DESCRIPTION:` 与其后的说明正文为相邻的两个 NUL 结尾字符串）。六份微码映像的元数据汇总如下：

| 微码文件 | `TOOL` | `TITLE` | `VERSION` | `AUTHOR` | `DESCRIPTION` |
| --- | --- | --- | --- | --- | --- |
| `tse0.bin` | `Version 4.54` | `FID TSE Micro Program` | `3.11` | `Schaefer, Brunnbauer, Linortner` | `Implements the microcode for the TSE0 coprocessor.` |
| `tse1.bin` | `Version 4.54` | `FWD TSE Micro Program` | `3.1` | `Schaefer, Brunnbauer, Linortner` | `Implements the microcode for the TSE1 coprocessor` |
| `tse2.bin` | `Version 4.54` | `TAG TSE Micro Program` | `3.9` | `Schaefer, Brunnbauer, Linortner` | `Implements the microcode for the TSE2 coprocessor.` |
| `tse3.bin` | `Version 4.54` | `TBL TSE Micro Program` | `3.16` | `Schaefer, Brunnbauer, Linortner` | `Implements the microcode for the TSE3 coprocessor.` |
| `tse4.bin` | `Version 4.54` | `MSF TSE Micro Program` | `3.3` | `Schaefer, Brunnbauer, Linortner` | `Implements the microcode for the TSE4 coprocessor.` |
| `tse5.bin` | `Version 4.54` | `EXT TSE Micro Program` | `3.8` | `Schaefer, Brunnbauer, Linortner` | `Implements the microcode for the TSE5 coprocessor.` |

六份微码反汇编文件（`tse0.s`–`tse5.s`）的全部伪指令与每条 16 位微码指令的逐行详解见 [5.8 TSE 微码固件反汇编逐行详解（tse0.s – tse5.s）](08_tse_firmware_disassembly.md)。
