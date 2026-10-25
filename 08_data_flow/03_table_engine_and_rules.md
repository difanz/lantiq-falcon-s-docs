# 8.3 GPE 表接口与 FID 转发

GPE（GPON Packet Engine）采用双域硬件表架构支撑线速报文解析与转发：定长配置属性表镜像存储在 6 颗 `PE`（`PE0`–`PE5`，`0x1D610000`–`0x1D660000`）各自的片上数据 RAM 中，供硬件线程单周期直接寻址；流表、哈希表、规则表与计数器表存储在 6 个表搜索协处理器功能块（`COP0 = FID`、`COP1 = FWD`、`COP2 = TAG`、`COP3 = TBL`、`COP4 = MSF`、`COP5 = EXT`）的专用表 SRAM 中，由协处理器微码或硬连线表引擎执行哈希查找、单链表遍历、三态掩码匹配或原子计数。各功能块的完整表存储器布局与表项位域见 [5.5 SCE 硬件功能块详解](../05_coprocessors/05_sce_function_blocks.md)，协处理器微码的逐行指令实现见 [5.8 TSE 微码固件反汇编逐行详解](../05_coprocessors/08_tse_firmware_disassembly.md)。

```mermaid
flowchart TD
    HOST["主控配置通道"] -->|HOST 邮箱广播写入 PE0..PE5| PE_RAM["PE 本地数据 RAM 表 ID 64..79"]
    HOST -->|LINK1 / LINK2 协处理器命令帧| COP_BUS["SCE 内部 COP 命令与响应总线"]
    PE_THREAD["PE0..PE5 48 路硬件线程"] -->|单周期本地读取| PE_RAM
    PE_THREAD <-->|LINK0 发起查表与接收响应| COP_BUS
    COP_BUS --> COP0["COP0 FID 转发域分配与 EtherType / ACL Lane 3 ID 0..7"]
    COP_BUS --> COP1["COP1 FWD 二层 MAC / IPv4 短转发与学习老化 ID 8..15"]
    COP_BUS --> COP2["COP2 TAG VLAN 标签过滤与 MAC 过滤 / ACL Lane 1 ID 16..23"]
    COP_BUS --> COP3["COP3 TBL 下行 GEM Port 与 IPv6 压缩 / ACL Lane 2 ID 24..31"]
    COP_BUS --> COP4["COP4 MSF 上行 GEM Port、源过滤与计数器 ID 32..39"]
    COP_BUS --> COP5["COP5 EXT Extended VLAN 转换与 L4 / ACL Lane 0 ID 40..47"]
```

---

## 1. 硬件表编号空间与存储域划分

GPE 将全部硬件表统一编址在 7-bit 全局 `Table ID`（`0`–`79`）空间内，按 `ID = 64` 划分为两个物理存储域：

| 存储域 | 全局 Table ID 范围 | 硬件寻址译码 | 物理位置与访问机制 |
| --- | --- | --- | --- |
| **COP 协处理器表** | `0`–`63` | `cop_id = id >> 3`<br/>`tbl_id = id & 0x7` | 位于 `COP0`–`COP5` 专用表 SRAM（每颗 COP `2048 × 32-bit`）。通过 `LINK0`（PE 线程）或 `LINK1`/`LINK2`（主控）发送 `LINKC1` 原语（`READ`、`WRITE`、`ADD`、`REMOVE`、`SEARCH`、`SEARCHR`、`SEARCHW`、`COUNT`、`EXEC`）访问 |
| **PE 本地镜像表** | `64`–`79` | `pe_tbl_idx = id - 64` | 位于 `PE0`–`PE5` 的 12 KiB 本地数据 RAM。转发线程单周期直接读取；主控通过 `HOST[1]`–`HOST[9]` 邮箱寄存器配合 `PCTRL.ISIG` 信号以 `pe_mask = 0x3F` 广播写入全部 6 颗 `PE` |

### 1.1 数据通路转发查表总览

