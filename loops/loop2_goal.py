"""
循环 ② 目标式 —— 人定目标，系统跑到达标
════════════════════════════════════════════════════════════════════
人的位置：只在两端。给一个可验证的目标 + 预算，中间它自己规划、执行、
          跑验证，达标或超预算才回来。
适合：完成标准可以客观判定的任务——测试通过、账对平、指标达标。
真实案例：阿里云通义灵码——900 万下载、15 亿行代码被采纳，对"完成"的
          判据是生成的单测能编译运行通过。

这一版要讲清楚的**唯一控制点**：
    完成不由模型宣布，由独立验证器判定。
    模型每轮说"我改好了"一文不值；一段独立的、确定性的 verifier 跑一遍
    才算数。再加**轮数 + 成本双上限**，防止不可解的任务把循环拖死。
    退出只有两种：达标，或超预算。

行业反例大家都知道：某明星编码 agent 官方演示很漂亮，独立评测 20 个任务
只成功 3 个——差距就差在"完成"没法被客观判定。下面的 demo 里，模型会
先"谎报完成"，看 verifier 怎么把它按回去继续干。
"""
from __future__ import annotations
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import trace
from common.switch import control_off, banner_note


# ─────────────────────────── 目标与验证器 ───────────────────────────
# 目标：把配置里的三项凑齐并取值正确。verifier 是一组断言，机器判定，
# 与"写配置的模型"完全分开。这就是"完成 = 测试通过"的最小骨架。
TARGET = {"port": 8080, "timeout": 30, "retries": 3}


def verifier(config: dict) -> tuple[bool, list[str]]:
    """独立验证器：返回 (是否全过, 失败项列表)。不看模型怎么说，只看事实。"""
    fails = []
    for k, want in TARGET.items():
        if config.get(k) != want:
            # ← 想手动关验证器？注释掉这一行 fails.append，它就永远说“全过”（=信模型自述）
            fails.append(f"{k}={config.get(k)} 期望 {want}")
    return (len(fails) == 0), fails


# ─────────────────────────── 模型（桩）───────────────────────────
# 一个会"逐步逼近、且中途谎报完成"的假模型：
#   - 第 1 轮：只补一项，却宣称"已完成"（考验 verifier 敢不敢驳回）
#   - 之后每轮补齐一项，直到正确
class DraftingModel:
    def __init__(self):
        self._round = 0
        self._plan = [
            {"port": 8080},                                   # 第1轮：只给1项
            {"port": 8080, "timeout": 30},                    # 第2轮
            {"port": 8080, "timeout": 30, "retries": 3},      # 第3轮：达标
        ]

    def propose(self, feedback: list[str]) -> tuple[dict, bool]:
        cfg = self._plan[min(self._round, len(self._plan) - 1)]
        claims_done = (self._round == 0)  # 第1轮谎报完成
        self._round += 1
        return dict(cfg), claims_done


# ─────────────────────────── 目标式循环 ───────────────────────────
def run(max_rounds: int = 5, cost_budget: float = 1.0) -> dict:
    trace.banner("②", "目标式", "人定目标，系统跑到达标 · 闸门 = 独立验证器 + 预算双上限")
    trace.step("目标", f"{TARGET}（可机器判定）")
    trace.step("预算", f"最多 {max_rounds} 轮 / 成本上限 {cost_budget}")
    if banner_note():
        trace.step("⚠ 开关", banner_note())

    model = DraftingModel()
    feedback: list[str] = []
    spent = 0.0
    outcome = "unknown"
    for n in range(1, max_rounds + 1):
        cost_per_round = 0.25
        if spent + cost_per_round > cost_budget:
            trace.tick(n)
            trace.gate(False, f"再跑一轮将超成本预算（已花 {spent}）→ 退出")
            outcome = "budget_exceeded"
            break
        spent += cost_per_round

        trace.tick(n, f"已花成本 {spent:.2f}")
        config, claims_done = model.propose(feedback)
        trace.step("模型产出", str(config))
        if claims_done:
            trace.step("模型声称", "「我已经完成了」")

        if control_off() and claims_done:   # ← 开关：不跑 verifier，信模型自述
            trace.gate(True, "⚠ 控制点已关闭：信了模型的自述 → 当作完成（实际未达标）")
            trace.close("裸奔退出")
            outcome = "unsafe_trusted"
            break

        passed, fails = verifier(config)
        if passed:
            trace.gate(True, "验证器：全部断言通过 → 真正达标")
            trace.close("达标退出")
            outcome = "passed"
            break
        # 关键：模型说完成、验证器说没有，以验证器为准，继续
        reason = "验证器驳回：" + "；".join(fails)
        if claims_done:
            reason = "模型谎报完成，" + reason
        trace.gate(False, reason)
        feedback = fails
        trace.close("带着失败项进入下一轮")

    trace.summary([
        f"结局：{ {'passed':'达标','budget_exceeded':'超预算退出','unknown':'未收敛','unsafe_trusted':'裸奔·信了模型自述(未达标)'}[outcome] }"
        f" · 共 {n} 轮 · 花费 {spent:.2f}",
        "完成与否始终由 verifier 说了算，模型的自我宣布不作数。",
        "把 cost_budget 调到 0.4，看不可达时预算如何兜底止损。",
    ])
    return {"outcome": outcome, "rounds": n, "spent": spent}


if __name__ == "__main__":
    run()
