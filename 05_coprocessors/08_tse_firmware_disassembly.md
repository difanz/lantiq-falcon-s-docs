# 5.8 TSE 微码固件反汇编逐行详解（`tse0.s` – `tse5.s`）

6 颗表搜索协处理器（`COP0`–`COP5`）上装载的微码映像（`tse0.bin`–`tse5.bin`）经反汇编后得到 `tse0.s`–`tse5.s` 六份汇编源文件，共计 185 条 16 位微码指令、29 项硬件表描述符配置（`.table`）、48 项自定义匹配寄存器初值（`.custom`）以及 16 个导出微码函数入口（`.export`）。以下列出每份反汇编文件的完整源码，并逐行解析全部伪指令与每一条微码指令的机器码位域、寄存器输入输出、硬件表访问及控制流转移行为。

---

## 1. 反汇编伪指令的硬件装载语义

每份 `.s` 文件顶部的伪指令直接对应微码容器中的逻辑地址窗口，在硬件初始化阶段通过 `LINK` 总线向目标 COP 的 `Table 0`（内部控制寄存器空间）发起 `WRITE (cmd = 2)` 命令完成配置：

| 伪指令语法 | 容器地址窗口 | 目标内部寄存器索引 (`Table 0`) | 逐行硬件作用说明 |
| --- | --- | --- | --- |
| `.comment "<str>"` | `0xFC00`–`0xFFFF` | 不写入硬件寄存器 | 存放汇编器版本（`TOOL`）、微码标题（`TITLE`）、微码版本号（`VERSION`）、作者（`AUTHOR`）与功能描述（`DESCRIPTION`） |
| `.export <id>, "<name>", <byte_addr>` | `0xF800` (`INTERFACE`) + `0xE000` (`NAMES`) | 映射为 `EXEC` 命令的入口 PC | 将全局导出函数编号 `<id>`（`1`–`25`）及符号名 `<name>` 绑定到代码段字节偏移 `<byte_addr>`。PE 或主控发起 `EXEC` 命令时，硬件将 `PC` 置为 `<byte_addr> >> 1` |
| `.custom <idx>, <val32>` | `0xF400`–`0xF41F` | `0x300 + <idx>` (`CUSTOM0`–`CUSTOM7`) | 初始化 `CUSTOM` 匹配模式使用的 8 个 32 位协议比较寄存器。容器默认将 `CUSTOM1`–`CUSTOM4` 设为 `0xFFFF0000`（屏蔽 `ETY1`–`ETY4`），其余清零 |
| `.table 0, empty` | `0xC000`–`0xC00F` | `0x000`–`0x003` | 表 0 占位记录（4 个 32 位字全 `0`），硬件跳过不写，因为表 0 自身即为 COP 寄存器控制面 |
| `.table <n>, type=..., func=..., width=..., key=..., mask=..., kmsk=..., size=..., base=..., aux_valid=..., count=..., aux=...` | `0xC010 + (n-1)*0x10` | `0x004 + (n-1)*4` (`TABLEn0`–`TABLEn3`) | 配置当前 COP 物理表 `<n>`（`1`–`6`）的 4 个 32 位硬件控制寄存器：`TABLEn0`（`DATA_MASK[31:16]`、`KEY_SIZE[10:8]`、`ENTRY_SIZE[7:6]`、`FUNCTION[5:3]`、`TYPE[2:0]`）、`TABLEn1`（`SIZE[31:16]`、`BASE[15:0]`）、`TABLEn2`（`AUX_V[31]`、`ENTRY_COUNTER[25:16]`、`AUX[15:0]`）及第四个零填充字。以寄存器头文件定义为准，不能将反汇编器打印字段名重新排列成另一套硬件布局 |
| `.code <byte_addr>` | `0x0000`–`0x3FFF` | `0x200 + (<byte_addr> >> 1)` (`CRAM`) | 指示后续 16 位微码指令按顺序装入代码 RAM（`CRAM`），起始指令地址 `PC = <byte_addr> >> 1` |
| `.code_tail <byte_addr>` | `0x0000`–`0x3FFF` | `0x200 + (<byte_addr> >> 1)` (`CRAM`) | 指示位于 `.table` 记录之后的一条尾部代码记录（仅 `tse1.s` 使用，在表配置完成后将 `PC = 0` 的跳转指令写入 `CRAM[0]`） |

---

## 2. `tse0.s`（`COP0 = FID`，40 条指令）完整反汇编与逐行详解

### 2.1 `tse0.s` 完整反汇编源码

```text
; =============================================================================
; Disassembled by cop-disas from: tse0.bin
; Records: 31 (recorded: 31) | End PC: 0 | Instructions: 40
; =============================================================================

; --- Comment Section (0xFC00) ---
.comment "TOOL:Version 4.54"
.comment "TITLE: FID TSE Micro Program"
.comment "VERSION: 3.11"
.comment "AUTHOR: Schaefer, Brunnbauer, Linortner"
.comment "DESCRIPTION:"
.comment "Implements the microcode for the TSE0 coprocessor."
.comment ""

; --- Interface Exports (0xF800) & Names (0xE000) ---
.export 10, "IF_FID_LOOKUP_MC", 0x0000 ; PC=0 (0x00)
.export 25, "IF_FID_LOOKUP_UC", 0x000c ; PC=6 (0x06)
.export 18, "IF_ETHFILT_SEARCHW", 0x0038 ; PC=28 (0x1c)
.export 24, "IF_ACL_SEARCH_3", 0x0040 ; PC=32 (0x20)

; --- Custom Registers (0xF400..0xF41F) ---
.custom 0, 0x00000000
.custom 1, 0xffff0000
.custom 2, 0xffff0000
.custom 3, 0xffff0000
.custom 4, 0xffff0000
.custom 5, 0x00000000
.custom 6, 0x00000000
.custom 7, 0x00000000

; --- Hardware Table Configurations (0xC000) ---
.table 0, empty
.table 1, type=LLIST, func=GENERIC, width=64, key=32, mask=0, kmsk=0xffff, size=256, base=0x0000, aux_valid=1, count=0, aux=0x0000
.table 2, type=HASH, func=GENERIC, width=32, key=32, mask=0, kmsk=0xffff, size=128, base=0x0200, aux_valid=1, count=0, aux=0x0200
.table 3, type=LIST, func=GENERIC, width=32, key=16, mask=0, kmsk=0xffff, size=64, base=0x0280, aux_valid=1, count=0, aux=0x0280
.table 4, type=LIST, func=GENERIC, width=256, key=128, mask=0, kmsk=0xffff, size=128, base=0x02c0, aux_valid=1, count=0, aux=0x02c0
.table 5, type=LIST, func=TERNARY, width=256, key=128, mask=0, kmsk=0xffff, size=128, base=0x02c0, aux_valid=1, count=0, aux=0x02c0

; --- Code Segment 0 (primary, byte_addr=0x0000, 40 instructions) ---
.code 0x0000

; --- Export ID 10: IF_FID_LOOKUP_MC, byte_addr=0x0000, PC=0 (0x00) ---
IF_FID_LOOKUP_MC:
    settab 2                           ; [PC= 0 (0x00) @0x0000: e010]
    searchr 2, 0, 32                   ; [PC= 1 (0x01) @0x0002: a010]
    [!res1|err] goto 0x05              ; [PC= 2 (0x02) @0x0004: 0305] -> PC=5
    mov %index, %data1.16              ; [PC= 3 (0x03) @0x0006: 7000]
    searchr 1, 0, 64                   ; [PC= 4 (0x04) @0x0008: a088]
    return 64                          ; [PC= 5 (0x05) @0x000a: 0005]

; --- Export ID 25: IF_FID_LOOKUP_UC, byte_addr=0x000c, PC=6 (0x06) ---
IF_FID_LOOKUP_UC:
    settab 2                           ; [PC= 6 (0x06) @0x000c: e010]
    mov %data2, %data1                 ; [PC= 7 (0x07) @0x000e: 7340]
    searchr 2, 0, 32                   ; [PC= 8 (0x08) @0x0010: a010]
    mov %res2, %res1                   ; [PC= 9 (0x09) @0x0012: 7600]
    [err] goto 0x0f                    ; [PC=10 (0x0a) @0x0014: 028f] -> PC=15
    [!res1] goto 0x10                  ; [PC=11 (0x0b) @0x0016: 0110] -> PC=16
    mov %index, %data1.16              ; [PC=12 (0x0c) @0x0018: 7000]
    searchr 1, 0, 64                   ; [PC=13 (0x0d) @0x001a: a088]
    [!res1] goto 0x10                  ; [PC=14 (0x0e) @0x001c: 0110] -> PC=16
    return 64                          ; [PC=15 (0x0f) @0x001e: 0005]
    mov %data1, %data2                 ; [PC=16 (0x10) @0x0020: 7260]
    [res2] goto 0x15                   ; [PC=17 (0x11) @0x0022: 0795] -> PC=21
    add 1, 0, 1                        ; [PC=18 (0x12) @0x0024: d408] (bit10=1 (new chain head))
    [res1] goto 0x16                   ; [PC=19 (0x13) @0x0026: 0196] -> PC=22
    return 64                          ; [PC=20 (0x14) @0x0028: 0005]
    add 1, 0                           ; [PC=21 (0x15) @0x002a: d008]
    [err] goto 0x0f                    ; [PC=22 (0x16) @0x002c: 028f] -> PC=15
    [res2] goto 0x0f                   ; [PC=23 (0x17) @0x002e: 078f] -> PC=15
    mov %data1.16, %index              ; [PC=24 (0x18) @0x0030: 7200]
    add 2, 0                           ; [PC=25 (0x19) @0x0032: d010]
    mov %index, %data1.16              ; [PC=26 (0x1a) @0x0034: 7000]
    mov %data1, %data2 || return 64    ; [PC=27 (0x1b) @0x0036: 7265]

; --- Export ID 18: IF_ETHFILT_SEARCHW, byte_addr=0x0038, PC=28 (0x1c) ---
IF_ETHFILT_SEARCHW:
    search 3                           ; [PC=28 (0x1c) @0x0038: c018]
    [!res1|err] goto 0x1f              ; [PC=29 (0x1d) @0x003a: 031f] -> PC=31
    searchw 3, 0, 32                   ; [PC=30 (0x1e) @0x003c: d818]
    return 32                          ; [PC=31 (0x1f) @0x003e: 0004]

; --- Export ID 24: IF_ACL_SEARCH_3, byte_addr=0x0040, PC=32 (0x20) ---
IF_ACL_SEARCH_3:
    mov %data2, %data1                 ; [PC=32 (0x20) @0x0040: 7340]
    mov %aux, %data1.16                ; [PC=33 (0x21) @0x0042: 7718] (inferred dst=7,src=0,sel=3)
    mov %index, 0                      ; [PC=34 (0x22) @0x0044: 4000]
    read 4, 0, 256                     ; [PC=35 (0x23) @0x0046: 81a0]
    mov %data1, %data2                 ; [PC=36 (0x24) @0x0048: 7260]
    mov %index, %aux                   ; [PC=37 (0x25) @0x004a: 70f8] (dst=0,src=7,sel=3)
    searchr 5, 0, 128                  ; [PC=38 (0x26) @0x004c: a128]
    mov %index, %prev_src || return 32 ; [PC=39 (0x27) @0x004e: 70c4]
```

### 2.2 `tse0.s` 头部伪指令逐行详解（行 7–40）

| 源码行 | 伪指令内容 | 逐行硬件作用与寄存器配置说明 |
| --- | --- | --- |
| `7`–`13` | `.comment "TOOL:Version 4.54"` 等 7 行 | 声明 `COP0`（`FID`）微码由汇编器 `4.54` 生成，微码版本 `3.11`，实现 `TSE0` 协处理器微程序 |
| `16` | `.export 10, "IF_FID_LOOKUP_MC", 0x0000` | 将导出函数 ID `10`（`IF_FID_LOOKUP_MC`，组播/只读 FID 查找）绑定至字节偏移 `0x0000`（入口 `PC = 0`） |
| `17` | `.export 25, "IF_FID_LOOKUP_UC", 0x000c` | 将导出函数 ID `25`（`IF_FID_LOOKUP_UC`，单播 FID 查找与未命中自动插入）绑定至字节偏移 `0x000C`（入口 `PC = 6`） |
| `18` | `.export 18, "IF_ETHFILT_SEARCHW", 0x0038` | 将导出函数 ID `18`（`IF_ETHFILT_SEARCHW`，EtherType 过滤搜索并写回统计位）绑定至字节偏移 `0x0038`（入口 `PC = 28`） |
| `19` | `.export 24, "IF_ACL_SEARCH_3", 0x0040` | 将导出函数 ID `24`（`IF_ACL_SEARCH_3`，ACL 第 4 通道三态搜索）绑定至字节偏移 `0x0040`（入口 `PC = 32`） |
| `22`–`29` | `.custom 0`–`.custom 7` | 将 `CUSTOM0`、`CUSTOM5`–`CUSTOM7` 置为 `0x00000000`，将 `CUSTOM1`–`CUSTOM4` 置为 `0xFFFF0000`（`COP0` 不使用 `CUSTOM` 匹配模式） |
| `32` | `.table 0, empty` | 表 0 占位记录（不写硬件） |
| `33` | `.table 1, type=LLIST, func=GENERIC, width=64, key=32, ..., size=256, base=0x0000, aux=0x0000` | 配置物理表 1（`FID_ASSIGNMENT_TABLE`）：单向冲突链表（`LLIST`），精确匹配（`GENERIC`），每项 64 位（2 字），键宽 32 位，容量 256 项，占用表 RAM `0x0000`–`0x01FF`，空闲链指针 `%aux` 初值 `0x0000` |
| `34` | `.table 2, type=HASH, func=GENERIC, width=32, key=32, ..., size=128, base=0x0200, aux=0x0200` | 配置物理表 2（`FID_HASH_TABLE`）：哈希桶头表（`HASH`），每项 32 位（1 字），键宽 32 位，容量 128 桶，占用表 RAM `0x0200`–`0x027F` |
| `35` | `.table 3, type=LIST, func=GENERIC, width=32, key=16, ..., size=64, base=0x0280, aux=0x0280` | 配置物理表 3（`ETHERTYPE_FILTER_TABLE`）：顺序列表（`LIST`），每项 32 位，键宽 16 位（EtherType），容量 64 项，占用表 RAM `0x0280`–`0x02BF` |
| `36` | `.table 4, type=LIST, func=GENERIC, width=256, key=128, ..., size=128, base=0x02c0, aux=0x02c0` | 配置物理表 4（`ACL_FILTER_TABLE_LANE3` 掩码读取视图）：`GENERIC` 模式列表，每项 256 位（8 字），键宽 128 位，容量 128 项，占用表 RAM `0x02C0`–`0x06BF` |
| `37` | `.table 5, type=LIST, func=TERNARY, width=256, key=128, ..., size=128, base=0x02c0, aux=0x02c0` | 配置物理表 5（`ACL_FILTER_TABLE_LANE3_TERNARY` 三态搜索视图）：与表 4 共享物理基址 `0x02C0`，但匹配模式设为 `TERNARY`（三态掩码匹配） |
| `40` | `.code 0x0000` | 指示后续 40 条指令从 `CRAM` 字节地址 `0x0000`（`PC = 0`）起顺序装载 |

