# 5.4 COP 表搜索协处理器与表结构

GPE 内部包含 8 个硬件表搜索协处理器（COP0–COP7）；GPE 初始化的 625 MHz 目标及其证据边界见 [5.1](01_cop_overview.md)。PE 与主机通过片上 `LINK` 互连网络向 COP 发送查表、读写或微码执行请求，硬件在单套表引擎上支持直接数组、变长数组、顺序表、动态单链表、哈希表与三态掩码匹配。

## 1. 协处理器编号与微码映像

`SYS_GPE` 的 bit 31:24（掩码 `0xFF000000`）提供 COP7–COP0 的独立时钟与复位控制。其中 COP0–COP5 为带 16 位微码的表搜索协处理器（分别装载 `tse0.bin`–`tse5.bin`）：

| 协处理器 ID | 硬件名称 | 微码映像 | 映像长度 | 内部标题 | 指令数 | PC 范围 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | FID | `tse0.bin` | 697 B | `FID TSE Micro Program` | 40 | 0–39 |
| 1 | FWD | `tse1.bin` | 812 B | `FWD TSE Micro Program` | 85 | 0–84 |
| 2 | TAG | `tse2.bin` | 575 B | `TAG TSE Micro Program` | 24 | 0–23 |
| 3 | TBL | `tse3.bin` | 603 B | `TBL TSE Micro Program` | 18 | 0–17 |
| 4 | MSF | `tse4.bin` | 431 B | `MSF TSE Micro Program` | 0 | — |
| 5 | EXT | `tse5.bin` | 597 B | `EXT TSE Micro Program` | 18 | 0–17 |
| 6–7 | — | 无 | — | — | — | — |
| 14 | TBM | 无 | — | Token Bucket Meter | — | — |

COP6、COP7 在 `SYS_GPE` 中有独立时钟门控位，标识 14 命名为 `TBM`（SBS2 总线 `0x1D600700` 另有 `TBM` 寄存器窗口），这三项均无对应的 `tse` 微码映像。在 `LINK` 消息的 5 位 `COPID` 字段（`0`–`31`）中，编号 `0`–`5` 对应 `TSE0`–`TSE5`，编号 `30` 对应 `TBM`，编号 `31` 对应 `LOOP`。

## 2. COP 内部寄存器地址空间

当发往 COP 的消息指定逻辑表号 `table == 0` 时，10 位 `index` 直接寻址该 COP 的内部控制寄存器与代码 RAM：

| 寄存器名 | 内部 10 位索引 | 功能说明 |
| --- | --- | --- |
| `COPLINK_COP_TABLE10`–`TABLE12` | `0x004`–`0x006` | 表 1 配置寄存器 0–2 |
| `COPLINK_COP_TABLE20`–`TABLE22` | `0x008`–`0x00A` | 表 2 配置寄存器 0–2 |
| `COPLINK_COP_TABLE30`–`TABLE32` | `0x00C`–`0x00E` | 表 3 配置寄存器 0–2 |
| `COPLINK_COP_TABLE40`–`TABLE42` | `0x010`–`0x012` | 表 4 配置寄存器 0–2 |
| `COPLINK_COP_TABLE50`–`TABLE52` | `0x014`–`0x016` | 表 5 配置寄存器 0–2 |
| `COPLINK_COP_TABLE60`–`TABLE62` | `0x018`–`0x01A` | 表 6 配置寄存器 0–2 |
| `COPLINK_COP_TABLE70`–`TABLE72` | `0x01C`–`0x01E` | 表 7 配置寄存器 0–2 |
| `COPLINK_COP_GLOBAL0`–`GLOBAL5` | `0x100`–`0x105` | 全局配置与状态寄存器 0–5 |
| `COPLINK_COP_CRAM` | `0x200`–`0x2FF` | 256 个半字的代码 RAM（低 16 位 `COMMAND` 存放微码指令） |
| `COPLINK_COP_CUSTOM0`–`CUSTOM7` | `0x300`–`0x307` | 自定义匹配配置寄存器 0–7 |

## 3. 表配置寄存器 (`TABLE10`–`TABLE72`) 与硬件表结构

每个 COP 最多管理 7 张硬件数据表（表 1–表 7）。每张表由 3 个 32 位寄存器（`TABLEn0`、`TABLEn1`、`TABLEn2`）配置：

### 3.1 配置字 0 (`TABLEn0`)

