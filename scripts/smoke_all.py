"""
纯标准库冒烟测试 —— 不装任何依赖即可验证四个循环的核心行为。

    MOCK_LLM=1 python scripts/smoke_all.py

每个断言对应该循环"唯一控制点"是否真的生效：
  ① 对话式    退款（高风险）必须被清单拦下转人工
  ② 目标式    模型谎报完成不算数，最终由 verifier 判达标
  ③ 定时式    重启不重复、重复投递被幂等丢弃
  ④ 流水线式  超额/低置信进例外队列，下游失败触发补偿
断言全绿，说明四个控制点都在。任何一条被删掉，这里立刻变红。
"""
from __future__ import annotations
import sys, os, io, contextlib

os.environ.setdefault("MOCK_LLM", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loops import loop1_dialog, loop2_goal, loop3_scheduled, loop4_pipeline


def _quiet(fn, *a, **k):
    """跑循环但吞掉终端输出，只留返回值做断言。"""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def check(name: str, cond: bool):
    print(f"  {'✔' if cond else '✘ FAIL'}  {name}")
    assert cond, name


def main() -> int:
    print("四种循环 · 冒烟测试（MOCK，纯标准库）")

    # ① 对话式：3 轮里恰好 1 轮转人工（那句退款）
    s1 = _quiet(loop1_dialog.run)
    check("① 退款高风险被清单拦下 → 恰 1 轮转人工", s1["escalated"] == 1 and s1["auto_sent"] == 2)

    # ② 目标式：最终达标，且用了多于 1 轮（证明第 1 轮谎报完成被驳回）
    s2 = _quiet(loop2_goal.run)
    check("② 谎报完成被 verifier 驳回，最终真正达标", s2["outcome"] == "passed" and s2["rounds"] >= 3)
    # 预算兜底：极小预算下不达标也能安全止损
    s2b = _quiet(loop2_goal.run, max_rounds=5, cost_budget=0.4)
    check("② 预算过小 → 超预算安全退出（不无限跑）", s2b["outcome"] == "budget_exceeded")

    # ③ 定时式：5 条订单各处理一次，重复投递不增加
    s3 = _quiet(loop3_scheduled.run)
    check("③ 重启+重复投递后仍恰好处理 5 条不重复", len(s3["processed"]) == 5 and s3["cursor"] == 5)

    # ④ 流水线式：2 件进例外队列，1 件补偿，其余自动结案
    s4 = _quiet(loop4_pipeline.run)
    check("④ 超额/低置信入例外队列（2 件）", s4["exception"] == 2)
    check("④ 下游失败触发补偿（1 件）", s4["compensated"] == 1)
    check("④ 其余自动结案（2 件）", s4["auto_closed"] == 2)

    print("\n全部通过 ✔  四个控制点都在。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