### 2.3 `IF_FID_LOOKUP_MC`（行 43–49，`PC = 0`–`5`）逐行详解

调用前置条件：PE 将 32 位内外层 VLAN 键（`prio_inner:vid_inner:prio_outer:vid_outer`）放入请求帧装入 `%key[31:0]`，发起 `EXEC (PC = 0)`：

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `44` | `0` (`0x00`) | `0xe010` | `settab 2` | `op=0x1c (settab)`, `table=2`, `ret=0`。将当前活动表切换为 `Table 2`（`FID_HASH_TABLE`），准备对 `%key[31:0]` 执行 7 位硬件 CRC 哈希 |
| `45` | `1` (`0x01`) | `0xa010` | `searchr 2, 0, 32` | `op=0x14 (searchr)`, `len=0 (32b)`, `off=0`, `table=2`, `ret=0`。以 `%key[31:0]` 哈希索引 `Table 2`，读取 32 位哈希桶头至 `%data1[31:0]`；若桶有效（`valid == 1`）则置 `%res1 = 1`，否则 `%res1 = 0` |
| `46` | `2` (`0x02`) | `0x0305` | `[!res1\|err] goto 0x05` | `op=0 (branch)`, `cond=6 (!res1\|err)`, `target=0x05`。若哈希桶为空（`%res1 == 0`）或硬件报错（`err == 1`），跳过冲突链搜索直接转至 `PC = 5` 返回未命中 |
| `47` | `3` (`0x03`) | `0x7000` | `mov %index, %data1.16` | `op=0x0e (reg_op)`, `dst=%index`, `src=%data1.16`, `ret=0`。从刚读出的哈希桶 `%data1[29:16]`（`fwd_id_assignent_table_pointer`）提取冲突链首节点索引装入 `%index` |
| `48` | `4` (`0x04`) | `0xa088` | `searchr 1, 0, 64` | `op=0x14 (searchr)`, `len=1 (64b)`, `off=0`, `table=1`, `ret=0`。从 `%index` 指定的首节点开始，在 `Table 1`（`LLIST`）中沿 `next_entry` 遍历冲突链比对 32 位 `%key`；若命中，将该节点的 64 位完整表项（含 `Word 1 [7:0]` 的 `fid`）读入 `%data1[63:0]` 并置 `%res1 = 1` |
| `49` | `5` (`0x05`) | `0x0005` | `return 64` | `op=0 (branch)`, `cond=0 (nop/ret)`, `ret=5 (64b)`。结束微码执行，向 `LINK` 总线返回状态标志（`%res1`、`%err`、`%index`）及 `%data1[63:0]` 的 64 位表项数据 |

### 2.4 `IF_FID_LOOKUP_UC`（行 52–74，`PC = 6`–`27`）逐行详解

调用前置条件：单播帧或主控请求查找 32 位 VLAN 键对应的 `FID`，且当表项不存在时自动在 `Table 1`（`FID_ASSIGNMENT_TABLE`）和 `Table 2`（`FID_HASH_TABLE`）中分配并插入新节点。调用方将 32 位 VLAN 键装入 `%key[31:0]`，同时将待插入的 64 位表项模板装入 `%data1[63:0]`：

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `53` | `6` (`0x06`) | `0xe010` | `settab 2` | 选择 `Table 2`（`FID_HASH_TABLE`）作为当前活动表 |
| `54` | `7` (`0x07`) | `0x7340` | `mov %data2, %data1` | `dst=%data2`, `src=%data1`。将调用方传入的 64 位待插入模板备份到 `%data2`，防止后续 `searchr` 覆盖 `%data1` |
| `55` | `8` (`0x08`) | `0xa010` | `searchr 2, 0, 32` | 对 `%key` 计算哈希并读取 `Table 2` 的 32 位桶头至 `%data1[31:0]`，桶有效标志写入 `%res1` |
| `56` | `9` (`0x09`) | `0x7600` | `mov %res2, %res1` | 将哈希桶是否已存在（`%res1`）备份至 `%res2`：`%res2 == 1` 表示该哈希桶已有冲突链，`%res2 == 0` 表示空桶 |
| `57` | `10` (`0x0a`) | `0x028f` | `[err] goto 0x0f` | `cond=5 (err)`, `target=0x0f`。若哈希查找发生硬件错误，跳至 `PC = 15` 直接返回 |
| `58` | `11` (`0x0b`) | `0x0110` | `[!res1] goto 0x10` | `cond=2 (!res1)`, `target=0x10`。若哈希桶为空（`%res1 == 0`），无需搜索冲突链，直接跳至 `PC = 16` 执行新表项分配与建桶 |
| `59` | `12` (`0x0c`) | `0x7000` | `mov %index, %data1.16` | 哈希桶非空，提取桶头中的冲突链首节点索引 `%data1[29:16]` 装入 `%index` |
| `60` | `13` (`0x0d`) | `0xa088` | `searchr 1, 0, 64` | 在 `Table 1`（`LLIST`）中沿冲突链搜索 `%key`；若命中，将 64 位表项读入 `%data1` 并置 `%res1 = 1`；若走到链尾（`end == 1`）仍未命中，置 `%res1 = 0` 且 `%index` 停留在链尾节点 |
| `61` | `14` (`0x0e`) | `0x0110` | `[!res1] goto 0x10` | 若冲突链中未找到匹配键（`%res1 == 0`），跳至 `PC = 16` 将新节点追加到该冲突链末尾 |
| `62` | `15` (`0x0f`) | `0x0005` | `return 64` | 命中现有表项（或由错误跳转至此），向调用方返回 64 位 `%data1` 结果 |
| `63` | `16` (`0x10`) | `0x7260` | `mov %data1, %data2` | 未命中分支入口：从 `%data2` 恢复调用方最初传入的 64 位新表项数据至 `%data1` |
| `64` | `17` (`0x11`) | `0x0795` | `[res2] goto 0x15` | `cond=15 (res2)`, `target=0x15`。检查 `PC = 9` 保存的 `%res2`：若哈希桶原本非空（`%res2 == 1`），跳至 `PC = 21` 执行链表追加；若原本为空桶（`%res2 == 0`），顺序执行 `PC = 18` 创建新链头 |
| `65` | `18` (`0x12`) | `0xd408` | `add 1, 0, 1` | `op=0x1a (add)`, `bit10=1 (new_head)`, `ov=0`, `table=1`。哈希桶为空时，从 `Table 1` 空闲池（`%aux`）分配一个新槽位作为独立冲突链首节点写入 `%data1`（置 `valid = 1, end = 1`），新槽位索引存入 `%index` |
| `66` | `19` (`0x13`) | `0x0196` | `[res1] goto 0x16` | `cond=3 (res1)`, `target=0x16`。若新链头分配成功（`%res1 == 1`），跳至 `PC = 22` 继续回填 `Table 2` 哈希桶头 |
| `67` | `20` (`0x14`) | `0x0005` | `return 64` | 若分配失败（`%res1 == 0`），直接返回 64 位响应 |
| `68` | `21` (`0x15`) | `0xd008` | `add 1, 0` | `op=0x1a (add)`, `bit10=0 (append)`, `ov=0`, `table=1`。哈希桶非空时，从 `Table 1` 空闲池分配新槽位写入 `%data1`，并自动将原链尾节点的 `end` 清零、`next_entry` 指向新槽位 `%index` |
| `69` | `22` (`0x16`) | `0x028f` | `[err] goto 0x0f` | 若 `add` 触发 `OUT_OF_MEMORY`（表满）等硬件错误，跳至 `PC = 15` 返回错误码 |
| `70` | `23` (`0x17`) | `0x078f` | `[res2] goto 0x0f` | 若哈希桶原本已存在（`%res2 == 1`），`Table 2` 的桶头指针无需变动，直接跳至 `PC = 15` 返回新插入的 64 位表项 |
| `71` | `24` (`0x18`) | `0x7200` | `mov %data1.16, %index` | 哈希桶原本为空（`%res2 == 0`）：将刚在 `Table 1` 中分配到的首节点索引 `%index` 写入 `%data1[29:16]`，构造 `Table 2` 的桶头字 |
| `72` | `25` (`0x19`) | `0xd010` | `add 2, 0` | `op=0x1a (add)`, `table=2`。将构造好的桶头指针（`valid = 1`, `pointer = %data1.16`）写入 `Table 2`（`FID_HASH_TABLE`）对应哈希桶 |
| `73` | `26` (`0x1a`) | `0x7000` | `mov %index, %data1.16` | 将 `Table 1` 新节点的索引从 `%data1.16` 恢复回 `%index` 寄存器，以便返回给调用方 |
| `74` | `27` (`0x1b`) | `0x7265` | `mov %data1, %data2 \|\| return 64` | `op=0x0e`, `dst=%data1`, `src=%data2`, `ret=5 (64b)`。将 `%data2` 中保存的 64 位表项恢复至 `%data1`，并在同一周期返回 64 位结果 |

### 2.5 `IF_ETHFILT_SEARCHW`（行 77–81，`PC = 28`–`31`）逐行详解

调用前置条件：调用方将端口 EtherType 子表起始下标装入 `%index`，待比对的 16 位 EtherType 装入 `%key[15:0]`，命中后待写回的 32 位字装入 `%data1[31:0]`：

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `78` | `28` (`0x1c`) | `0xc018` | `search 3` | `op=0x18 (search)`, `table=3`, `ret=0`。从 `%index` 起在 `Table 3`（`ETHERTYPE_FILTER_TABLE`，`LIST`）中顺序比对 16 位 `ethertype` 直至命中或遇到 `end == 1`。命中时 `%res1 = 1` 且 `%index` 指向命中项 |
| `79` | `29` (`0x1d`) | `0x031f` | `[!res1\|err] goto 0x1f` | 若未命中（`%res1 == 0`）或越界出错（`err == 1`），跳过写操作直接转至 `PC = 31` 返回 |
| `80` | `30` (`0x1e`) | `0xd818` | `searchw 3, 0, 32` | `op=0x1b (searchw)`, `len=0 (32b)`, `off=0`, `table=3`。命中时将 `%data1[31:0]` 写回 `Table 3` 当前命中的 `%index` 槽位 |
| `81` | `31` (`0x1f`) | `0x0004` | `return 32` | 返回 32 位状态与 `%data1[31:0]` |

### 2.6 `IF_ACL_SEARCH_3`（行 84–92，`PC = 32`–`39`）逐行详解