| 位域 | 字段名 | 编码与硬件行为 |
| --- | --- | --- |
| `31:16` | `DATA_MASK` | 表数据掩码，每 1 位屏蔽 256 位表项中的 16 位 |
| `10:8` | `KEY_SIZE` | 搜索键宽度代码：`0`=0 位，`1`=16 位，`2`=32 位，`3`=64 位，`4`=96 位，`5`=128 位，`6`=144 位，`7`=160 位 |
| `7:6` | `ENTRY_SIZE` | 表项存储宽度代码：`0`=32 位，`1`=64 位，`2`=128 位，`3`=256 位 |
| `5:3` | `FUNCTION` | 硬件匹配功能：`0`=`GENERIC`（通用全键匹配），`1`=`CUSTOM`（自定义协议字段匹配，对 ARRAY 与 HASH 无效），`2`=`TERNARY`（三态掩码匹配） |
| `2:0` | `TYPE` | 硬件表类型：`0`=`ARRAY`，`1`=`VARRAY`，`2`=`LIST`，`3`=`LLIST`，`4`=`HASH`（寄存器定义还保留 `5`=`TREE`） |

### 3.2 配置字 1 (`TABLEn1`) 与配置字 2 (`TABLEn2`)

| 寄存器 | 位域 | 字段名 | 编码与硬件行为 |
| --- | --- | --- | --- |
| `TABLEn1` | `31:16` | `SIZE` | 表项最大条数 |
| `TABLEn1` | `15:0` | `BASE` | 表在 COP 本地数据 RAM 中的基址（以 32 位字为单位） |
| `TABLEn2` | `31` | `AUX_V` | 空闲链表头指针有效标志（`1` 为有效，`0` 为空闲表已耗尽） |
| `TABLEn2` | `25:16` | `ENTRY_COUNTER` | 当前有效表项计数（执行 `ADD` 命令加 1，执行 `REMOVE` 命令减 1） |
| `TABLEn2` | `15:0` | `AUX` | 仅用于 `LLIST`：指向空闲链表（free list）下一表项的指针 |

`LLIST`（动态单链表）表项的控制字段位于每个条目最后一个 32 位字的高 16 位：bit 31 为 `VALID`（有效标志），bit 30 为 `END`（链表尾标志），bit 29:16 为 `NEXT`（下一表项的 32 位字地址）。初始化 `LLIST` 表时，`TABLEn2` 写入 `BASE | 0x80000000`（置位 `AUX_V` 并将 `AUX` 指向表首项），表中第 `0` 至 `SIZE - 2` 项的末字依次写入下一表项地址 `next_base << 16`，最后一项（`SIZE - 1`）的末字写入 `0x40000000`（置位 `END`）。

## 4. 六份微码的表配置参数

`tse0.bin`–`tse5.bin` 为 COP0–COP5 配置的硬件表参数如下（所有非零表的初始 `AUX_V` 均为 1，初始 `ENTRY_COUNTER` 均为 0）：

### 4.1 `tse0.bin` (COP0: FID)

| 表号 | 类型 | 功能 | 表项宽度 (位) | 键宽 (位) | 条目数 | 基址 (`BASE`) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `LLIST` | `GENERIC` | 64 | 32 | 256 | `0x0000` |
| 2 | `HASH` | `GENERIC` | 32 | 32 | 128 | `0x0200` |
| 3 | `LIST` | `GENERIC` | 32 | 16 | 64 | `0x0280` |
| 4 | `LIST` | `GENERIC` | 256 | 128 | 128 | `0x02c0` |
| 5 | `LIST` | `TERNARY` | 256 | 128 | 128 | `0x02c0` |

### 4.2 `tse1.bin` (COP1: FWD)

| 表号 | 类型 | 功能 | 表项宽度 (位) | 键宽 (位) | 条目数 | 基址 (`BASE`) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `HASH` | `GENERIC` | 32 | 64 | 512 | `0x0000` |
| 2 | `LLIST` | `GENERIC` | 128 | 64 | 1024 | `0x0200` |
| 3 | `ARRAY` | `GENERIC` | 32 | 0 | 128 | `0x1200` |
| 4 | `VARRAY` | `GENERIC` | 128 | 0 | 1024 | `0x0200` |

### 4.3 `tse2.bin` (COP2: TAG)

