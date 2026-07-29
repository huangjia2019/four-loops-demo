"""
循环 ① 对话式 —— 人每轮发起，每轮验收
════════════════════════════════════════════════════════════════════
人的位置：一直在环里。你发一句 → 它改一版 → 你看一眼。
适合：验收标准还在人脑子里的工作，改一版看一版。
真实案例：阿里店小蜜（IT之家报道）——转人工率下降 45%，验收线画在
          "什么情况不许自答"。

这一版要讲清楚的**唯一控制点**：
    生成 ≠ 批准。
    模型负责写答案，一张「发送前验收清单」决定这答案能不能自动发出去。
    清单不放行的，一律转人工。清单是独立于模型的一段确定性代码，
    可评审、可审计、可单测。

把清单删掉，模型就会把"退款"这种高风险回复也直接发出去——
那正是裸对话循环最危险的地方。运行下面的 demo，看闸门怎么拦下它。
"""
from __future__ import annotations
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.model import mock_reply
from common import trace
from common.switch import control_off, banner_note


# ─────────────────────── 发送前验收清单（闸门）───────────────────────
# 这就是店小蜜那条"什么情况不许自答"的工程化。每条规则都是一个纯函数，
# 输入模型草稿 + 信号，输出放行/拦下。规则入库即可评审，改规则不用动模型。
CONFIDENCE_FLOOR = 0.6


def acceptance_check(draft: dict) -> tuple[bool, str]:
    """返回 (是否放行, 理由)。任一条不过就转人工。"""
    if control_off():                       # ← 开关：NO_CONTROL=1 时跳过整张清单
        return True, "⚠ 控制点已关闭：一律放行（裸奔）"
    # ┌─ 想手动关控制点？把下面这三条 if 注释掉即可（别动 one_turn 里的调用！）─┐
    if draft["intent_high_risk"]:
        return False, "命中高风险意图（退款/投诉/索赔）→ 强制转人工"
    if draft["confidence"] < CONFIDENCE_FLOOR:
        return False, f"置信度 {draft['confidence']} < {CONFIDENCE_FLOOR} → 不自答"
    if not draft["cites_order"] and "订单" in draft["draft"]:
        return False, "回复涉及订单却未引用订单事实 → 防编造"
    # └─ 注释掉上面三条 → 只剩下面这行 return True → 一律放行（=关掉控制点，不会报错）─┘
    return True, f"置信度 {draft['confidence']}，无高风险信号，可自动发出"


# ─────────────────────────── 一圈对话 ───────────────────────────
def one_turn(n: int, user_msg: str) -> str:
    """一圈 = 人发起一句 → 模型出草稿 → 清单裁决 → 发出 or 转人工。"""
    trace.tick(n, f"用户：{user_msg}")
    draft = mock_reply(system="你是「福来包子铺」的客服", user=user_msg)
    trace.step("模型草稿", draft["draft"])
    trace.step("信号", f"conf={draft['confidence']}  引用订单={draft['cites_order']}"
                       f"  高风险={draft['intent_high_risk']}")
    passed, reason = acceptance_check(draft)
    trace.gate(passed, reason)
    if passed:
        trace.close("已自动发送")
        return "auto_sent"
    trace.escalate("草稿存草稿箱，转人工席接手")
    trace.close("人工处理")
    return "escalated"


def run() -> dict:
    trace.banner("①", "对话式", "人每轮发起、每轮验收 · 闸门 = 发送前验收清单")
    if banner_note():
        trace.step("⚠ 开关", banner_note())
    # 三句典型消息：正常问询 / 退款（高风险）/ 无订单事实的模糊问询
    msgs = [
        "订单 A2381 今天能到吗？",     # 引用了订单、置信高 → 放行
        "你们这什么破店，我要退款！",   # 高风险意图 → 拦下转人工
        "你们几点关门",               # 泛问、无订单事实 → 放行（不涉及订单）
    ]
    stats = {"auto_sent": 0, "escalated": 0}
    for i, m in enumerate(msgs, 1):
        stats[one_turn(i, m)] += 1
    total = sum(stats.values())
    trace.summary([
        f"共 {total} 轮：自动发送 {stats['auto_sent']} · 转人工 {stats['escalated']}",
        f"转人工率 {stats['escalated']/total:.0%} —— 全部由清单决定，模型无权自己放行",
        "把 acceptance_check() 删掉，第 2 轮的退款回复就会被直接发出去。",
    ])
    return stats


if __name__ == "__main__":
    run()