该 8 指令序列在 `COP0`（`IF_ACL_SEARCH_3`）、`COP2`（`IF_ACL_SEARCH_1`）、`COP3`（`IF_ACL_SEARCH_2`）与 `COP5`（`IF_ACL_SEARCH_0`）中完全一致（仅 `COP5` 使用表 `5`/`6`，其余使用表 `4`/`5`）。调用前置条件：PE 将 128 位报文特征键装入 `%key[127:0]`，将当前 ACL 搜索起始规则索引装入 `%data1[29:16]`（即 `%data1.16`），发起 `EXEC`：

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `85` | `32` (`0x20`) | `0x7340` | `mov %data2, %data1` | 将输入 `%data1` 备份至 `%data2`，防止后续 `read` 256 位掩码项时冲掉输入参数 |
| `86` | `33` (`0x21`) | `0x7718` | `mov %aux, %data1.16` | `dst=7 (%aux)`, `src=0 (%data1.16)`, `sel=3`。推测为暂存规则起始索引；`0x7718` 在原打印器中无操作数名称，`%data1[29:16]` 的具体切片未证实 |
| `87` | `34` (`0x22`) | `0x4000` | `mov %index, 0` | `op=0x08 (mov_imm index)`, `imm=0`。将表索引 `%index` 清零，指向 ACL 表的第 0 号槽位（全局掩码槽位） |
| `88` | `35` (`0x23`) | `0x81a0` | `read 4, 0, 256` | `op=0x10 (read)`, `len=3 (256b)`, `off=0`, `table=4`。从 `Table 4`（`GENERIC` 视图）索引 `0` 读取 256 位初始掩码项至 `%data1` / 内部三态掩码锁存器 |
| `89` | `36` (`0x24`) | `0x7260` | `mov %data1, %data2` | 从 `%data2` 恢复原始输入数据至 `%data1` |
| `90` | `37` (`0x25`) | `0x70f8` | `mov %index, %aux` | `dst=0 (%index)`, `src=7 (%aux)`, `sel=3`。将 `%aux` 中暂存的规则起始索引恢复到 `%index` |
| `91` | `38` (`0x26`) | `0xa128` | `searchr 5, 0, 128` | `op=0x14 (searchr)`, `len=2 (128b)`, `off=0`, `table=5`。在 `Table 5`（`TERNARY` 视图）中从 `%index` 起执行硬件三态匹配搜索，命中时读取 128 位规则动作载荷并记录命中规则索引至 `%prev_src` |
| `92` | `39` (`0x27`) | `0x70c4` | `mov %index, %prev_src \|\| return 32` | `dst=%index`, `src=%prev_src`, `ret=4 (32b)`。将命中的规则下标从 `%prev_src` 装入 `%index` 并返回 32 位动作控制字 |

---

## 3. `tse1.s`（`COP1 = FWD`，85 条指令）完整反汇编与逐行详解

### 3.1 `tse1.s` 完整反汇编源码

```text
; =============================================================================
; Disassembled by cop-disas from: tse1.bin
; Records: 37 (recorded: 37) | End PC: 0 | Instructions: 85
; =============================================================================

; --- Comment Section (0xFC00) ---
.comment "TOOL:Version 4.54"
.comment "TITLE: FWD TSE Micro Program"
.comment "VERSION: 3.1"
.comment "AUTHOR: Schaefer, Brunnbauer, Linortner"
.comment "DESCRIPTION:"
.comment "Implements the microcode for the TSE1 coprocessor"
.comment ""

; --- Interface Exports (0xF800) & Names (0xE000) ---
.export  1, "IF_FWD_AGE", 0x0000 ; PC=0 (0x00)
.export  2, "IF_FWD_FORWARD", 0x0002 ; PC=1 (0x01)
.export  3, "IF_FWD_RELEARN", 0x0018 ; PC=12 (0x0c)
.export  4, "IF_FWD_ADD", 0x0034 ; PC=26 (0x1a)
.export  5, "IF_FWD_REMOVE", 0x0072 ; PC=57 (0x39)

; --- Custom Registers (0xF400..0xF41F) ---
.custom 0, 0x00000000
.custom 1, 0xffff0000
.custom 2, 0xffff0000
.custom 3, 0xffff0000
.custom 4, 0xffff0000
.custom 5, 0x00000000
.custom 6, 0x00000000
.custom 7, 0x00000000

; --- Hardware Table Configurations (0xC000) ---
.table 0, empty
.table 1, type=HASH, func=GENERIC, width=32, key=64, mask=0, kmsk=0xffff, size=512, base=0x0000, aux_valid=1, count=0, aux=0x0000
.table 2, type=LLIST, func=GENERIC, width=128, key=64, mask=0, kmsk=0xffff, size=1024, base=0x0200, aux_valid=1, count=0, aux=0x0200
.table 3, type=ARRAY, func=GENERIC, width=32, key=0, mask=0, kmsk=0xffff, size=128, base=0x1200, aux_valid=1, count=0, aux=0x1200
.table 4, type=VARRAY, func=GENERIC, width=128, key=0, mask=0, kmsk=0xffff, size=1024, base=0x0200, aux_valid=1, count=0, aux=0x0200

; --- Code Segment 0 (primary, byte_addr=0x0002, 84 instructions) ---
; Note: PC=0 (0x0000: 00cd = `goto 0x4d`) is placed in `.code_tail 0x0000` at the end of this file.
.code 0x0002

; --- Export ID 2: IF_FWD_FORWARD, byte_addr=0x0002, PC=1 (0x01) ---
IF_FWD_FORWARD:
    settab 1                           ; [PC= 1 (0x01) @0x0002: e008]
    searchr 1, 0, 32                   ; [PC= 2 (0x02) @0x0004: a008]
    [!res1|err] goto 0x0b              ; [PC= 3 (0x03) @0x0006: 030b] -> PC=11
    mov %index, %data1.16              ; [PC= 4 (0x04) @0x0008: 7000]
    searchr 2, 64, 64                  ; [PC= 5 (0x05) @0x000a: a290]
    [!res1|err] goto 0x0b              ; [PC= 6 (0x06) @0x000c: 030b] -> PC=11
    mov %data2, %data1                 ; [PC= 7 (0x07) @0x000e: 7340]
    mov %data1, 0x100                  ; [PC= 8 (0x08) @0x0010: 5800]
    or %data1, %data2                  ; [PC= 9 (0x09) @0x0012: 7240]
    add 2, 1                           ; [PC=10 (0x0a) @0x0014: d210]
    return 64                          ; [PC=11 (0x0b) @0x0016: 0005]

; --- Export ID 3: IF_FWD_RELEARN, byte_addr=0x0018, PC=12 (0x0c) ---
IF_FWD_RELEARN:
    settab 2                           ; [PC=12 (0x0c) @0x0018: e010]
    mov %data2, %data1                 ; [PC=13 (0x0d) @0x001a: 7340]
    searchr 1, 0, 32                   ; [PC=14 (0x0e) @0x001c: a008]
    [!res1] goto 0x18                  ; [PC=15 (0x0f) @0x001e: 0118] -> PC=24
    mov %index, %data1.16              ; [PC=16 (0x10) @0x0020: 7000]
    searchr 2, 64, 64                  ; [PC=17 (0x11) @0x0022: a290]
    [!res1] goto 0x18                  ; [PC=18 (0x12) @0x0024: 0118] -> PC=24
    [eq8] goto 0x15                    ; [PC=19 (0x13) @0x0026: 0415] -> PC=21
    mov %err, 6 || return 32           ; [PC=20 (0x14) @0x0028: 6034]
    now                                ; [PC=21 (0x15) @0x002a: 7820]
    add 2, 1                           ; [PC=22 (0x16) @0x002c: d210]
    mov %index, 0 || return 32         ; [PC=23 (0x17) @0x002e: 4004]
    mov %err, 7                        ; [PC=24 (0x18) @0x0030: 6038]
    mov %index, 0 || return 32         ; [PC=25 (0x19) @0x0032: 4004]

; --- Export ID 4: IF_FWD_ADD, byte_addr=0x0034, PC=26 (0x1a) ---
IF_FWD_ADD:
    settab 2                           ; [PC=26 (0x1a) @0x0034: e010]
    mov %data2, %data1                 ; [PC=27 (0x1b) @0x0036: 7340]
    [!data1.9] goto 0x21               ; [PC=28 (0x1c) @0x0038: 24a1] -> PC=33
    mov %index, %data1                 ; [PC=29 (0x1d) @0x003a: 7080]
    searchr 3, 0, 32                   ; [PC=30 (0x1e) @0x003c: a018]
    [lt16] goto 0x21                   ; [PC=31 (0x1f) @0x003e: 0521] -> PC=33
    mov %err, 7 || return 32           ; [PC=32 (0x20) @0x0040: 603c]
    searchr 1, 0, 32                   ; [PC=33 (0x21) @0x0042: a008]
    mov %res2, %res1                   ; [PC=34 (0x22) @0x0044: 7600]
    [!res1] goto 0x29                  ; [PC=35 (0x23) @0x0046: 0129] -> PC=41
    settab 2                           ; [PC=36 (0x24) @0x0048: e010]
    mov %index, %data1.16              ; [PC=37 (0x25) @0x004a: 7000]
    searchr 2, 0, 128                  ; [PC=38 (0x26) @0x004c: a110]
    [!res1] goto 0x29                  ; [PC=39 (0x27) @0x004e: 0129] -> PC=41
    mov %err, 4 || return 32           ; [PC=40 (0x28) @0x0050: 6024]
    mov %data1, %data2                 ; [PC=41 (0x29) @0x0052: 7260]
    now                                ; [PC=42 (0x2a) @0x0054: 7820]
    [res2] goto 0x2f                   ; [PC=43 (0x2b) @0x0056: 07af] -> PC=47
    add 2, 0, 1                        ; [PC=44 (0x2c) @0x0058: d410] (bit10=1 (new chain head))
    [res1] goto 0x30                   ; [PC=45 (0x2d) @0x005a: 01b0] -> PC=48
    return 32                          ; [PC=46 (0x2e) @0x005c: 0004]
    add 2, 0                           ; [PC=47 (0x2f) @0x005e: d010]
    [err] goto 0x38                    ; [PC=48 (0x30) @0x0060: 02b8] -> PC=56
    [res2] goto 0x34                   ; [PC=49 (0x31) @0x0062: 07b4] -> PC=52
    mov %data1.16, %index              ; [PC=50 (0x32) @0x0064: 7200]
    add 1, 0                           ; [PC=51 (0x33) @0x0066: d008]
    mov %data1, %data2                 ; [PC=52 (0x34) @0x0068: 7260]
    [!data1.9] goto 0x38               ; [PC=53 (0x35) @0x006a: 24b8] -> PC=56
    mov %index, %data1                 ; [PC=54 (0x36) @0x006c: 7080]
    count 3, +1                        ; [PC=55 (0x37) @0x006e: 9918]
    mov %index, 0 || return 32         ; [PC=56 (0x38) @0x0070: 4004]

; --- Export ID 5: IF_FWD_REMOVE, byte_addr=0x0072, PC=57 (0x39) ---
IF_FWD_REMOVE:
    settab 1                           ; [PC=57 (0x39) @0x0072: e008]
    searchr 1, 0, 32                   ; [PC=58 (0x3a) @0x0074: a008]
    [!res1|err] goto 0x4c              ; [PC=59 (0x3b) @0x0076: 034c] -> PC=76
    mov %index, %data1.16              ; [PC=60 (0x3c) @0x0078: 7000]
    searchr 2, 64, 32                  ; [PC=61 (0x3d) @0x007a: a210]
    [!res1|err] goto 0x4c              ; [PC=62 (0x3e) @0x007c: 034c] -> PC=76
    [!data1.9] goto 0x42               ; [PC=63 (0x3f) @0x007e: 24c2] -> PC=66
    mov %index, %data1                 ; [PC=64 (0x40) @0x0080: 7080]
    count 3, -1                        ; [PC=65 (0x41) @0x0082: 9998]
    searchr 1, 0, 32                   ; [PC=66 (0x42) @0x0084: a008]
    mov %index, %data1.16              ; [PC=67 (0x43) @0x0086: 7000]
    remove 2                           ; [PC=68 (0x44) @0x0088: c810]
    [first] goto 0x47                  ; [PC=69 (0x45) @0x008a: 05c7] -> PC=71
    return 32                          ; [PC=70 (0x46) @0x008c: 0004]
    [last] goto 0x4b                   ; [PC=71 (0x47) @0x008e: 064b] -> PC=75
    mov %index, %next                  ; [PC=72 (0x48) @0x0090: 70a0]
    mov %data1.16, %index              ; [PC=73 (0x49) @0x0092: 7200]
    add 1, 1 || return 32              ; [PC=74 (0x4a) @0x0094: d20c]
    remove 1 || return 32              ; [PC=75 (0x4b) @0x0096: c80c]
    mov %err, 7 || return 32           ; [PC=76 (0x4c) @0x0098: 603c]
    settab 4                           ; [PC=77 (0x4d) @0x009a: e020]
    searchr 4, 0, 128                  ; [PC=78 (0x4e) @0x009c: a120]
    [!res1] goto 0x54                  ; [PC=79 (0x4f) @0x009e: 0154] -> PC=84
    mov %key, %data1                   ; [PC=80 (0x50) @0x00a0: 7540]
    searchr 4, 64, 64                  ; [PC=81 (0x51) @0x00a2: a2a0]
    [!data1.10] goto 0x54              ; [PC=82 (0x52) @0x00a4: 2554] -> PC=84
    [aged] goto 0x39                   ; [PC=83 (0x53) @0x00a6: 06b9] -> IF_FWD_REMOVE (PC=57)
    mov %index, 0 || return 32         ; [PC=84 (0x54) @0x00a8: 4004]

; --- Code Segment 1 (emitted after .table, byte_addr=0x0000, 1 instructions) ---
.code_tail 0x0000

; --- Export ID 1: IF_FWD_AGE, byte_addr=0x0000, PC=0 (0x00) ---
IF_FWD_AGE:
    goto 0x4d                          ; [PC= 0 (0x00) @0x0000: 00cd] -> PC=77
```

### 3.2 `tse1.s` 头部伪指令逐行详解（行 7–41 与行 140）

