"""
循环 ③ 定时式 —— 定时或事件唤醒，处理完睡眠
════════════════════════════════════════════════════════════════════
人的位置：退到环外。定时器或事件把它叫醒，拉新状态，有变化才处理，
          处理完睡眠，等下一轮。
适合：周期检查和增量处理——值守、巡检、风控扫描。
真实案例：蚂蚁消费金融风控（新华网）——大模型风控全链路自动化率 90%，
          支付风控单笔 0.1 秒内完成。重复扫描同一笔，结果不变（幂等）。

这一版要讲清楚的**唯一控制点**：
    幂等 + 游标。
    - 游标（cursor）：记住"处理到哪了"。重启后从游标继续，不从头再来。
    - 幂等键（idempotency key）：同一件事处理两遍，第二遍是空操作。
    这两样是定时/事件循环能安全重启、能容忍重复投递的根。
    另加一条纪律：间隔匹配变化速度，能事件触发就别空转轮询。

下面的 demo 故意做两件"脏"事：(1) 中途"重启"，(2) 重复投递一条旧事件。
看游标和幂等键怎么让结果依然正确——已处理的绝不重复处理。
"""
from __future__ import annotations
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import trace
from common.switch import control_off, banner_note


# ───────────────────────── 模拟数据源 ─────────────────────────
# 订单流：每个订单有单调递增的 seq（当游标用）和唯一 id（当幂等键用）。
# 真实世界里 seq 可能是数据库自增列/时间戳/binlog offset，id 是业务主键。
ORDERS = [
    {"seq": 1, "id": "A001", "amount": 120},
    {"seq": 2, "id": "A002", "amount": 8600},   # 大额，风控命中
    {"seq": 3, "id": "A003", "amount": 300},
    {"seq": 4, "id": "A004", "amount": 50},
    {"seq": 5, "id": "A005", "amount": 12000},  # 大额，风控命中
]


def fetch_since(cursor: int) -> list[dict]:
    """只拉游标之后的增量——这就是'有变化才处理'，不是每轮全表扫。"""
    return [o for o in ORDERS if o["seq"] > cursor]


# ───────────────────────── 处理器（幂等）─────────────────────────
_processed: set[str] = set()   # 幂等键集合；真实系统里是 Redis/DB 唯一约束


def process(order: dict) -> str:
    """幂等处理：见过的 id 直接跳过。返回动作。"""
    # ↓ 想手动关幂等？把下面这两行 if...return 注释掉，重复投递就会被二次处理
    if order["id"] in _processed and not control_off():   # ← 开关关掉幂等
        return "skip_dup"          # 幂等：重复投递 → 空操作
    _processed.add(order["id"])
    risk = order["amount"] >= 5000
    return "flag_risk" if risk else "ok"


# ───────────────────────── 一次唤醒 = 一圈 ─────────────────────────
def wake(n: int, cursor: int, note: str = "") -> int:
    """被唤醒一次：拉增量 → 逐条幂等处理 → 推进游标 → 睡眠。返回新游标。"""
    trace.tick(n, note or f"唤醒，游标在 seq={cursor}")
    batch = fetch_since(cursor)
    if not batch:
        trace.step("增量", "无新数据，继续睡眠")
        trace.close("空转一圈（正常）")
        return cursor
    for o in batch:
        action = process(o)
        label = {"ok": "正常入账", "flag_risk": "⚠ 大额→转人工复核",
                 "skip_dup": "幂等跳过（已处理过）"}[action]
        trace.step(f"order {o['id']}", f"¥{o['amount']:>6}  {label}")
        cursor = max(cursor, o["seq"])   # 游标只前进
    trace.step("游标推进到", f"seq={cursor}")
    trace.close("处理完，睡眠等下一轮")
    return cursor


def run() -> dict:
    trace.banner("③", "定时式", "定时/事件唤醒 · 闸门 = 幂等键 + 游标（可安全重启）")
    if banner_note():
        trace.step("⚠ 开关", banner_note())

    cursor = 0
    cursor = wake(1, cursor, "第一次唤醒：从头拉")           # 处理 seq 1-5
    # ——— 模拟进程重启：游标和幂等键都持久化在 DB/Redis，重启后都还在 ———
    # 丢的只是内存里的工作态；'处理到哪了(游标)'和'处理过谁(幂等键)'都落了库。
    trace.step("〈事故〉", "进程重启：游标已落库=5，幂等键也在持久化存储中")
    cursor = wake(2, cursor, "重启后唤醒：从持久化游标 seq=5 继续")  # 无增量→空转
    # ——— 模拟消息中间件重复投递一条旧事件（at-least-once 投递常有）———
    trace.tick(3, "消息队列重复投递了 order A002（旧事件）")
    dup = {"seq": 2, "id": "A002", "amount": 8600}
    action = process(dup)   # 幂等键仍在则跳过；控制点关闭则重复处理
    ok = (action == "skip_dup")
    trace.gate(ok, "幂等键命中 → 重复投递被安全丢弃"
               if ok else "⚠ 控制点已关闭：幂等失效，A002 被二次入账")
    trace.close("重复投递未造成二次入账" if ok else "裸奔：同一笔重复处理了")

    trace.summary([
        f"最终游标 seq={cursor}，已处理订单 {sorted(_processed)}",
        "重启不从头再来（靠游标）；重复投递不二次处理（靠幂等键）。",
        "把 process() 里的幂等判断去掉，第 3 圈就会把 A002 重复入账一次。",
    ])
    return {"cursor": cursor, "processed": sorted(_processed)}


if __name__ == "__main__":
    run()
