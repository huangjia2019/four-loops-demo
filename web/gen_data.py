"""
生成网页 UI 的数据 —— 跑真实的四个循环，把玻璃罩事件录制成 JSON。

    MOCK_LLM=1 python3 web/gen_data.py

产出 web/data.json：UI 和终端共用这一份真实运行数据，不会各写一套对不上。
每次改了循环逻辑，重跑这个脚本，UI 自动跟着变。
"""
from __future__ import annotations
import sys, os, io, json, contextlib

os.environ.setdefault("MOCK_LLM", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import trace
from loops import loop1_dialog, loop2_goal, loop3_scheduled, loop4_pipeline

# 每个循环：函数 + 给 UI 的元信息（控制点、真实案例、人怎么控制）
SPECS = [
    dict(key="dialog", color="#15a0a0", fn=loop1_dialog.run,
         control="发送前验收清单", control_sub="生成 ≠ 批准：模型写答案，清单决定能不能发",
         case="阿里店小蜜", case_stat="转人工率 ↓45%",
         human="人事先把「什么情况不许自答」写成清单，之后循环替你先过一遍",
         file="loops/loop1_dialog.py"),
    dict(key="goal", color="#1f9d4d", fn=loop2_goal.run,
         control="独立验证器 + 预算双上限", control_sub="模型说完成不算数，verifier 跑一遍才算",
         case="通义灵码", case_stat="15 亿行代码被采纳",
         human="人只在两端出现：给可验证目标 + 预算，中间它自己跑到达标",
         file="loops/loop2_goal.py"),
    dict(key="scheduled", color="#0f8fd0", fn=loop3_scheduled.run,
         control="游标 + 幂等键", control_sub="重启从游标继续，重复投递被幂等键丢弃",
         case="蚂蚁风控", case_stat="全链路自动化率 90%",
         human="人退到环外：定时器/事件唤醒，人只在大额结果上复核",
         file="loops/loop3_scheduled.py"),
    dict(key="pipeline", color="#9b2fae", fn=loop4_pipeline.run,
         control="例外队列 + 补偿", control_sub="低置信/超额进例外队列，下游失败自动补偿",
         case="众安理赔", case_stat="自动化率 59% · 最快 15 秒",
         human="人从操作者变成例外处理者：只裁决被拦下的那几件",
         file="loops/loop4_pipeline.py"),
]

NAMES = {"dialog": "① 对话式", "goal": "② 目标式",
         "scheduled": "③ 定时式", "pipeline": "④ 流水线式"}


def run_one(spec) -> dict:
    trace.record_on()
    with contextlib.redirect_stdout(io.StringIO()):
        spec["fn"]()
    events = trace.record_dump()
    return {
        "key": spec["key"], "name": NAMES[spec["key"]], "color": spec["color"],
        "control": spec["control"], "control_sub": spec["control_sub"],
        "case": spec["case"], "case_stat": spec["case_stat"],
        "human": spec["human"], "file": spec["file"],
        "events": events,
    }


def main() -> int:
    data = {"loops": [run_one(s) for s in SPECS]}
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    n = sum(len(l["events"]) for l in data["loops"])
    print(f"wrote {out}  ·  {len(data['loops'])} loops · {n} events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