| 源码行 | 伪指令内容 | 逐行硬件作用与寄存器配置说明 |
| --- | --- | --- |
| `7`–`13` | `.comment "TOOL:Version 4.54"` 等 7 行 | 声明 `COP1`（`FWD`）微码标题为 `FWD TSE Micro Program`，版本 `3.1` |
| `16` | `.export 1, "IF_FWD_AGE", 0x0000` | 将导出函数 ID `1`（`IF_FWD_AGE`，单步老化扫描）绑定至 `0x0000`（`PC = 0`） |
| `17` | `.export 2, "IF_FWD_FORWARD", 0x0002` | 将导出函数 ID `2`（`IF_FWD_FORWARD`，目的地址转发查表）绑定至 `0x0002`（`PC = 1`） |
| `18` | `.export 3, "IF_FWD_RELEARN", 0x0018` | 将导出函数 ID `3`（`IF_FWD_RELEARN`，源 MAC 刷新与端口迁移检测）绑定至 `0x0018`（`PC = 12`） |
| `19` | `.export 4, "IF_FWD_ADD", 0x0034` | 将导出函数 ID `4`（`IF_FWD_ADD`，新表项插入与端口学习计数递增）绑定至 `0x0034`（`PC = 26`） |
| `20` | `.export 5, "IF_FWD_REMOVE", 0x0072` | 将导出函数 ID `5`（`IF_FWD_REMOVE`，表项删除、冲突链修补与端口计数递减）绑定至 `0x0072`（`PC = 57`） |
| `23`–`30` | `.custom 0`–`.custom 7` | 写入 `CUSTOM0`–`CUSTOM7` 默认初值 |
| `33` | `.table 0, empty` | 表 0 占位记录 |
| `34` | `.table 1, type=HASH, func=GENERIC, width=32, key=64, ..., size=512, base=0x0000, aux=0x0000` | 配置物理表 1（`SHORT_FWD_HASH_TABLE`）：512 桶哈希表，每桶 32 位，输入键宽 64 位（`FID + MAC` 或 `FID + IPv4`），占用表 RAM `0x0000`–`0x01FF` |
| `35` | `.table 2, type=LLIST, func=GENERIC, width=128, key=64, ..., size=1024, base=0x0200, aux=0x0200` | 配置物理表 2（`SHORT_FWD_TABLE` 链表视图）：1024 项单向冲突链表（`LLIST`），每项 128 位（4 字：低 64 位键 + 高 64 位载荷），键宽 64 位，占用表 RAM `0x0200`–`0x11FF`，空闲链头 `%aux` 初值 `0x0200` |
| `36` | `.table 3, type=ARRAY, func=GENERIC, width=32, key=0, ..., size=128, base=0x1200, aux=0x1200` | 配置物理表 3（`LEARNING_LIMITATION_TABLE`）：128 项定长数组（`ARRAY`），每项 32 位（高 16 位上限 `learning_limit`，低 16 位当前计数 `association_count`），占用表 RAM `0x1200`–`0x127F` |
| `37` | `.table 4, type=VARRAY, func=GENERIC, width=128, key=0, ..., size=1024, base=0x0200, aux=0x0200` | 配置物理表 4（`SHORT_FWD_TABLE_MAC_ALTERNATE` 老化数组视图）：与 `Table 2` 共享物理基址 `0x0200`，类型设为带有效位的定长数组（`VARRAY`），键宽 `0`，供 `IF_FWD_AGE` 按下标 `0`–`1023` 直接读取 128 位表项 |
| `41` | `.code 0x0002` | 主代码段从字节偏移 `0x0002`（`PC = 1`）开始装载 `84` 条指令（`PC = 1`–`84`） |
| `140` | `.code_tail 0x0000` | 在 `.table` 记录之后单独发出一笔 2 字节代码记录写入 `0x0000`（`PC = 0`），使复位/老化入口跳往 `PC = 77`（`0x4d`） |

### 3.3 `IF_FWD_FORWARD`（行 44–55，`PC = 1`–`11`）逐行详解

调用前置条件：PE 将 64 位目的转发键（`FID + DMAC` 或 `FID + DIP`）装入 `%key[63:0]`，发起 `EXEC (PC = 1)`：

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `45` | `1` (`0x01`) | `0xe008` | `settab 1` | `op=0x1c`, `table=1`。选择 `Table 1`（`SHORT_FWD_HASH_TABLE`）作为当前活动表 |
| `46` | `2` (`0x02`) | `0xa008` | `searchr 1, 0, 32` | 对 64 位 `%key` 计算 9 位 CRC 哈希，从 `Table 1` 读取 32 位哈希桶头至 `%data1[31:0]`，桶有效标志存入 `%res1` |
| `47` | `3` (`0x03`) | `0x030b` | `[!res1\|err] goto 0x0b` | 若哈希桶为空（`%res1 == 0`）或出错，跳至 `PC = 11` 返回未命中（由 PE 执行未知单播/组播泛洪） |
| `48` | `4` (`0x04`) | `0x7000` | `mov %index, %data1.16` | 提取桶头中的冲突链首节点索引 `%data1[29:16]` 装入 `%index` |
| `49` | `5` (`0x05`) | `0xa290` | `searchr 2, 64, 64` | `op=0x14 (searchr)`, `len=1 (64b)`, `off=2 (64b)`, `table=2`。在 `Table 2`（`LLIST`）中沿冲突链比对低 64 位键；若命中，从表项位偏移 `64` 起读取高 64 位载荷（`Word 2`–`Word 3`）至 `%data1[63:0]`，并置 `%res1 = 1` |
| `50` | `6` (`0x06`) | `0x030b` | `[!res1\|err] goto 0x0b` | 若冲突链遍历完毕仍未命中，跳至 `PC = 11` 返回未命中 |
| `51` | `7` (`0x07`) | `0x7340` | `mov %data2, %data1` | 命中表项：将刚读出的高 64 位转发载荷备份至 `%data2[63:0]` |
| `52` | `8` (`0x08`) | `0x5800` | `mov %data1, 0x100` | `op=0x0b (mov_imm data1)`, `imm=0x100`。将立即数 `0x00000100`（bit 8 转发命中活动标志位）装入 `%data1` |
| `53` | `9` (`0x09`) | `0x7240` | `or %data1, %data2` | `op=0x0e`, `subop=or`。执行 `%data1 = %data1 \| %data2`，在保持原 64 位转发载荷不变的同时将 `%data1[8]` 置 `1` |
| `54` | `10` (`0x0a`) | `0xd210` | `add 2, 1` | `op=0x1a (add)`, `ov=1 (overwrite)`, `table=2`。将置位了活动标志的 `%data1` 原地覆盖写回 `Table 2` 当前命中的 `%index` 槽位高 64 位 |
| `55` | `11` (`0x0b`) | `0x0005` | `return 64` | 向 PE 返回 64 位转发控制载荷（含目标桥接端口或组播端口位图）与命中标志 `%res1` |

### 3.4 `IF_FWD_RELEARN`（行 58–72，`PC = 12`–`25`）逐行详解

调用前置条件：PE 入向线程在收到开启源学习的报文时，将 64 位源键（`FID + SMAC`）装入 `%key[63:0]`，将携带当前入向源端口 `source_port`（位于 `bit 7:0`）的 64 位控制字装入 `%data1[63:0]`，发起 `EXEC (PC = 12)`：

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `59` | `12` (`0x0c`) | `0xe010` | `settab 2` | 选择 `Table 2`（`SHORT_FWD_TABLE`）准备后续比较 |
| `60` | `13` (`0x0d`) | `0x7340` | `mov %data2, %data1` | 将包含入向 `source_port`（`%data1[7:0]`）的输入控制字保存至 `%data2`，供硬件 `[eq8]` 比较器作为右操作数 |
| `61` | `14` (`0x0e`) | `0xa008` | `searchr 1, 0, 32` | 在 `Table 1`（`SHORT_FWD_HASH_TABLE`）中查找源 MAC 的哈希桶头 |
| `62` | `15` (`0x0f`) | `0x0118` | `[!res1] goto 0x18` | 若哈希桶为空（`%res1 == 0`，该源 MAC 尚未学习），跳至 `PC = 24` 返回软错误 `7`（通知 PE 调用 `IF_FWD_ADD` 执行新学习） |
| `63` | `16` (`0x10`) | `0x7000` | `mov %index, %data1.16` | 提取冲突链首节点索引装入 `%index` |
| `64` | `17` (`0x11`) | `0xa290` | `searchr 2, 64, 64` | 在 `Table 2` 中搜索源 MAC 并读出已存表项的高 64 位控制字至 `%data1`。此时硬件自动比对 `%data1[7:0]`（已存源端口）与 `%data2[7:0]`（当前入向源端口）并更新 `[eq8]` 标志 |
| `65` | `18` (`0x12`) | `0x0118` | `[!res1] goto 0x18` | 若冲突链中未找到该源 MAC（`%res1 == 0`），跳至 `PC = 24` 返回软错误 `7` |
| `66` | `19` (`0x13`) | `0x0415` | `[eq8] goto 0x15` | `cond=8 (eq8)`, `target=0x15`。若已存 `source_port` 与当前入向端口相等（`eq8 == 1`，端口未迁移），跳至 `PC = 21` 刷新老化时间戳 |
| `67` | `20` (`0x14`) | `0x6034` | `mov %err, 6 \|\| return 32` | `op=0x0c (mov_imm err)`, `err=6`, `ret=4 (32b)`。源 MAC 已存在但源端口发生迁移（`eq8 == 0`），立即置软错误码 `%err = 6`（`SOFT_ERR_1`）并返回 32 位响应，由 PE 检查端口锁定标志后决定是否先删后加 |
| `68` | `21` (`0x15`) | `0x7820` | `now` | `op=0x0f (special)`, `subop=4 (now)`。端口未变化：硬件将内部全局老化计时器的当前时间戳写入 `%data1` 的 `timestamp` 字段（`Word 3 [15:0]`） |
| `69` | `22` (`0x16`) | `0xd210` | `add 2, 1` | `ov=1`。将刷新了老化时间戳的 `%data1` 原地覆盖写回 `Table 2` 当前命中的 `%index` 槽位 |
| `70` | `23` (`0x17`) | `0x4004` | `mov %index, 0 \|\| return 32` | 将 `%index` 清零并返回 32 位成功响应（`%err = 0`） |
| `71` | `24` (`0x18`) | `0x6038` | `mov %err, 7` | 未命中分支：置软错误码 `%err = 7`（`SOFT_ERR_2`，指示源 MAC 未在表中） |
| `72` | `25` (`0x19`) | `0x4004` | `mov %index, 0 \|\| return 32` | 清零 `%index` 并返回 32 位响应 |

### 3.5 `IF_FWD_ADD`（行 75–106，`PC = 26`–`56`）逐行详解