| 表号 | 类型 | 功能 | 表项宽度 (位) | 键宽 (位) | 条目数 | 基址 (`BASE`) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `VARRAY` | `GENERIC` | 64 | 0 | 128 | `0x0000` |
| 2 | `LIST` | `GENERIC` | 32 | 16 | 1024 | `0x0100` |
| 3 | `LLIST` | `GENERIC` | 64 | 64 | 256 | `0x0500` |
| 4 | `LIST` | `GENERIC` | 256 | 128 | 128 | `0x0700` |
| 5 | `LIST` | `TERNARY` | 256 | 128 | 128 | `0x0700` |

### 4.4 `tse3.bin` (COP3: TBL)

| 表号 | 类型 | 功能 | 表项宽度 (位) | 键宽 (位) | 条目数 | 基址 (`BASE`) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `VARRAY` | `GENERIC` | 128 | 0 | 256 | `0x0000` |
| 2 | `HASH` | `GENERIC` | 32 | 128 | 256 | `0x0400` |
| 3 | `LLIST` | `GENERIC` | 256 | 128 | 400 | `0x0500` |
| 4 | `LIST` | `GENERIC` | 256 | 128 | 128 | `0x1180` |
| 5 | `LIST` | `TERNARY` | 256 | 128 | 128 | `0x1180` |

### 4.5 `tse4.bin` (COP4: MSF)

| 表号 | 类型 | 功能 | 表项宽度 (位) | 键宽 (位) | 条目数 | 基址 (`BASE`) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `VARRAY` | `GENERIC` | 64 | 0 | 256 | `0x0000` |
| 2 | `LIST` | `GENERIC` | 128 | 64 | 512 | `0x0200` |
| 3 | `ARRAY` | `GENERIC` | 32 | 0 | 704 | `0x0a00` |
| 4 | `LIST` | `GENERIC` | 32 | 16 | 64 | `0x0cc0` |

### 4.6 `tse5.bin` (COP5: EXT)

| 表号 | 类型 | 功能 | 表项宽度 (位) | 键宽 (位) | 条目数 | 基址 (`BASE`) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `VARRAY` | `GENERIC` | 64 | 0 | 128 | `0x0000` |
| 2 | `LIST` | `CUSTOM` | 64 | 96 | 1024 | `0x0100` |
| 3 | `VARRAY` | `GENERIC` | 64 | 0 | 1024 | `0x0900` |
| 4 | `LIST` | `GENERIC` | 32 | 16 | 64 | `0x1100` |
| 5 | `LIST` | `GENERIC` | 256 | 128 | 128 | `0x1140` |
| 6 | `LIST` | `TERNARY` | 256 | 128 | 128 | `0x1140` |

## 5. 全局配置寄存器 (`GLOBAL0`–`GLOBAL5`)

| 寄存器 | 内部索引 | 位域与硬件功能 |
| --- | --- | --- |
| `GLOBAL0` | `0x100` | bit 18:16 `FUNCTION`（当前 COP 支持的匹配功能：Ternary/Custom/Generic）；bit 15:0 `TYPE`（当前 COP 支持的表类型：HASH/LLIST/LIST/VARRAY/ARRAY） |
| `GLOBAL1` | `0x101` | bit 31:28 `VERSION`（COP 硬件版本）；bit 27:24 `TABLES`（支持的表数量）；bit 23:16 `CRAM_SIZE`（CRAM 条目数）；bit 15:0 `DRAM_SIZE`（连接的表存储器容量） |
| `GLOBAL2` | `0x102` | bit 22:16 `TRACE_ID`（跟踪响应的目标线程 ID，初始化写 `0x7E << 16`）；bit 1 `PERF`（A2x 性能计数器使能）；bit 0 `TRACE`（单步跟踪模式使能） |
| `GLOBAL3` | `0x103` | bit 15:0 `PRESCALE`（时间戳计数器预分频值） |
| `GLOBAL4` | `0x104` | bit 31:0 `PERFORMANCE_CNTR`（A2x：当 `GLOBAL2.PERF = 1` 时记录上一次命令处理消耗的时钟周期数） |
| `GLOBAL5` | `0x105` | A2x 隐藏特性寄存器：bit 31:24 `WRITE_ENABLE_CODE` 必须写入 `0xF1`；bit 2 `ADD_FORCE_TOUCH`（空表 `NIL = 0` 时仍插入元素）；bit 1 `MASKED_SEARCHW`（`SEARCHW` 时对键字段做掩码）；bit 0 `NEW_SEARCHW`（使能新 `SEARCHW` 协议）。初始化写入 `0xF1000003` |

## 6. `LINKC1` / `LINKC2` 查表消息协议

