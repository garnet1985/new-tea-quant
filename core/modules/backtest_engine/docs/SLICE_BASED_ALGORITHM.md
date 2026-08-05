# slice_based 算法（权威约定）

**模块：** `modules.backtest_engine`  
**地位：** 本文是 `slice_based` 的**算法单一事实来源（SOT）**。  
**若代码与本文冲突：以本文为准，改代码。不做兼容旧路径。**

---

## 0. 问题

全截面 per-entity 数据可能远大于可用内存。按片从 DB 装载/释放；global 全量常驻。

---

## 1. 禁止

- task 开头一次拉满全窗 per-entity  
- N 个正式片只读 1 次 DB  
- UX 硬上限偷改 `min_required`  
- 用探针空转期的读算比定 queue（不可靠）  
- 模块级 export 的自由函数充当算法入口（算法挂类）

---

## 2. 探针（只认真用内存）

```text
W_probe = min_required_records（缺省 20）
装载宽 = W_probe 的一小块真实数据（全 entity）
→ probe_mb（该块总内存）

若 budget * 0.8 < 2 * probe_mb → 直接 fail
  （有回溯时算侧至少 2 片；0.8 作用在预算上）

mb_per_point = probe_mb / W_probe
```

`t_load` / `t_compute` 可记日志，**不**用于初始 queue。

---

## 3. 在飞结构（OOM 用峰值）

| 符号 | 含义 | 怎么定 |
|------|------|--------|
| `compute_slices` | 算侧滑动窗 | 有回溯时 **2**（写死） |
| `R` | 并发 reader（在读、尚未入队也可占 1 片） | `max(0, cores - reserved - 1)`（1 个 compute 进程） |
| `N` | queue 中已就绪片数上限 | 初值见 §4；运行中真片再调 |
| `in_flight` | 峰值上界 | **`2 + N + R`**（不是 `2+N`） |

单/双核时 `R` 常为 0 → 串行预读，合法。

---

## 4. 初始 plan（不定读算比）

```text
R = max(0, cores - reserved - 1)

for N in R … 0:                    # 上限先取 R；优先较大 N
    in_flight = 2 + N + R
    width = floor(budget * 0.8 / in_flight / mb_per_point)
    if width >= W_probe:            # W_probe == min_required
        return Plan(width, queue=N, readers=R, in_flight)
fail("内存不足以支撑 min_required × 在飞")
```

- 片宽 **无 UX 上限**  
- 成功时 `width ≥ min_required`，且在该约束下尽量大 N（偏多预读）  
- `N=0` 仍不够 → 报错抛回用户  

---

## 5. 运行中调 N（真片读算比）

片宽 **冻结**。每片（过空转、有真实业务后）更新：

```text
N_ideal = ceil(t_load / t_compute)
N_max   = floor(budget * 0.8 / slice_mb - 2 - R)
N       = clamp(N_ideal, 0, N_max)
```

内存不够追比值 → 接受算侧空等；不得为加大 N 突破预算或改片宽。

---

## 6. 数据分层与滑动窗

- **per-entity**：按正式片 IO；峰值按 `in_flight`  
- **global**：全窗常驻（GDP/日历/list…）  
- **算侧**：至少片1+片2 ready 再算；滑出 lookback 后释放旧片  
- **tracker / session_state**：常驻，不随片释放  

---

## 7. 进度

探针/首包双片就绪后出第一次进度；之后按正式片完成汇报。禁止全窗一次加载导致长时间卡在 15%。

---

## 8. 分工

| 谁 | 职责 |
|----|------|
| **BE** | 探针内存门槛、§4/§5 plan、多进程按片调度、进度 |
| **Strategy** | 按窗 load 一片 per-entity、compute；禁止全窗一次装 per-entity |

算法入口：`SliceMemoryPlanner`（类方法），见 `core/schedule/slice_based/slice_width.py`。

---

## 9. 不变量

1. `in_flight = 2 + N + R`  
2. 探针 fail：`budget*0.8 < 2*probe_mb`  
3. 初始 N 不依赖探针读算比  
4. N 正式片 ≥ N 次 per-entity DB 读  
5. 无 UX 硬上限；装不下报错  

---

## 相关文档

- [DESIGN.md](./DESIGN.md)  
- [ARCHITECTURE.md](./ARCHITECTURE.md)  
- [API.md](../API.md)  