调用前置条件：PE 或主控将 64 位键（`FID + MAC/IPv4`）装入 `%key[63:0]`，将待写入的高 64 位控制字（含 `learning_limitation_enable` 即 `%data1.9`、以及 `source_port` 即 `%data1[7:0]`）装入 `%data1[63:0]`，发起 `EXEC (PC = 26)`：

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `76` | `26` (`0x1a`) | `0xe010` | `settab 2` | 选择 `Table 2`（`SHORT_FWD_TABLE`） |
| `77` | `27` (`0x1b`) | `0x7340` | `mov %data2, %data1` | 将待插入的 64 位控制字备份至 `%data2` |
| `78` | `28` (`0x1c`) | `0x24a1` | `[!data1.9] goto 0x21` | `op=1 (bit_branch)`, `inv=1`, `bit=9`, `target=0x21`。测试 `%data1[9]`（`learning_limitation_enable`）：若为 `0`（不限制学习数量，如静态项或未开启限制的端口），跳过 `Table 3` 检查直接转至 `PC = 33` |
| `79` | `29` (`0x1d`) | `0x7080` | `mov %index, %data1` | 开启了端口学习限制：将 `%data1` 低位的 `source_port`（桥接端口索引）装入 `%index` |
| `80` | `30` (`0x1e`) | `0xa018` | `searchr 3, 0, 32` | 按 `%index` 读取 `Table 3`（`LEARNING_LIMITATION_TABLE`）的 32 位表项至 `%data1`；硬件自动比较低 16 位 `association_count` 与高 16 位 `learning_limit`，若 `count < limit` 则置 `lt16 = 1` |
| `81` | `31` (`0x1f`) | `0x0521` | `[lt16] goto 0x21` | `cond=10 (lt16)`, `target=0x21`。若当前已学习数量未达到上限（`lt16 == 1`），跳至 `PC = 33` 继续执行哈希查重与插入 |
| `82` | `32` (`0x20`) | `0x603c` | `mov %err, 7 \|\| return 32` | 已达到该端口的 MAC 学习数量上限（`lt16 == 0`），拒绝学习并返回软错误 `%err = 7` |
| `83` | `33` (`0x21`) | `0xa008` | `searchr 1, 0, 32` | 对 64 位 `%key` 查 `Table 1`（`SHORT_FWD_HASH_TABLE`）获取 32 位哈希桶头 |
| `84` | `34` (`0x22`) | `0x7600` | `mov %res2, %res1` | 将哈希桶是否已存在（`%res1`）保存至 `%res2` |
| `85` | `35` (`0x23`) | `0x0129` | `[!res1] goto 0x29` | 若哈希桶为空（`%res1 == 0`），必不重复，直接跳至 `PC = 41` 分配新表项 |
| `86` | `36` (`0x24`) | `0xe010` | `settab 2` | 哈希桶非空，切换至 `Table 2` 检查该键是否已在冲突链中 |
| `87` | `37` (`0x25`) | `0x7000` | `mov %index, %data1.16` | 将冲突链首节点索引装入 `%index` |
| `88` | `38` (`0x26`) | `0xa110` | `searchr 2, 0, 128` | 在 `Table 2` 中沿冲突链搜索 `%key` |
| `89` | `39` (`0x27`) | `0x0129` | `[!res1] goto 0x29` | 若冲突链中不存在该键（`%res1 == 0`），跳至 `PC = 41` 执行插入 |
| `90` | `40` (`0x28`) | `0x6024` | `mov %err, 4 \|\| return 32` | 表项已存在（`%res1 == 1`），置错误码 `%err = 4`（`ENTRY_EXISTS`）并立即返回 |
| `91` | `41` (`0x29`) | `0x7260` | `mov %data1, %data2` | 从 `%data2` 恢复待插入的高 64 位控制载荷至 `%data1` |
| `92` | `42` (`0x2a`) | `0x7820` | `now` | 将当前硬件老化时间戳写入 `%data1` 的 `timestamp` 字段 |
| `93` | `43` (`0x2b`) | `0x07af` | `[res2] goto 0x2f` | 若哈希桶原本非空（`%res2 == 1`），跳至 `PC = 47` 追加到现有冲突链尾 |
| `94` | `44` (`0x2c`) | `0xd410` | `add 2, 0, 1` | 哈希桶原本为空（`%res2 == 0`）：在 `Table 2` 中分配新槽位创建独立链首节点（`bit10 = 1`） |
| `95` | `45` (`0x2d`) | `0x01b0` | `[res1] goto 0x30` | 若分配成功（`%res1 == 1`），跳至 `PC = 48` |
| `96` | `46` (`0x2e`) | `0x0004` | `return 32` | 若分配失败，直接返回 32 位响应 |
| `97` | `47` (`0x2f`) | `0xd010` | `add 2, 0` | 哈希桶非空分支：在 `Table 2` 中分配新槽位并链接到原冲突链尾节点的 `next_entry` 之后（`bit10 = 0`） |
| `98` | `48` (`0x30`) | `0x02b8` | `[err] goto 0x38` | 若 `add` 发生表满错误（`err == 1`），跳至 `PC = 56` 退出（不递增端口学习计数） |
| `99` | `49` (`0x31`) | `0x07b4` | `[res2] goto 0x34` | 若哈希桶原本已存在（`%res2 == 1`），跳过 `Table 1` 桶头写入，直接转至 `PC = 52` |
| `100` | `50` (`0x32`) | `0x7200` | `mov %data1.16, %index` | 哈希桶原本为空：将 `Table 2` 新分配的首节点索引 `%index` 填入 `%data1[29:16]` |
| `101` | `51` (`0x33`) | `0xd008` | `add 1, 0` | 将新桶头写入 `Table 1`（`SHORT_FWD_HASH_TABLE`）对应哈希桶 |
| `102` | `52` (`0x34`) | `0x7260` | `mov %data1, %data2` | 从 `%data2` 恢复控制字至 `%data1`，准备检查是否需要递增端口学习计数 |
| `103` | `53` (`0x35`) | `0x24b8` | `[!data1.9] goto 0x38` | 若 `%data1[9]`（`learning_limitation_enable`）为 `0`，跳至 `PC = 56` 直接返回 |
| `104` | `54` (`0x36`) | `0x7080` | `mov %index, %data1` | 提取 `source_port` 至 `%index` |
| `105` | `55` (`0x37`) | `0x9918` | `count 3, +1` | `op=0x13 (count)`, `sub=0 (+1)`, `table=3`。对 `Table 3[%index]` 的低 16 位 `association_count` 执行硬件原子加 1 |
| `106` | `56` (`0x38`) | `0x4004` | `mov %index, 0 \|\| return 32` | 清零 `%index` 并返回 32 位成功响应 |

### 3.6 `IF_FWD_REMOVE`（行 109–129，`PC = 57`–`76`）逐行详解

调用前置条件：主控删除指定键（传入 64 位 `%key` 发起 `EXEC (PC = 57)`），或由 `IF_FWD_AGE` 在检测到表项老化后于 `PC = 83` 通过 `[aged] goto 0x39` 直接内部跳转至此（此时 `%key` 已被 `PC = 80` 装入老化表项的 64 位键）：

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `110` | `57` (`0x39`) | `0xe008` | `settab 1` | 选择 `Table 1`（`SHORT_FWD_HASH_TABLE`） |
| `111` | `58` (`0x3a`) | `0xa008` | `searchr 1, 0, 32` | 查找 64 位 `%key` 所在的哈希桶头 |
| `112` | `59` (`0x3b`) | `0x034c` | `[!res1\|err] goto 0x4c` | 若哈希桶为空或出错，跳至 `PC = 76` 返回 `%err = 7` |
| `113` | `60` (`0x3c`) | `0x7000` | `mov %index, %data1.16` | 提取冲突链首节点索引至 `%index` |
| `114` | `61` (`0x3d`) | `0xa210` | `searchr 2, 64, 32` | `len=0 (32b)`, `off=2 (64b)`, `table=2`。在 `Table 2` 冲突链中定位目标键，并将该表项 `Word 2`（位偏移 64 起的 32 位控制字，含 `bit 9` 与 `source_port`）读入 `%data1[31:0]` |
| `115` | `62` (`0x3e`) | `0x034c` | `[!res1\|err] goto 0x4c` | 若冲突链中未找到目标键，跳至 `PC = 76` 返回 `%err = 7` |
| `116` | `63` (`0x3f`) | `0x24c2` | `[!data1.9] goto 0x42` | 检查被删表项的 `%data1[9]`（`learning_limitation_enable`）：若为 `0`，跳过计数递减直接转至 `PC = 66` |
| `117` | `64` (`0x40`) | `0x7080` | `mov %index, %data1` | 提取被删表项的 `source_port`（`%data1[7:0]`）至 `%index` |
| `118` | `65` (`0x41`) | `0x9998` | `count 3, -1` | `op=0x13 (count)`, `sub=1 (-1)`, `table=3`。对 `Table 3[%index]` 的端口学习计数 `association_count` 执行硬件原子减 1 |
| `119` | `66` (`0x42`) | `0xa008` | `searchr 1, 0, 32` | 重新读取 `Table 1` 哈希桶头（因为 `PC = 64` 修改了 `%index`） |
| `120` | `67` (`0x43`) | `0x7000` | `mov %index, %data1.16` | 将冲突链首节点索引重新装入 `%index` |
| `121` | `68` (`0x44`) | `0xc810` | `remove 2` | `op=0x19 (remove)`, `table=2`。从 `%index` 起在 `Table 2`（`LLIST`）中定位 `%key` 所在节点并将其释放回空闲链（`%aux`）：若被删节点不是链首，硬件自动将其前驱节点的 `next_entry` 指向后继节点 `%next`（若被删节点为链尾则置前驱 `end = 1`），并设置 `[first]` 与 `[last]` 标志位 |
| `122` | `69` (`0x45`) | `0x05c7` | `[first] goto 0x47` | `cond=11 (first)`, `target=0x47`。若刚刚删除的是冲突链首节点（`first == 1`），必须同步修改 `Table 1` 哈希桶头，跳至 `PC = 71` |
| `123` | `70` (`0x46`) | `0x0004` | `return 32` | 若删除的是链中或链尾节点（`first == 0`），前驱指针已由 `remove 2` 硬件自动修补，直接返回 32 位成功响应 |
| `124` | `71` (`0x47`) | `0x064b` | `[last] goto 0x4b` | `cond=12 (last)`, `target=0x4b`。被删节点既是链首（`first == 1`）又是链尾（`last == 1`，即该哈希桶仅有这 1 个节点），跳至 `PC = 75` 清空哈希桶 |
| `125` | `72` (`0x48`) | `0x70a0` | `mov %index, %next` | 被删节点是链首但后续仍有节点（`last == 0`）：将 `remove 2` 锁存的后继节点索引 `%next` 装入 `%index` |
| `126` | `73` (`0x49`) | `0x7200` | `mov %data1.16, %index` | 将新的链首节点索引填入 `%data1[29:16]` |
| `127` | `74` (`0x4a`) | `0xd20c` | `add 1, 1 \|\| return 32` | `op=0x1a (add)`, `ov=1`, `table=1`, `ret=4 (32b)`。原地覆盖更新 `Table 1` 哈希桶头使其指向新链首 `%next`，并立即返回 32 位响应 |
| `128` | `75` (`0x4b`) | `0xc80c` | `remove 1 \|\| return 32` | `op=0x19 (remove)`, `table=1`, `ret=4 (32b)`。单节点链被删空：将 `Table 1` 对应哈希桶的 `valid` 位清零，并立即返回 32 位响应 |
| `129` | `76` (`0x4c`) | `0x603c` | `mov %err, 7 \|\| return 32` | 未找到目标表项错误出口：置 `%err = 7` 并返回 32 位响应 |

### 3.7 `IF_FWD_AGE`（行 143–144 `PC = 0` 与行 130–137 `PC = 77`–`84`）逐行详解

调用前置条件：PE 老化线程按序将待扫描的槽位号（`0`–`1023`）装入 `%index`，发起 `EXEC (PC = 0)`：

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `144` | `0` (`0x00`) | `0x00cd` | `goto 0x4d` | `op=0 (branch)`, `cond=1 (always)`, `target=0x4d (77)`。从入口 `PC = 0` 无条件跳转至位于 `PC = 77` 的老化扫描主体 |
| `130` | `77` (`0x4d`) | `0xe020` | `settab 4` | 选择 `Table 4`（`SHORT_FWD_TABLE_MAC_ALTERNATE`，与 `Table 2` 共享基址 `0x0200` 的 `VARRAY` 视图） |
| `131` | `78` (`0x4e`) | `0xa120` | `searchr 4, 0, 128` | 按 `%index` 直接读取 `Table 4[%index]` 的 128 位表项：若槽位有效（`Word 3 [31] valid == 1`），置 `%res1 = 1` 并将低 64 位键装入 `%data1[63:0]` |
| `132` | `79` (`0x4f`) | `0x0154` | `[!res1] goto 0x54` | 若该槽位为空闲槽（`%res1 == 0`），直接跳至 `PC = 84` 返回 |
| `133` | `80` (`0x50`) | `0x7540` | `mov %key, %data1` | `dst=%key`, `src=%data1`。将该有效槽位低 64 位中的搜索键（`FID + MAC/IPv4`）装入 `%key` 寄存器，为可能触发的 `IF_FWD_REMOVE` 准备好哈希查找键 |
| `134` | `81` (`0x51`) | `0xa2a0` | `searchr 4, 64, 64` | 读取同一槽位位偏移 `64` 起的高 64 位控制字与时间戳（`Word 2`–`Word 3`）至 `%data1[63:0]`；硬件同时比对 `Word 3 [15:0]` 的 `timestamp` 与当前全局老化时钟，更新 `[aged]` 条件标志 |
| `135` | `82` (`0x52`) | `0x2554` | `[!data1.10] goto 0x54` | `op=1 (bit_branch)`, `inv=1`, `bit=10`, `target=0x54`。测试 `%data1[10]`（`dynamic_enable`）：若为 `0`（静态配置表项），豁免老化直接跳至 `PC = 84` 返回 |
| `136` | `83` (`0x53`) | `0x06b9` | `[aged] goto 0x39` | `cond=13 (aged)`, `target=0x39 (57)`。若该动态表项的时间戳已超过老化阈值（`aged == 1`），直接跳转至 `PC = 57`（`IF_FWD_REMOVE`），复用 `PC = 80` 装入的 `%key` 自动递减端口计数并从 `Table 2` 与 `Table 1` 中摘除该表项 |
| `137` | `84` (`0x54`) | `0x4004` | `mov %index, 0 \|\| return 32` | 表项未到期（或为空闲/静态项）：清零 `%index` 并返回 32 位响应 |

---

## 4. `tse2.s`（`COP2 = TAG`，24 条指令）完整反汇编与逐行详解

### 4.1 `tse2.s` 完整反汇编源码

