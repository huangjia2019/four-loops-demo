"""
循环 ④ 流水线式 —— 事件驱动持续运行，人只处理例外
════════════════════════════════════════════════════════════════════
人的位置：退到最外面，从操作者变成例外处理者。整条流程自动推进，
          人不点任何一步的"继续"，只在被叫到时处理例外。
适合：多步业务流程——理赔、对账、工单。
真实案例：众安保险理赔年报（央广网）——一年 9.66 亿件，自动化率 59%，
          最快 15 秒结案；剩下 41% 不是做不到，是设计成必须走人工核赔。

这一版要讲清楚的**唯一控制点**：
    人只处理例外 —— 例外队列 + 补偿。
    - 每一步有确定性验收标准，过了才进下一步。
    - 低置信 / 超金额 / 疑欺诈 → 进例外队列，人工裁决后才继续。
    - 已经发生的动作（如打款）可补偿、可回滚：下游失败时自动冲正。
    自动化率不是越高越好，41% 走人工是**设计出来的**安全边界。

下面的 demo 跑一批理赔：多数自动过，两笔进例外队列等人裁决，还有一笔
在"打款"后遇到下游失败，触发补偿把款冲回去。
"""
from __future__ import annotations
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import trace
from common.switch import control_off, banner_note


# ───────────────────────── 一批理赔申请 ─────────────────────────
CLAIMS = [
    {"id": "C01", "amount": 200,   "confidence": 0.95, "fraud": False},
    {"id": "C02", "amount": 900,   "confidence": 0.91, "fraud": False},
    {"id": "C03", "amount": 60000, "confidence": 0.88, "fraud": False},  # 超额→例外
    {"id": "C04", "amount": 500,   "confidence": 0.55, "fraud": False},  # 低置信→例外
    {"id": "C05", "amount": 1500,  "confidence": 0.93, "fraud": False},  # 打款后下游失败→补偿
]

AMOUNT_CEILING = 50000     # 超过必须人工核赔
CONFIDENCE_FLOOR = 0.75    # 低于必须人工核赔


# ─────────────────────── 流水线各步（每步有验收）───────────────────────
def stage_intake(claim: dict) -> tuple[bool, str]:
    ok = claim["amount"] > 0
    return ok, "受理：材料齐全" if ok else "受理：金额非法"


def stage_assess(claim: dict) -> tuple[bool, str]:
    """核赔闸门：任一条命中 → 判为例外，交人工。"""
    if control_off():                       # ← 开关：不拦例外，一律自动放行
        return True, "⚠ 控制点已关闭：跳过例外队列，直接自动理算（裸奔）"
    # ┌─ 想手动关例外队列？把下面这三条 if 注释掉即可（别动 run() 里对本函数的调用）─┐
    if claim["fraud"]:
        return False, "疑似欺诈"
    if claim["amount"] > AMOUNT_CEILING:
        return False, f"金额 ¥{claim['amount']} 超上限 ¥{AMOUNT_CEILING}"
    if claim["confidence"] < CONFIDENCE_FLOOR:
        return False, f"置信度 {claim['confidence']} < {CONFIDENCE_FLOOR}"
    # └─ 注释掉上面三条 → 只剩下面这行 return True → 一切都自动放行（不会报错）─┘
    return True, "核赔通过（可自动理算）"


def stage_payout(claim: dict) -> tuple[bool, str]:
    """打款 + 下游对账。C05 模拟下游对账失败，触发补偿。"""
    paid = claim["amount"]
    downstream_ok = claim["id"] != "C05"
    if not downstream_ok:
        # 补偿：已打的款冲正回滚，保持账一致
        return False, f"已打款 ¥{paid}，下游对账失败 → 补偿冲正 ¥{paid}"
    return True, f"打款 ¥{paid} 成功，结案"


# ─────────────────────── 流水线循环 ───────────────────────
def run() -> dict:
    trace.banner("④", "流水线式", "事件驱动持续运行 · 闸门 = 例外队列 + 补偿")
    if banner_note():
        trace.step("⚠ 开关", banner_note())
    exception_queue: list[tuple[dict, str]] = []
    stats = {"auto_closed": 0, "exception": 0, "compensated": 0}

    for n, claim in enumerate(CLAIMS, 1):
        trace.tick(n, f"理赔 {claim['id']}  ¥{claim['amount']}  conf={claim['confidence']}")

        ok, msg = stage_intake(claim)
        trace.step("① 受理", msg)
        if not ok:
            trace.close("受理不过，退回")
            continue

        ok, msg = stage_assess(claim)
        if not ok:
            trace.escalate(f"核赔 → 例外队列：{msg}")
            exception_queue.append((claim, msg))
            stats["exception"] += 1
            trace.close("人不处理就不往下走")
            continue
        trace.step("② 核赔", msg)

        ok, msg = stage_payout(claim)
        if not ok:
            trace.gate(False, "③ 理算：" + msg)
            stats["compensated"] += 1
            trace.close("补偿完成，账务一致")
            continue
        trace.step("③ 理算", msg)
        trace.gate(True, "全流程自动走完")
        stats["auto_closed"] += 1
        trace.close("结案")

    # ——— 人工处理例外队列（异步、批量）———
    if exception_queue:
        print()
        trace.step("〈人工席〉", f"例外队列 {len(exception_queue)} 件，逐件裁决：")
        for claim, why in exception_queue:
            trace.step(f"  {claim['id']}", f"{why} —— 人工核赔后放行/驳回")

    total = len(CLAIMS)
    auto_rate = stats["auto_closed"] / total
    trace.summary([
        f"共 {total} 件：自动结案 {stats['auto_closed']} · 例外 {stats['exception']} · 补偿 {stats['compensated']}",
        f"自动化率 {auto_rate:.0%} —— 其余走例外队列，是设计出来的安全边界（对标众安 59%）。",
        "人从'逐件点继续'变成'只处理被拦下的那几件'。",
    ])
    return stats


if __name__ == "__main__":
    run()