| 全局 Table ID | 表名称 | 所属功能块 | 项数 × 宽度 | 表类型 / 模式 | 报文转发阶段与硬件用途 |
| --- | --- | --- | --- | --- | --- |
| `1` / `6` | `FID_ASSIGNMENT_TABLE` | `COP0` (`FID`) | 256 × 64-bit | `LLIST` (`GENERIC` / `MASK`) | 哈希冲突链表，将 `(prio_inner, vid_inner, prio_outer, vid_outer)` 映射为 8-bit `FID` 与 `cross_connect` 标志 |
| `2` | `FID_HASH_TABLE` | `COP0` (`FID`) | 128 × 32-bit | `HASH` (`GENERIC`) | 128 桶 FID 哈希头表，指向 `FID_ASSIGNMENT_TABLE` 冲突链首节点 |
| `3` | `ETHERTYPE_FILTER_TABLE` | `COP0` (`FID`) | 64 × 32-bit | `LIST` (`GENERIC`) | 二层 16-bit EtherType 协议过滤列表（由 `IF_ETHFILT_SEARCHW` 检索并置位命中标志） |
| `4` / `5` | `ACL_FILTER_TABLE_LANE3` | `COP0` (`FID`) | 128 × 256-bit | `LIST` (`GENERIC` / `TERNARY`) | 4 通道并行 ACL 搜索的第 4 通道（`IF_ACL_SEARCH_3`） |
| `9` | `SHORT_FWD_HASH_TABLE` | `COP1` (`FWD`) | 512 × 32-bit | `HASH` (`GENERIC`) | 二层 MAC 与 IPv4 短转发表的 512 桶哈希头表 |
| `10` / `12` | `SHORT_FWD_TABLE` | `COP1` (`FWD`) | 1024 × 128-bit | `LLIST` / `VARRAY` | 存放单播 MAC、组播 MAC、IPv4 单播与 IPv4 组播转发项（物理表 2 为 `LLIST` 供查表增删，物理表 4 为重叠基址 `VARRAY` 供 `IF_FWD_AGE` 顺序扫描老化） |
| `11` | `LEARNING_LIMITATION_TABLE` | `COP1` (`FWD`) | 128 × 32-bit | `ARRAY` (`GENERIC`) | 按桥接端口索引存放 16-bit `learning_limit` 与 16-bit `association_count` |
| `17` | `TAGGING_FILTER_TABLE` | `COP2` (`TAG`) | 128 × 64-bit | `VARRAY` (`GENERIC`) | VLAN Tagging Filter 入口描述符表（含 `tci_mask`、过滤极性与 `vlan_table_index`） |
| `18` | `VLAN_TABLE` | `COP2` (`TAG`) | 1024 × 32-bit | `LIST` (`MASK`) | 供 `IF_TAG_FILTER` 顺序比对 16-bit TCI 的过滤段列表 |
| `19` | `MAC_FILTER_TABLE` | `COP2` (`TAG`) | 256 × 64-bit | `LLIST` (`GENERIC`) | 源/目的 MAC 地址过滤链表 |
| `20` / `21` | `ACL_FILTER_TABLE_LANE1` | `COP2` (`TAG`) | 128 × 256-bit | `LIST` (`GENERIC` / `TERNARY`) | 4 通道并行 ACL 搜索的第 2 通道（`IF_ACL_SEARCH_1`） |
| `25` | `DS_GEM_PORT_TABLE` | `COP3` (`TBL`) | 256 × 128-bit | `VARRAY` (`GENERIC`) | 下行 GEM 端口属性表（以 8-bit `GPIX` 直接索引） |
| `26` | `IPV6_REDUCTION_HASH_TABLE` | `COP3` (`TBL`) | 256 × 32-bit | `HASH` (`GENERIC`) | 128-bit IPv6 地址压缩表 256 桶哈希头 |
| `27` | `IPV6_REDUCTION_TABLE` | `COP3` (`TBL`) | 400 × 256-bit | `LLIST` (`GENERIC`) | 将 128-bit IPv6 地址压缩映射为 9-bit 短索引（`0`–`399`） |
| `28` / `29` | `ACL_FILTER_TABLE_LANE2` | `COP3` (`TBL`) | 128 × 256-bit | `LIST` (`GENERIC` / `TERNARY`) | 4 通道并行 ACL 搜索的第 3 通道（`IF_ACL_SEARCH_2`） |
| `33` | `US_GEM_PORT_TABLE` | `COP4` (`MSF`) | 256 × 64-bit | `VARRAY` (`GENERIC`) | 上行 GEM 端口属性表（以 8-bit `GPIX` 索引出向 `GEM Port-ID` 与 `egress_queue`） |
| `34` | `DS_MC_IP_SOURCE_FILTER_TABLE` | `COP4` (`MSF`) | 512 × 128-bit | `LIST` (`GENERIC`) | 下行 IGMPv3 / MLDv2 组播源 IP 地址过滤表 |
| `35` | `COUNTER_TABLE` | `COP4` (`MSF`) | 704 × 32-bit | `ARRAY` (`GENERIC`) | 桥接端口收发/丢包、上下行 GEM Port 帧计数与网桥学习丢弃计数器 |
| `36` | `VLAN_METERING_TABLE` | `COP4` (`MSF`) | 64 × 32-bit | `LIST` (`GENERIC`) | 基于 VID 的上下行 `TBM` 计量器绑定表 |
| `41` | `EXTENDED_VLAN_TABLE` | `COP5` (`EXT`) | 128 × 64-bit | `VARRAY` (`GENERIC`) | Extended VLAN 引擎入口描述符表（含 `rule_table_pointer` 与自定义 TPID） |
| `42` | `VLAN_RULE_TABLE` | `COP5` (`EXT`) | 1024 × 64-bit | `LIST` (`CUSTOM`) | Extended VLAN 96-bit 键匹配规则表 |
| `43` | `VLAN_TREATMENT_TABLE` | `COP5` (`EXT`) | 1024 × 64-bit | `VARRAY` (`GENERIC`) | Extended VLAN 标签剥离、重写与压入动作表（由 `treat` 指令合成 128-bit 改写向量） |
| `44` | `L4_FILTER_TABLE` | `COP5` (`EXT`) | 64 × 32-bit | `LIST` (`GENERIC`) | 四层 TCP/UDP 端口号过滤列表 |
| `45` / `46` | `ACL_FILTER_TABLE_LANE0` | `COP5` (`EXT`) | 128 × 256-bit | `LIST` (`GENERIC` / `TERNARY`) | 4 通道并行 ACL 搜索的第 1 通道（`IF_ACL_SEARCH_0`） |
| `64` | `CONSTANTS_TABLE` | `PE0`–`PE5` | 51 × 32-bit | `ARRAY` | SCE 全局协议常量、TPID、老化周期与异常计量器参数表 |
| `65` | `BRIDGE_PORT_TABLE` | `PE0`–`PE5` | 88 × 128-bit | `VARRAY` | 桥接端口配置表（含入出向 VLAN 索引、计量器、网桥索引与转发控制标志） |
| `66` | `PMAPPER_TABLE` | `PE0`–`PE5` | 32 × 96-bit | `VARRAY` | IEEE 802.1p P-Mapper 8 路优先级到上行 `GPIX` 映射表 |
| `67` | `LAN_PORT_TABLE` | `PE0`–`PE5` | 8 × 256-bit | `VARRAY` | UNI 物理端口入口属性表 |
| `76` | `BRIDGE_TABLE` | `PE0`–`PE5` | 8 × 256-bit | `ARRAY` | 8 个虚拟网桥实例配置表（广播/未知单播/未知组播 64-bit 泛洪端口位图） |