```text
; =============================================================================
; Disassembled by cop-disas from: tse2.bin
; Records: 25 (recorded: 25) | End PC: 0 | Instructions: 24
; =============================================================================

; --- Comment Section (0xFC00) ---
.comment "TOOL:Version 4.54"
.comment "TITLE: TAG TSE Micro Program"
.comment "VERSION: 3.9"
.comment "AUTHOR: Schaefer, Brunnbauer, Linortner"
.comment "DESCRIPTION:"
.comment "Implements the microcode for the TSE2 coprocessor."
.comment ""

; --- Interface Exports (0xF800) & Names (0xE000) ---
.export  6, "IF_TAG_FILTER", 0x0000 ; PC=0 (0x00)
.export 22, "IF_ACL_SEARCH_1", 0x0020 ; PC=16 (0x10)

; --- Custom Registers (0xF400..0xF41F) ---
.custom 0, 0x00000000
.custom 1, 0xffff0000
.custom 2, 0xffff0000
.custom 3, 0xffff0000
.custom 4, 0xffff0000
.custom 5, 0x00000000
.custom 6, 0x00000000
.custom 7, 0x00000000

; --- Hardware Table Configurations (0xC000) ---
.table 0, empty
.table 1, type=VARRAY, func=GENERIC, width=64, key=0, mask=0, kmsk=0xffff, size=128, base=0x0000, aux_valid=1, count=0, aux=0x0000
.table 2, type=LIST, func=GENERIC, width=32, key=16, mask=0, kmsk=0xffff, size=1024, base=0x0100, aux_valid=1, count=0, aux=0x0100
.table 3, type=LLIST, func=GENERIC, width=64, key=64, mask=0, kmsk=0xffff, size=256, base=0x0500, aux_valid=1, count=0, aux=0x0500
.table 4, type=LIST, func=GENERIC, width=256, key=128, mask=0, kmsk=0xffff, size=128, base=0x0700, aux_valid=1, count=0, aux=0x0700
.table 5, type=LIST, func=TERNARY, width=256, key=128, mask=0, kmsk=0xffff, size=128, base=0x0700, aux_valid=1, count=0, aux=0x0700

; --- Code Segment 0 (primary, byte_addr=0x0000, 24 instructions) ---
.code 0x0000

; --- Export ID 6: IF_TAG_FILTER, byte_addr=0x0000, PC=0 (0x00) ---
IF_TAG_FILTER:
    settab 1                           ; [PC= 0 (0x00) @0x0000: e008]
    searchr 1, 0, 64                   ; [PC= 1 (0x01) @0x0002: a088]
    [!res1|err] goto 0x0b              ; [PC= 2 (0x02) @0x0004: 030b] -> PC=11
    tag                                ; [PC= 3 (0x03) @0x0006: 7808]
    [!res1] goto 0x0d                  ; [PC= 4 (0x04) @0x0008: 010d] -> PC=13
    mov %index, %data1.48              ; [PC= 5 (0x05) @0x000a: 7020]
    mov %key_mask, %data1              ; [PC= 6 (0x06) @0x000c: 7400]
    search 2                           ; [PC= 7 (0x07) @0x000e: c010]
    [err] goto 0x0a                    ; [PC= 8 (0x08) @0x0010: 028a] -> PC=10
    xorn %res1, %data1.19              ; [PC= 9 (0x09) @0x0012: 6f98]
    return 32                          ; [PC=10 (0x0a) @0x0014: 0004]
    mov %res1, 1                       ; [PC=11 (0x0b) @0x0016: 6900]
    mov %err, 6 || return 32           ; [PC=12 (0x0c) @0x0018: 6034]
    [err] goto 0x0f                    ; [PC=13 (0x0d) @0x001a: 028f] -> PC=15
    mov %res1, 1                       ; [PC=14 (0x0e) @0x001c: 6900]
    mov %err, 0 || return 32           ; [PC=15 (0x0f) @0x001e: 6004]

; --- Export ID 22: IF_ACL_SEARCH_1, byte_addr=0x0020, PC=16 (0x10) ---
IF_ACL_SEARCH_1:
    mov %data2, %data1                 ; [PC=16 (0x10) @0x0020: 7340]
    mov %aux, %data1.16                ; [PC=17 (0x11) @0x0022: 7718] (inferred dst=7,src=0,sel=3)
    mov %index, 0                      ; [PC=18 (0x12) @0x0024: 4000]
    read 4, 0, 256                     ; [PC=19 (0x13) @0x0026: 81a0]
    mov %data1, %data2                 ; [PC=20 (0x14) @0x0028: 7260]
    mov %index, %aux                   ; [PC=21 (0x15) @0x002a: 70f8] (dst=0,src=7,sel=3)
    searchr 5, 0, 128                  ; [PC=22 (0x16) @0x002c: a128]
    mov %index, %prev_src || return 32 ; [PC=23 (0x17) @0x002e: 70c4]
```

### 4.2 `tse2.s` 头部伪指令逐行详解（行 7–38）

| 源码行 | 伪指令内容 | 逐行硬件作用与寄存器配置说明 |
| --- | --- | --- |
| `7`–`13` | `.comment "TOOL:Version 4.54"` 等 7 行 | 声明 `COP2`（`TAG`）微码标题为 `TAG TSE Micro Program`，版本 `3.9` |
| `16` | `.export 6, "IF_TAG_FILTER", 0x0000` | 将导出函数 ID `6`（`IF_TAG_FILTER`，VLAN 标签过滤）绑定至 `0x0000`（`PC = 0`） |
| `17` | `.export 22, "IF_ACL_SEARCH_1", 0x0020` | 将导出函数 ID `22`（`IF_ACL_SEARCH_1`，ACL 第 2 通道三态搜索）绑定至 `0x0020`（`PC = 16`） |
| `20`–`27` | `.custom 0`–`.custom 7` | 写入 `CUSTOM0`–`CUSTOM7` 默认初值 |
| `30` | `.table 0, empty` | 表 0 占位记录 |
| `31` | `.table 1, type=VARRAY, func=GENERIC, width=64, key=0, ..., size=128, base=0x0000, aux=0x0000` | 配置物理表 1（`TAGGING_FILTER_TABLE`）：128 项带有效位的数组（`VARRAY`），每项 64 位，占用表 RAM `0x0000`–`0x00FF` |
| `32` | `.table 2, type=LIST, func=GENERIC, width=32, key=16, ..., size=1024, base=0x0100, aux=0x0100` | 配置物理表 2（`VLAN_TABLE`）：1024 项顺序列表（`LIST`），每项 32 位，键宽 16 位（`tci`），占用表 RAM `0x0100`–`0x04FF` |
| `33` | `.table 3, type=LLIST, func=GENERIC, width=64, key=64, ..., size=256, base=0x0500, aux=0x0500` | 配置物理表 3（`MAC_FILTER_TABLE`）：256 项单链表（`LLIST`），每项 64 位，键宽 64 位，占用表 RAM `0x0500`–`0x06FF` |
| `34`–`35` | `.table 4` 与 `.table 5` (`base=0x0700`) | 配置物理表 4（`GENERIC`）与表 5（`TERNARY`）共享 `0x0700`–`0x0AFF`，承载 128 项 × 256 位 `ACL_FILTER_TABLE_LANE1` |
| `38` | `.code 0x0000` | 代码段从 `0x0000`（`PC = 0`）起顺序装载 24 条指令 |

### 4.3 `IF_TAG_FILTER`（行 41–57，`PC = 0`–`15`）逐行详解

调用前置条件：PE 将 `TAGGING_FILTER_TABLE` 的入口索引装入 `%index`，待过滤帧的 16 位 TCI 装入 `%key[15:0]`，带标签标志 `tagged`（`1` = 有标签，`0` = 无标签）装入 `%aux[0]`，发起 `EXEC (PC = 0)`：

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `42` | `0` (`0x00`) | `0xe008` | `settab 1` | 选择 `Table 1`（`TAGGING_FILTER_TABLE`） |
| `43` | `1` (`0x01`) | `0xa088` | `searchr 1, 0, 64` | 按 `%index` 读取 `Table 1` 的 64 位过滤描述符至 `%data1[63:0]`：低 32 位包含 `pass_on_match_enable`（bit 19）、`tagged_drop_enable`（bit 18）、`tagged_pass_enable`（bit 17）、`untagged_drop_enable`（bit 16）与 `tci_mask`（bits 15:0）；高 32 位包含 `valid`（bit 63）与 `vlan_table_index`（bits 61:48） |
| `44` | `2` (`0x02`) | `0x030b` | `[!res1\|err] goto 0x0b` | 若该 `TAGGING_FILTER_TABLE` 槽位无效（`%res1 == 0`）或索引越界（`err == 1`），跳至 `PC = 11` 默认放行并报告软错误 `6` |
| `45` | `3` (`0x03`) | `0x7808` | `tag` | `op=0x0f (special)`, `subop=1 (tag)`。硬件专用指令，结合 `%aux[0]`（`tagged`）与 `%data1[18:16]` 判定是否需要继续扫描 `VLAN_TABLE`：<br/>1. 若 `tagged == 0`（无标签帧）：无需查表，置 `%res1 = 0`；若 `untagged_drop_enable == 1` 则置 `err = 1`（丢弃），否则 `err = 0`（放行）。<br/>2. 若 `tagged == 1` 且 `tagged_drop_enable == 1`：无需查表直接丢弃，置 `%res1 = 0, err = 1`。<br/>3. 若 `tagged == 1` 且 `tagged_pass_enable == 1`：无需查表直接放行，置 `%res1 = 0, err = 0`。<br/>4. 若 `tagged == 1` 且上述两位均为 `0`：必须扫描 `Table 2` VID 列表，置 `%res1 = 1, err = 0` |
| `46` | `4` (`0x04`) | `0x010d` | `[!res1] goto 0x0d` | 若 `tag` 判定无需扫描 `VLAN_TABLE`（`%res1 == 0`），直接跳至 `PC = 13` 根据 `err` 标志输出放行或丢弃结果 |
| `47` | `5` (`0x05`) | `0x7020` | `mov %index, %data1.48` | `dst=%index`, `src=%data1.48`。需要扫描 VID 列表：从 `%data1[61:48]` 提取 `vlan_table_index` 起始槽位号装入 `%index` |
| `48` | `6` (`0x06`) | `0x7400` | `mov %key_mask, %data1` | `dst=%key_mask`, `src=%data1`。将 `%data1[15:0]` 的 `tci_mask` 装入 `%key_mask` 寄存器，使后续 `search 2` 仅比对掩码置 `1` 的 TCI 位（如仅比对 12 位 VID 或同时比对 PCP+VID） |
| `49` | `7` (`0x07`) | `0xc010` | `search 2` | 在 `Table 2`（`VLAN_TABLE`，`LIST`）中从 `%index` 起按 `(entry.tci & %key_mask) == (%key & %key_mask)` 顺序搜索直至命中（`%res1 = 1`）或遇到 `end == 1`（`%res1 = 0`） |
| `50` | `8` (`0x08`) | `0x028a` | `[err] goto 0x0a` | 若列表搜索越界报错（`err == 1`），跳至 `PC = 10` 直接返回 |
| `51` | `9` (`0x09`) | `0x6f98` | `xorn %res1, %data1.19` | `op=0x0d (bit_logic)`, `subop=xorn`, `bit=19`。将列表搜索命中结果 `%res1` 与 `%data1[19]`（`pass_on_match_enable`）执行同或（XNOR，`!(%res1 ^ %data1.19)`）运算写回 `%res1`：<br/>- 当 `pass_on_match_enable == 1`（白名单）时：命中（`1`）得 `%res1 = 1`（放行），未命中（`0`）得 `%res1 = 0`（丢弃）；<br/>- 当 `pass_on_match_enable == 0`（黑名单）时：命中（`1`）得 `%res1 = 0`（丢弃），未命中（`0`）得 `%res1 = 1`（放行） |
| `52` | `10` (`0x0a`) | `0x0004` | `return 32` | 返回 32 位过滤响应（`%res1 == 1` 放行，`%res1 == 0` 丢弃） |
| `53` | `11` (`0x0b`) | `0x6900` | `mov %res1, 1` | `Table 1` 表项无效出口：置 `%res1 = 1` |
| `54` | `12` (`0x0c`) | `0x6034` | `mov %err, 6 \|\| return 32` | 置软错误 `%err = 6` 并返回 32 位响应 |
| `55` | `13` (`0x0d`) | `0x028f` | `[err] goto 0x0f` | `tag` 免查表分支：若 `tag` 指令置了 `err == 1`（表示无标签丢弃或有标签直接丢弃，此时 `%res1` 仍为 `0`），跳至 `PC = 15` 保持 `%res1 = 0`（丢弃） |
| `56` | `14` (`0x0e`) | `0x6900` | `mov %res1, 1` | 若 `tag` 指令未置 `err`（表示无标签放行或有标签直接放行），置 `%res1 = 1`（放行） |
| `57` | `15` (`0x0f`) | `0x6004` | `mov %err, 0 \|\| return 32` | 将 `tag` 借用的 `%err` 标志清零为 `0`（正常完成），并返回携带最终放行/丢弃位 `%res1` 的 32 位响应 |

### 4.4 `IF_ACL_SEARCH_1`（行 60–68，`PC = 16`–`23`）逐行详解

行 `61`–`68`（`PC = 16`–`23`）为 ACL 第 2 通道（Lane 1）的 8 指令三态查找序列，在 `COP2` 的 `Table 4`（`GENERIC`）与 `Table 5`（`TERNARY`）上执行，各行机器码与寄存器行为同第 `2.6` 节 `IF_ACL_SEARCH_3`。

---

## 5. `tse3.s`（`COP3 = TBL`，18 条指令）完整反汇编与逐行详解

### 5.1 `tse3.s` 完整反汇编源码