PE 线程与主机（经 `LINK2` 接口，物理基址 `0x1D600400`）均使用 `LINKC1` 请求格式与 `LINKC2` 响应格式访问 COP。每次总线传输以 64 位（`DATA0`、`DATA1` 两个 32 位字）为单位，首拍置 `BMX | SOP`，末拍置 `EOP`。

### 6.1 `LINKC1` 请求命令头

| 位域 | 宽度 | 字段名 | 说明 |
| --- | --- | --- | --- |
| `31:27` | 5 位 | `COPID` | 目标协处理器编号（`0`–`7` 为 COP0–COP7，`30` 为 TBM，`31` 为 LOOP） |
| `26:20` | 7 位 | `TID` | 发起请求的线程 ID（主机常规访问使用 `0x7F`，微码单步跟踪使用 `0x7E`） |
| `19:16` | 4 位 | `CMD` | 硬件命令码：`0x0` `READ`、`0x1` `CLEAR`（或 `SEARCHR` 左移 2 位拼入 2 位长度码）、`0x2` `WRITE`、`0x3` `COUNT`、`0x8` `SEARCH`、`0x9` `REMOVE`、`0xA` `ADD`、`0xB` `SEARCHW`、`0xC` `EXEC` |
| `15:12` | 4 位 | `TABLE` | 目标逻辑表编号（`0`–`7`）；当 `CMD == 0xC` (`EXEC`) 时，bit 18:12 填入 7 位微码入口 PC |
| `11` | 1 位 | `NIL` | 空表标志位 |
| `10` | 1 位 | `OFF` | 条目内字偏移标志 |
| `9:0` | 10 位 | `INDEX` | 10 位表项索引或 `table = 0` 时的内部寄存器地址（`0x000`–`0x3FF`） |

### 6.2 `LINKC2` 响应头与硬件状态码

COP 完成命令后返回 2 个 32 位字的 `LINKC2` 响应头（以及可选的 32/64/128/256 位查表结果数据）：

- 响应字 0（对应 `DATA1`）：bit 31:27 为 `COPID`，bit 26:20 为 `TID`，bit 19 为 `RES`（命中标志，掩码 `0x80000`），bit 18:16 为 3 位错误码 `ERR`（掩码 `0x70000`），bit 15:12 为 `TABLE`，bit 11 为 `NIL`，bit 9:0 为 `INDEX`。
- 响应字 1（对应 `DATA0`）：当附带结果数据时，bit 31:24 为 8 位硬件老化时间戳 `TIMESTAMP`；当处于微码单步跟踪模式（`TID = 0x7E`）时，bit 31 为 `DBGRES2`，bit 30:28 为 `DBGERR`，bit 27:18 为 10 位 `DBGPREV`，bit 17:8 为 10 位 `DBGNEXT`，bit 6:0 为 7 位 `DBGPC`。

3 位硬件状态码 `ERR`（`0`–`7`）的定义如下：

| `ERR` 编码 | 状态名 | 触发条件 |
| --- | --- | --- |
| 0 | `OK` | 执行完成且无错误 |
| 1 | `INVALID_INDEX` | `INDEX` 超出表容量或无效（例如执行 `INDEX = AUX` 后指向无效地址） |
| 2 | `END_OF_TABLE` | 顺序搜索到达表尾仍未找到匹配项 |
| 3 | `OUT_OF_MEMORY` | 向 `LLIST` 执行 `ADD` 时空闲链表已空（`AUX_V == 0`） |
| 4 | `ENTRY_EXISTS` | 向 `LIST` 或 `LLIST` 执行 `OV = 0` 的 `ADD` 时表中已存在相同键值 |
| 5 | `ERROR_DISCARD_FRAME` | 由外部信号 `External_0` 触发的丢包错误 |
| 6 | `SOFT_ERR_1` | 微码执行 `mov %err, 6` 触发的自定义错误 1 |
| 7 | `SOFT_ERR_2` | 微码执行 `mov %err, 7` 触发的自定义错误 2 |

## 本地依据与适用范围

`bsp/modules/onu/drv_onu_reg_coplink_cop.h`、`drv_onu_ll_cop.c`；表配置与指令数还可对照 `extracted/rootfs/lib/firmware/sfu/tse0.bin`–`tse5.bin` 和本地 `docs/COP_ISA.md`。

上述 `bsp/` 路径按本次审计的 `linux-3.10.49` 基线读取，属于源码/静态固件证据；不将 `linux-7.3` 移植结果或未上板验证的解释当作原固件运行事实。