---

## 2. Bridge Port 硬件表 (`BRIDGE_PORT_TABLE`, ID 65)

`BRIDGE_PORT_TABLE`（ID 65）在每颗 `PE` 本地数据 RAM 中包含 88 个表项（索引 `0`–`87`），每个表项占 128 位（4 个 32 位字 `Word 0`–`Word 3`）。无论是 UNI 物理端口、802.1p P-Mapper 还是单播/组播 GEM 端口，均通过分配独立的 `Bridge Port Index` 接入二层桥接矩阵。

### 2.1 128-bit 表项位域定义

| 32 位字 | 位域范围 | 字段名称 | 硬件功能说明 |
| --- | --- | --- | --- |
| `Word 0` | `[31:16]` | `learning_limit` | 端口学习限制参考值（同步写入 `COP1` `LEARNING_LIMITATION_TABLE` ID 11） |
| `Word 0` | `[15:10]` | `bridge_index` | 所属虚拟网桥实例编号（关联 `BRIDGE_TABLE` ID 76） |
| `Word 0` | `[9:8]` | `tp_type` | 终端点类型：`0` = UNI 端口，`1` = GEM 端口，`2` = 802.1p P-Mapper，`3` = IP Host |
| `Word 0` | `[7:0]` | `ext_vlan_idx` | 关联的 `EXTENDED_VLAN_TABLE`（ID 41）入口索引 |
| `Word 1` | `[31:24]` | `us_meter_id` | 入向流量监管计量器索引（指向 `COP14` `TBM` 桶 `0`–`511`） |
| `Word 1` | `[23:16]` | `ds_meter_id` | 出向流量监管计量器索引 |
| `Word 1` | `[15:8]` | `tag_filter_idx` | 关联的 `TAGGING_FILTER_TABLE`（ID 17）入口索引 |
| `Word 1` | `[6:0]` | `egress_port_idx` | 出向目标索引：根据 `tp_type` 指向 `GPIX`、`PMAPPER_TABLE` 索引或 UNI 端口号 |
| `Word 2` | `[31:24]` | `exception_profile` | 协议捕获与异常报文处理模板编号（指向 `EXCEPTION_TABLE` ID 78） |
| `Word 2` | `[22:16]` | `ingress_port_idx` | 入向源端口索引 |
| `Word 2` | `[15:0]` | `learned_cnt` | 状态与辅助计数字段 |
| `Word 3` | `[31:0]` | `ctrl_flags` | 硬件转发控制位与表项 `valid` 位（见下表） |