```text
; =============================================================================
; Disassembled by cop-disas from: tse3.bin
; Records: 27 (recorded: 27) | End PC: 0 | Instructions: 18
; =============================================================================

; --- Comment Section (0xFC00) ---
.comment "TOOL:Version 4.54"
.comment "TITLE: TBL TSE Micro Program"
.comment "VERSION: 3.16"
.comment "AUTHOR: Schaefer, Brunnbauer, Linortner"
.comment "DESCRIPTION:"
.comment "Implements the microcode for the TSE3 coprocessor."
.comment ""

; --- Interface Exports (0xF800) & Names (0xE000) ---
.export  7, "IF_IPV6_REDUCE", 0x0000 ; PC=0 (0x00)
.export 15, "IF_IPV6HASH_SEARCHR", 0x000c ; PC=6 (0x06)
.export 23, "IF_ACL_SEARCH_2", 0x0014 ; PC=10 (0x0a)

; --- Custom Registers (0xF400..0xF41F) ---
.custom 0, 0x00000000
.custom 1, 0xffff0000
.custom 2, 0xffff0000
.custom 3, 0xffff0000
.custom 4, 0xffff0000
.custom 5, 0x00000000
.custom 6, 0x00000000
.custom 7, 0x00000000

; --- Hardware Table Configurations (0xC000) ---
.table 0, empty
.table 1, type=VARRAY, func=GENERIC, width=128, key=0, mask=0, kmsk=0xffff, size=256, base=0x0000, aux_valid=1, count=0, aux=0x0000
.table 2, type=HASH, func=GENERIC, width=32, key=128, mask=0, kmsk=0xffff, size=256, base=0x0400, aux_valid=1, count=0, aux=0x0400
.table 3, type=LLIST, func=GENERIC, width=256, key=128, mask=0, kmsk=0xffff, size=400, base=0x0500, aux_valid=1, count=0, aux=0x0500
.table 4, type=LIST, func=GENERIC, width=256, key=128, mask=0, kmsk=0xffff, size=128, base=0x1180, aux_valid=1, count=0, aux=0x1180
.table 5, type=LIST, func=TERNARY, width=256, key=128, mask=0, kmsk=0xffff, size=128, base=0x1180, aux_valid=1, count=0, aux=0x1180

; --- Code Segment 0 (primary, byte_addr=0x0000, 18 instructions) ---
.code 0x0000

; --- Export ID 7: IF_IPV6_REDUCE, byte_addr=0x0000, PC=0 (0x00) ---
IF_IPV6_REDUCE:
    settab 2                           ; [PC= 0 (0x00) @0x0000: e010]
    searchr 2, 0, 32                   ; [PC= 1 (0x01) @0x0002: a010]
    [!res1|err] goto 0x05              ; [PC= 2 (0x02) @0x0004: 0305] -> PC=5
    mov %index, %data1.16              ; [PC= 3 (0x03) @0x0006: 7000]
    search 3                           ; [PC= 4 (0x04) @0x0008: c018]
    return 32                          ; [PC= 5 (0x05) @0x000a: 0004]

; --- Export ID 15: IF_IPV6HASH_SEARCHR, byte_addr=0x000c, PC=6 (0x06) ---
IF_IPV6HASH_SEARCHR:
    settab 2                           ; [PC= 6 (0x06) @0x000c: e010]
    search 2                           ; [PC= 7 (0x07) @0x000e: c010]
    read 2, 0, 32                      ; [PC= 8 (0x08) @0x0010: 8010]
    mov %res1, %data1.31 || return 32  ; [PC= 9 (0x09) @0x0012: 6bfc]

; --- Export ID 23: IF_ACL_SEARCH_2, byte_addr=0x0014, PC=10 (0x0a) ---
IF_ACL_SEARCH_2:
    mov %data2, %data1                 ; [PC=10 (0x0a) @0x0014: 7340]
    mov %aux, %data1.16                ; [PC=11 (0x0b) @0x0016: 7718] (inferred dst=7,src=0,sel=3)
    mov %index, 0                      ; [PC=12 (0x0c) @0x0018: 4000]
    read 4, 0, 256                     ; [PC=13 (0x0d) @0x001a: 81a0]
    mov %data1, %data2                 ; [PC=14 (0x0e) @0x001c: 7260]
    mov %index, %aux                   ; [PC=15 (0x0f) @0x001e: 70f8] (dst=0,src=7,sel=3)
    searchr 5, 0, 128                  ; [PC=16 (0x10) @0x0020: a128]
    mov %index, %prev_src || return 32 ; [PC=17 (0x11) @0x0022: 70c4]
```

### 5.2 `tse3.s` 头部伪指令逐行详解（行 7–39）

| 源码行 | 伪指令内容 | 逐行硬件作用与寄存器配置说明 |
| --- | --- | --- |
| `7`–`13` | `.comment "TOOL:Version 4.54"` 等 7 行 | 声明 `COP3`（`TBL`）微码标题为 `TBL TSE Micro Program`，版本 `3.16` |
| `16` | `.export 7, "IF_IPV6_REDUCE", 0x0000` | 将导出函数 ID `7`（`IF_IPV6_REDUCE`，128 位 IPv6 地址压缩查找）绑定至 `0x0000`（`PC = 0`） |
| `17` | `.export 15, "IF_IPV6HASH_SEARCHR", 0x000c` | 将导出函数 ID `15`（`IF_IPV6HASH_SEARCHR`，IPv6 哈希桶直接计算与读取）绑定至 `0x000C`（`PC = 6`） |
| `18` | `.export 23, "IF_ACL_SEARCH_2", 0x0014` | 将导出函数 ID `23`（`IF_ACL_SEARCH_2`，ACL 第 3 通道三态搜索）绑定至 `0x0014`（`PC = 10`） |
| `21`–`28` | `.custom 0`–`.custom 7` | 写入 `CUSTOM0`–`CUSTOM7` 默认初值 |
| `31` | `.table 0, empty` | 表 0 占位记录 |
| `32` | `.table 1, type=VARRAY, func=GENERIC, width=128, key=0, ..., size=256, base=0x0000, aux=0x0000` | 配置物理表 1（`DS_GEM_PORT_TABLE`）：256 项 × 128 位 `VARRAY`，由 PE 直接使用 `SEARCHR` 命令按 8 位 `GPIX` 读取，占用表 RAM `0x0000`–`0x03FF` |
| `33` | `.table 2, type=HASH, func=GENERIC, width=32, key=128, ..., size=256, base=0x0400, aux=0x0400` | 配置物理表 2（`IPV6_REDUCTION_HASH_TABLE`）：256 桶哈希头表，键宽 128 位（完整 IPv6 地址），每桶 32 位，占用表 RAM `0x0400`–`0x04FF` |
| `34` | `.table 3, type=LLIST, func=GENERIC, width=256, key=128, ..., size=400, base=0x0500, aux=0x0500` | 配置物理表 3（`IPV6_REDUCTION_TABLE`）：400 项 × 256 位单链表（`LLIST`），键宽 128 位，占用表 RAM `0x0500`–`0x117F` |
| `35`–`36` | `.table 4` 与 `.table 5` (`base=0x1180`) | 配置物理表 4（`GENERIC`）与表 5（`TERNARY`）共享 `0x1180`–`0x157F`，承载 128 项 × 256 位 `ACL_FILTER_TABLE_LANE2` |
| `39` | `.code 0x0000` | 代码段从 `0x0000`（`PC = 0`）起顺序装载 18 条指令 |

### 5.3 `IF_IPV6_REDUCE`（行 42–48，`PC = 0`–`5`）与 `IF_IPV6HASH_SEARCHR`（行 51–55，`PC = 6`–`9`）逐行详解

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `43` | `0` (`0x00`) | `0xe010` | `settab 2` | **`IF_IPV6_REDUCE` 入口**：选择 `Table 2`（`IPV6_REDUCTION_HASH_TABLE`） |
| `44` | `1` (`0x01`) | `0xa010` | `searchr 2, 0, 32` | 对调用方传入的 128 位 IPv6 地址（`%key[127:0]`）计算 8 位 CRC 哈希值，读取 `Table 2` 对应的 32 位哈希桶头至 `%data1[31:0]`，桶有效标志写入 `%res1` |
| `45` | `2` (`0x02`) | `0x0305` | `[!res1\|err] goto 0x05` | 若哈希桶为空或出错，跳至 `PC = 5` 返回未命中 |
| `46` | `3` (`0x03`) | `0x7000` | `mov %index, %data1.16` | 从哈希桶头 `%data1[29:16]` 提取 `IPV6_REDUCTION_TABLE` 冲突链首节点索引装入 `%index` |
| `47` | `4` (`0x04`) | `0xc018` | `search 3` | 在 `Table 3`（`IPV6_REDUCTION_TABLE`，`LLIST`）中沿冲突链比对 128 位 IPv6 地址（不覆盖 `%data1`）。若命中，置 `%res1 = 1`，且命中的槽位索引（`0`–`399`）保留在 `%index` 寄存器中 |
| `48` | `5` (`0x05`) | `0x0004` | `return 32` | 向 PE 返回响应包：响应头中的 `index` 字段即为压缩后的 9 位 IPv6 地址短索引 |
| `52` | `6` (`0x06`) | `0xe010` | `settab 2` | **`IF_IPV6HASH_SEARCHR` 入口**：选择 `Table 2`（`IPV6_REDUCTION_HASH_TABLE`） |
| `53` | `7` (`0x07`) | `0xc010` | `search 2` | 对 128 位 `%key` 计算 8 位哈希桶索引并存入 `%index`（不判断有效位） |
| `54` | `8` (`0x08`) | `0x8010` | `read 2, 0, 32` | 按计算出的桶索引 `%index` 直接读取 `Table 2[%index]` 的 32 位原始桶数据至 `%data1[31:0]` |
| `55` | `9` (`0x09`) | `0x6bfc` | `mov %res1, %data1.31 \|\| return 32` | `op=0x0d (bit_logic)`, `subop=mov_bit`, `bit=31`, `ret=4 (32b)`。将桶头最高位 `%data1[31]`（`valid`）复制到 `%res1`，同时在同一周期返回计算出的哈希桶索引 `%index` 与 32 位桶数据 `%data1` |

### 5.4 `IF_ACL_SEARCH_2`（行 58–66，`PC = 10`–`17`）逐行详解

行 `59`–`66`（`PC = 10`–`17`）为 ACL 第 3 通道（Lane 2）的 8 指令三态查找序列，在 `COP3` 的 `Table 4`（`GENERIC`）与 `Table 5`（`TERNARY`）上执行，各行机器码与寄存器行为同第 `2.6` 节 `IF_ACL_SEARCH_3`。

---

## 6. `tse4.s`（`COP4 = MSF`，0 条指令）完整反汇编与逐行详解

### 6.1 `tse4.s` 完整反汇编源码

```text
; =============================================================================
; Disassembled by cop-disas from: tse4.bin
; Records: 19 (recorded: 19) | End PC: 0 | Instructions: 0
; =============================================================================

; --- Comment Section (0xFC00) ---
.comment "TOOL:Version 4.54"
.comment "TITLE: MSF TSE Micro Program"
.comment "VERSION: 3.3"
.comment "AUTHOR: Schaefer, Brunnbauer, Linortner"
.comment "DESCRIPTION:"
.comment "Implements the microcode for the TSE4 coprocessor."
.comment ""

; --- Custom Registers (0xF400..0xF41F) ---
.custom 0, 0x00000000
.custom 1, 0xffff0000
.custom 2, 0xffff0000
.custom 3, 0xffff0000
.custom 4, 0xffff0000
.custom 5, 0x00000000
.custom 6, 0x00000000
.custom 7, 0x00000000

; --- Hardware Table Configurations (0xC000) ---
.table 0, empty
.table 1, type=VARRAY, func=GENERIC, width=64, key=0, mask=0, kmsk=0xffff, size=256, base=0x0000, aux_valid=1, count=0, aux=0x0000
.table 2, type=LIST, func=GENERIC, width=128, key=64, mask=0, kmsk=0xffff, size=512, base=0x0200, aux_valid=1, count=0, aux=0x0200
.table 3, type=ARRAY, func=GENERIC, width=32, key=0, mask=0, kmsk=0xffff, size=704, base=0x0a00, aux_valid=1, count=0, aux=0x0a00
.table 4, type=LIST, func=GENERIC, width=32, key=16, mask=0, kmsk=0xffff, size=64, base=0x0cc0, aux_valid=1, count=0, aux=0x0cc0

; --- No Code Instructions (Pure Table Configuration Image) ---
```

### 6.2 `tse4.s` 逐行详解（行 7–31）

`COP4`（`MSF`）的所有表操作均能在单条硬件 `LINKC1` 原语内完成，无需多步微码组合，因此 `tse4.bin` 仅包含注释段、`.custom` 寄存器初值与 4 张硬件表的寄存器描述符（共 19 条 `type = 3` 记录）：

| 源码行 | 伪指令内容 | 逐行硬件作用与硬连线访问方式 |
| --- | --- | --- |
| `7`–`13` | `.comment "TOOL:Version 4.54"` 等 7 行 | 声明 `COP4`（`MSF`）微码标题为 `MSF TSE Micro Program`，版本 `3.3` |
| `16`–`23` | `.custom 0`–`.custom 7` | 初始化 `CUSTOM0`–`CUSTOM7` 寄存器 |
| `26` | `.table 0, empty` | 表 0 占位记录 |
| `27` | `.table 1, type=VARRAY, func=GENERIC, width=64, key=0, ..., size=256, base=0x0000, aux=0x0000` | 配置物理表 1（`US_GEM_PORT_TABLE`）：256 项 × 64 位 `VARRAY`，占用表 RAM `0x0000`–`0x01FF`。PE 通过 `LINKC1 SEARCHR (table = 1)` 直接按 8 位 `GPIX` 读取上行 `GEM Port-ID` 与 `egress_queue` |
| `28` | `.table 2, type=LIST, func=GENERIC, width=128, key=64, ..., size=512, base=0x0200, aux=0x0200` | 配置物理表 2（`DS_MC_IP_SOURCE_FILTER_TABLE`）：512 项 × 128 位顺序列表（`LIST`），键宽 64 位，占用表 RAM `0x0200`–`0x09FF`。PE 通过 `LINKC1 SEARCHR (table = 2)` 硬件扫描下行组播源过滤列表 |
| `29` | `.table 3, type=ARRAY, func=GENERIC, width=32, key=0, ..., size=704, base=0x0a00, aux=0x0a00` | 配置物理表 3（`COUNTER_TABLE`）：704 项 × 32 位定长数组（`ARRAY`），占用表 RAM `0x0A00`–`0x0CBF`。PE 通过 `LINKC1 COUNT (table = 3)` 硬件原子递增对应统计计数器 |
| `30` | `.table 4, type=LIST, func=GENERIC, width=32, key=16, ..., size=64, base=0x0cc0, aux=0x0cc0` | 配置物理表 4（`VLAN_METERING_TABLE`）：64 项 × 32 位顺序列表（`LIST`），键宽 16 位，占用表 RAM `0x0CC0`–`0x0CFF`。PE 通过 `LINKC1 SEARCHR (table = 4)` 查找绑定到指定 VID 的上下行 `TBM` 计量器 |