`Word 3` 中的转发控制位定义如下：

| 位名称 | 硬件行为说明 |
| --- | --- |
| `ena_ing_ext_vlan` / `ena_egr_ext_vlan` | 使能入向 / 出向 `COP5` Extended VLAN 规则查找与标签改写 |
| `ena_ing_vlan_filter` / `ena_egr_vlan_filter` | 使能入向 / 出向 `COP2` VLAN Tagging Filter 过滤 |
| `ena_src_mac_learning` | 使能 `COP1` 对进入该端口的报文执行源 MAC 自动学习 |
| `ena_learning_limit` | 使能 `COP1` `LEARNING_LIMITATION_TABLE` 学习数量上限检查 |
| `ena_port_lock` | 端口锁定使能：源 MAC 已在其他桥接端口学习到时，禁止迁移并丢弃报文 |
| `ena_unknown_uc_flood` | 允许未知单播报文向该桥接端口泛洪 |
| `ena_unknown_mc_flood` | 允许未注册组播报文向该桥接端口泛洪 |
| `ena_broadcast_flood` | 允许广播报文向该桥接端口泛洪 |
| `ena_ani_side` | 标识该桥接端口位于 GPON ANI 侧（`1`）或 UNI 侧（`0`），用于水平分割隔离 |
| `ena_us_policer` / `ena_ds_policer` | 使能入向 / 出向 `COP14` `TBM` 硬件令牌桶监管 |
| `ena_mac_bridge` | 使能二层 MAC 桥接查表；清零时跳过 `COP1` 查表按点对点（Cross-Connect）直通转发 |

---

## 3. FID 分配 (`COP0`) 与二层 MAC 转发、学习及老化 (`COP1`)

### 3.1 FID 转发域分配机制 (`COP0`)

`COP0`（`FID`）将报文的 32 位内外层 VLAN 标签键 `(prio_inner, vid_inner, prio_outer, vid_outer)` 映射为 8-bit 桥接转发域标识符 `FID`，支持共享 VLAN 学习（SVL，多个 VID 映射到同一 `FID`）与独立 VLAN 学习（IVL，每个 VID 映射到独立 `FID`）：

1. **只读查找 (`IF_FID_LOOKUP_MC`, `PC = 0`)**：
   - `COP0` 对输入的 32 位 VLAN 键计算 7-bit CRC 哈希值，读取 128 项的 `FID_HASH_TABLE`（ID 2）桶头。
   - 若桶头 `valid == 1`，提取 `[29:16]` 的链表首节点指针装入 `%index`，沿 `FID_ASSIGNMENT_TABLE`（ID 1，256 × 64-bit `LLIST`）遍历冲突链比对 32 位键，命中后返回 64 位表项（其中 `Word 1 [7:0]` 为 `fid`，`Word 1 [8]` 为 `cross_connect`）。
2. **单播查找与未命中自动分配 (`IF_FID_LOOKUP_UC`, `PC = 6`)**：
   - 先执行与 `IF_FID_LOOKUP_MC` 相同的哈希与链表搜索；若未命中，则直接从 `FID_ASSIGNMENT_TABLE` 空闲链分配新节点写入待插入的 `FID` 映射，并在原哈希桶为空时自动将新节点索引写回 `FID_HASH_TABLE`。

### 3.2 二层短转发表查找、源学习与老化状态机 (`COP1`)

`COP1`（`FWD`）管理 `SHORT_FWD_HASH_TABLE`（ID 9，512 × 32-bit 哈希桶头表）、`SHORT_FWD_TABLE`（ID 10 / 12，1024 × 128-bit 冲突链表池）和 `LEARNING_LIMITATION_TABLE`（ID 11，128 × 32-bit 端口学习限制表）：

```mermaid
flowchart TD
    SMAC_IN["入向报文开启源 MAC 学习"] --> RELEARN["调用 COP1 IF_FWD_RELEARN PC=12"]
    RELEARN -->|命中且源端口未变 eq8=1| NOW_UPD["执行 now 刷新时间戳并覆盖写回 Table 2"]
    RELEARN -->|命中但源端口变化 eq8=0 返回 err=6| PORT_LOCK{"PE 检查端口锁定标志"}
    PORT_LOCK -->|端口已锁定| DROP["丢弃帧并递增丢包计数"]
    PORT_LOCK -->|允许迁移| RM_OLD["调用 IF_FWD_REMOVE PC=57 删除旧端口项"]
    RM_OLD --> ADD_NEW["调用 IF_FWD_ADD PC=26 学习新端口项"]
    RELEARN -->|未命中 返回 err=7| ADD_NEW
    ADD_NEW --> LIM_CHK{"Table 3 计数 lt16 检查"}
    LIM_CHK -->|已达上限 lt16=0| LIM_ERR["返回 err=7 递增网桥学习丢弃计数"]
    LIM_CHK -->|未达上限 lt16=1| INS_TBL["写入当前时间戳 插入 Table 2/1 并执行 count 3 +1"]
```