---

## 7. `tse5.s`（`COP5 = EXT`，18 条指令）完整反汇编与逐行详解

### 7.1 `tse5.s` 完整反汇编源码

```text
; =============================================================================
; Disassembled by cop-disas from: tse5.bin
; Records: 27 (recorded: 27) | End PC: 0 | Instructions: 18
; =============================================================================

; --- Comment Section (0xFC00) ---
.comment "TOOL:Version 4.54"
.comment "TITLE: EXT TSE Micro Program"
.comment "VERSION: 3.8"
.comment "AUTHOR: Schaefer, Brunnbauer, Linortner"
.comment "DESCRIPTION:"
.comment "Implements the microcode for the TSE5 coprocessor."
.comment ""

; --- Interface Exports (0xF800) & Names (0xE000) ---
.export  9, "IF_VLAN_TRANSLATE", 0x0000 ; PC=0 (0x00)
.export 21, "IF_ACL_SEARCH_0", 0x0014 ; PC=10 (0x0a)

; --- Custom Registers (0xF400..0xF41F) ---
.custom 0, 0x00000000
.custom 1, 0xffff0000
.custom 2, 0xffff0000
.custom 3, 0xffff0000
.custom 4, 0xffff0000
.custom 5, 0x00000000
.custom 6, 0x00000000
.custom 7, 0x00000000

; --- Hardware Table Configurations (0xC000) ---
.table 0, empty
.table 1, type=VARRAY, func=GENERIC, width=64, key=0, mask=0, kmsk=0xffff, size=128, base=0x0000, aux_valid=1, count=0, aux=0x0000
.table 2, type=LIST, func=CUSTOM, width=64, key=96, mask=0, kmsk=0xffff, size=1024, base=0x0100, aux_valid=1, count=0, aux=0x0100
.table 3, type=VARRAY, func=GENERIC, width=64, key=0, mask=0, kmsk=0xffff, size=1024, base=0x0900, aux_valid=1, count=0, aux=0x0900
.table 4, type=LIST, func=GENERIC, width=32, key=16, mask=0, kmsk=0xffff, size=64, base=0x1100, aux_valid=1, count=0, aux=0x1100
.table 5, type=LIST, func=GENERIC, width=256, key=128, mask=0, kmsk=0xffff, size=128, base=0x1140, aux_valid=1, count=0, aux=0x1140
.table 6, type=LIST, func=TERNARY, width=256, key=128, mask=0, kmsk=0xffff, size=128, base=0x1140, aux_valid=1, count=0, aux=0x1140

; --- Code Segment 0 (primary, byte_addr=0x0000, 18 instructions) ---
.code 0x0000

; --- Export ID 9: IF_VLAN_TRANSLATE, byte_addr=0x0000, PC=0 (0x00) ---
IF_VLAN_TRANSLATE:
    settab 1                           ; [PC= 0 (0x00) @0x0000: e008]
    searchr 1, 0, 64                   ; [PC= 1 (0x01) @0x0002: a088]
    [!res1] goto 0x09                  ; [PC= 2 (0x02) @0x0004: 0109] -> PC=9
    mov %index, %data1.48              ; [PC= 3 (0x03) @0x0006: 7020]
    mov %data2, %data1                 ; [PC= 4 (0x04) @0x0008: 7340]
    searchr 2, 0, 64                   ; [PC= 5 (0x05) @0x000a: a090]
    [!res1] goto 0x09                  ; [PC= 6 (0x06) @0x000c: 0109] -> PC=9
    searchr 3, 0, 64                   ; [PC= 7 (0x07) @0x000e: a098]
    treat                              ; [PC= 8 (0x08) @0x0010: 7810]
    return 128                         ; [PC= 9 (0x09) @0x0012: 0006]

; --- Export ID 21: IF_ACL_SEARCH_0, byte_addr=0x0014, PC=10 (0x0a) ---
IF_ACL_SEARCH_0:
    mov %data2, %data1                 ; [PC=10 (0x0a) @0x0014: 7340]
    mov %aux, %data1.16                ; [PC=11 (0x0b) @0x0016: 7718] (inferred dst=7,src=0,sel=3)
    mov %index, 0                      ; [PC=12 (0x0c) @0x0018: 4000]
    read 5, 0, 256                     ; [PC=13 (0x0d) @0x001a: 81a8]
    mov %data1, %data2                 ; [PC=14 (0x0e) @0x001c: 7260]
    mov %index, %aux                   ; [PC=15 (0x0f) @0x001e: 70f8] (dst=0,src=7,sel=3)
    searchr 6, 0, 128                  ; [PC=16 (0x10) @0x0020: a130]
    mov %index, %prev_src || return 32 ; [PC=17 (0x11) @0x0022: 70c4]
```

### 7.2 `tse5.s` 头部伪指令逐行详解（行 7–39）

| 源码行 | 伪指令内容 | 逐行硬件作用与寄存器配置说明 |
| --- | --- | --- |
| `7`–`13` | `.comment "TOOL:Version 4.54"` 等 7 行 | 声明 `COP5`（`EXT`）微码标题为 `EXT TSE Micro Program`，版本 `3.8` |
| `16` | `.export 9, "IF_VLAN_TRANSLATE", 0x0000` | 将导出函数 ID `9`（`IF_VLAN_TRANSLATE`，Extended VLAN 规则查找与标签改写合成）绑定至 `0x0000`（`PC = 0`） |
| `17` | `.export 21, "IF_ACL_SEARCH_0", 0x0014` | 将导出函数 ID `21`（`IF_ACL_SEARCH_0`，ACL 第 1 通道三态搜索）绑定至 `0x0014`（`PC = 10`） |
| `20`–`27` | `.custom 0`–`.custom 7` | 写入 `CUSTOM0`–`CUSTOM7` 容器默认初值；运行期初始化时，系统将 `CUSTOM0` 设为 `0x81000001`（`TPID = 0x8100, DEFRULE = 1`），将 `CUSTOM1`–`CUSTOM4` 依次设为 `0x0800`（IPv4）、`0x8863`（PPPoE）、`0x0806`（ARP）、`0x86DD`（IPv6） |
| `30` | `.table 0, empty` | 表 0 占位记录 |
| `31` | `.table 1, type=VARRAY, func=GENERIC, width=64, key=0, ..., size=128, base=0x0000, aux=0x0000` | 配置物理表 1（`EXTENDED_VLAN_TABLE`）：128 项 × 64 位 `VARRAY`，存放端口自定义 TPID 与规则段起始指针 `rule_table_pointer`，占用表 RAM `0x0000`–`0x00FF` |
| `32` | `.table 2, type=LIST, func=CUSTOM, width=64, key=96, ..., size=1024, base=0x0100, aux=0x0100` | 配置物理表 2（`VLAN_RULE_TABLE`）：1024 项 × 64 位顺序列表（`LIST`），匹配模式设为硬件自定义协议匹配（`func = CUSTOM`），输入键宽 96 位，占用表 RAM `0x0100`–`0x08FF` |
| `33` | `.table 3, type=VARRAY, func=GENERIC, width=64, key=0, ..., size=1024, base=0x0900, aux=0x0900` | 配置物理表 3（`VLAN_TREATMENT_TABLE`）：1024 项 × 64 位 `VARRAY`，与 `Table 2` 规则下标一一对应，占用表 RAM `0x0900`–`0x10FF` |
| `34` | `.table 4, type=LIST, func=GENERIC, width=32, key=16, ..., size=64, base=0x1100, aux=0x1100` | 配置物理表 4（`L4_FILTER_TABLE`）：64 项 × 32 位四层 TCP/UDP 端口号过滤列表，占用表 RAM `0x1100`–`0x113F` |
| `35`–`36` | `.table 5` 与 `.table 6` (`base=0x1140`) | 配置物理表 5（`GENERIC`）与表 6（`TERNARY`）共享 `0x1140`–`0x153F`，承载 128 项 × 256 位 `ACL_FILTER_TABLE_LANE0` |
| `39` | `.code 0x0000` | 代码段从 `0x0000`（`PC = 0`）起顺序装载 18 条指令 |

### 7.3 `IF_VLAN_TRANSLATE`（行 42–52，`PC = 0`–`9`）与 `IF_ACL_SEARCH_0`（行 55–63，`PC = 10`–`17`）逐行详解

| 源码行 | PC (`Hex`) | 半字机器码 | 汇编指令 | 机器码位域拆解与逐行硬件执行动作 |
| --- | --- | --- | --- | --- |
| `43` | `0` (`0x00`) | `0xe008` | `settab 1` | **`IF_VLAN_TRANSLATE` 入口**：选择 `Table 1`（`EXTENDED_VLAN_TABLE`） |
| `44` | `1` (`0x01`) | `0xa088` | `searchr 1, 0, 64` | 按输入 `%index` 读取 `Table 1` 的 64 位端口 Extended VLAN 描述符至 `%data1[63:0]`（含 `inner_tpid_1_value`、`inner_tpid_2_value`、`max_tags_to_remove` 与 `rule_table_pointer`） |
| `45` | `2` (`0x02`) | `0x0109` | `[!res1] goto 0x09` | 若该描述符无效（`%res1 == 0`），直接跳至 `PC = 9` 返回未命中 |
| `46` | `3` (`0x03`) | `0x7020` | `mov %index, %data1.48` | 从 `%data1[61:48]` 提取该端口在 `VLAN_RULE_TABLE`（`Table 2`）中的规则段起始索引 `rule_table_pointer` 装入 `%index` |
| `47` | `4` (`0x04`) | `0x7340` | `mov %data2, %data1` | 将 `Table 1` 读出的 64 位端口描述符（含自定义 `inner_tpid_1/2`）备份至 `%data2`，供后续 `CUSTOM` 匹配器及 `treat` 指令使用 |
| `48` | `5` (`0x05`) | `0xa090` | `searchr 2, 0, 64` | 在 `Table 2`（`VLAN_RULE_TABLE`，`func = CUSTOM`）中从 `%index` 起顺序扫描规则列表。硬件 `CUSTOM` 比较器综合比对 96 位入向帧标签键 `%key`、`%data2` 中的自定义 TPID 以及 `CUSTOM0`–`CUSTOM4` 中的全局 TPID / EtherType；命中首条满足条件的规则（或 `end == 1` 处的默认规则）时，置 `%res1 = 1`，将 `%index` 更新为命中规则下标，并将该 64 位规则读入 `%data1` |
| `49` | `6` (`0x06`) | `0x0109` | `[!res1] goto 0x09` | 若遍历至规则段末尾（`end == 1`）仍未命中任何规则，跳至 `PC = 9` 返回 `%res1 = 0` |
| `50` | `7` (`0x07`) | `0xa098` | `searchr 3, 0, 64` | 规则命中：保持命中的规则下标 `%index` 不变，直接从 `Table 3`（`VLAN_TREATMENT_TABLE`，`VARRAY`）同一下标 `%index` 读取对应的 64 位标签动作项至 `%data1[63:0]` |
| `51` | `8` (`0x08`) | `0x7810` | `treat` | `op=0x0f (special)`, `subop=2 (treat)`。硬件专用标签合成指令：根据 `%data1`（64 位 `VLAN_TREATMENT` 动作）、`%data2`（64 位 `EXTENDED_VLAN` 端口 TPID 描述符）、`%key`（96 位原帧内外层 TCI/TPID）以及 `%aux`（入向 DSCP 映射的 3 位候选 PCP），合成 128 位输出结构（含 `new_outer_tci`、`new_inner_tci`、`new_outer_tpid`、`new_inner_tpid`、`remove_tags`、`add_outer_tag`、`add_inner_tag`、`discard`）并写入 `%data1[127:0]` |
| `52` | `9` (`0x09`) | `0x0006` | `return 128` | `ret=6 (128b)`。向 PE 线程返回 128 位（4 个 32 位字）标签重写指令包 |
| `56`–`63` | `10`–`17` (`0x0a`–`0x11`) | `0x7340`..`0x70c4` | **`IF_ACL_SEARCH_0`**（8 条指令） | ACL 第 1 通道（Lane 0）三态查找序列：由于 `COP5` 前 4 张表已被 Extended VLAN 与 L4 Filter 占用，因此 `PC = 13` 执行 `read 5, 0, 256`（机器码 `0x81a8`，从 `Table 5` 读取 256 位掩码），`PC = 16` 执行 `searchr 6, 0, 128`（机器码 `0xa130`，在 `Table 6` 上执行三态匹配），其余 6 条指令与 `IF_ACL_SEARCH_1/2/3` 完全相同 |

证据边界：代码中的 `(inferred dst=7,src=0,sel=3)` 是人为推断标记。`0x7718` 的 `mov %aux, %data1.16` 不是原调试打印器已经支持的助记符，不能据此断言该条的切片宽度。其余逐行解释中的表用途来自主机表结构和上下文；不代表已经上板单步或掌握每条指令的周期数。

## 本地依据与适用范围

`extracted/rootfs/lib/firmware/sfu/tse0.bin`–`tse5.bin` 与 `docs/COP_ISA.md`；寄存器配置字布局以 `bsp/modules/onu/drv_onu_reg_coplink_cop.h` 核对。

上述 `bsp/` 路径按本次审计的 `linux-3.10.49` 基线读取，属于源码/静态固件证据；不将 `linux-7.3` 移植结果或未上板验证的解释当作原固件运行事实。