- **目的地址查找 (`IF_FWD_FORWARD`, `PC = 1`)**：以 64 位键（`FID + DMAC` 或 `FID + DIP`）查 `Table 1` 与 `Table 2`。命中时读取高 64 位转发载荷，通过 `mov %data1, 0x100` 与 `or %data1, %data2` 将 `Word 2 [8]` 活动位置 `1` 后以 `add 2, 1` 覆盖写回，并将目标 `bridge_port_index`（单播）或 23 位 `port_map`（组播）返回给 PE。
- **源 MAC 重学习与端口迁移检测 (`IF_FWD_RELEARN`, `PC = 12`)**：查 `Table 1` 与 `Table 2`。若未命中则返回软错误 `%err = 7` 触发 `IF_FWD_ADD`；若已命中，硬件 `[eq8]` 条件比对表中已存的 `source_port` 与当前入向源端口：端口一致时执行 `now` 刷新 `Word 3 [15:0]` 时间戳并原地更新；端口不一致时返回软错误 `%err = 6`。
- **新 MAC 插入与学习上限控制 (`IF_FWD_ADD`, `PC = 26`)**：若表项置位了 `learning_limitation_enable`（`Word 2 [9]`），微码先读取 `Table 3[source_port]` 检查 `[lt16]`（`association_count < learning_limit`），超限则返回 `%err = 7`；通过检查后执行 `now` 打上当前硬件时间戳，插入 `Table 2` 冲突链与 `Table 1` 桶头，并对 `Table 3[source_port]` 执行 `count 3, +1`。
- **硬件老化扫描与自动断链 (`IF_FWD_AGE`, `PC = 0` → `PC = 77` → `PC = 57`)**：`PCTRL` 硬件定时器周期性触发老化线程按索引 `0`–`1023` 调用 `IF_FWD_AGE`。微码通过 `Table 4`（`VARRAY` 视图）读取 128 位表项，将低 64 位键装入 `%key`，检查 `dynamic_enable`（`Word 2 [10] == 1`）与硬件老化条件 `[aged]`；一旦老化到期，微码直接跳转至 `IF_FWD_REMOVE`（`PC = 57`），先对 `Table 3[source_port]` 执行 `count 3, -1`，再执行 `remove 2` 从冲突链摘除节点，并根据 `[first]` 与 `[last]` 标志自动更新或清空 `Table 1` 哈希桶头。

---

## 4. SCE 全局常量表 (`CONSTANTS_TABLE`, ID 64)

`CONSTANTS_TABLE`（ID 64）驻留在每颗 `PE` 本地数据 RAM 中，共 51 个 32 位字（行索引 `0`–`50`），提供报文解析微码所需的协议常量与默认参数：

| 字节偏移 | 表行号 | 字段名称 | 缺省值与硬件说明 |
| --- | --- | --- | --- |
| `0x00` | Row 0 | `default_outer_tpid_a` / `b` | 外层 S-Tag 识别 TPID 组 1（如 `0x88A8`、`0x8100`） |
| `0x04` | Row 1 | `default_outer_tpid_c` / `d` | 外层 S-Tag 识别 TPID 组 2（如 `0x9100`、`0x9200`） |
| `0x08` | Row 2 | `default_inner_tpid_a` / `b` | 内层 C-Tag 识别 TPID 组 1（缺省 `0x8100`） |
| `0x0C` | Row 3 | `default_inner_tpid_c` / `d` | 内层 C-Tag 识别 TPID 组 2 |
| `0x10` | Row 4 `[11:0]` | `default_vid` | 无标签帧内部默认分配的 VID |
| `0x14` | Row 5 `[13:0]` | `packet_len_limit` | 转发引擎允许的最大二层帧长度阈值 |
| `0x1C` | Row 7 `[15:0]` | `pppoe_session_ethertype` | PPPoE 会话阶段协议号（`0x8864`） |
| `0x3C` | Row 15 `[8:0]` | `ani_exception_meter_id` | ANI 侧上送 CPU 异常报文绑定的共享 `TBM` 计量器 ID |
| `0x40` | Row 16 `[0]` | `ani_exception_meter_en` | ANI 侧异常流量硬件限速使能位 |
| `0x44`–`0x50` | Row 17–20 | `local_mac_addr` | 本机管理接口（IP Host / LCT）48-bit MAC 地址及匹配掩码 |
| `0x60` | Row 24 | `fwd_aging_trig_mantissa` | `COP1` 二层动态 MAC 表老化周期尾数与指数配置 |
