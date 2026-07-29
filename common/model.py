"""
共享「模型」层 —— 两种实现，同一个接口。

设计意图：四个循环演示的重点是**循环骨架和控制点**，不是模型多聪明。
所以默认走 MOCK：一个确定性的、规则式的假模型，零依赖、零 API key、每次
输出一样，方便课堂逐行讲解和断言测试。想看真模型时，设 ANTHROPIC_API_KEY
且不设 MOCK_LLM=1，自动切到 Claude。

    from common.model import complete
    reply = complete(system="你是客服", user="三里屯有咖啡优惠吗")

MOCK 的"智能"全部写在下面的规则里，看得见、改得动——这正是教学要的。
"""
from __future__ import annotations
import os
import re


def use_mock() -> bool:
    """默认离线。只有显式给了 key 且没强制 MOCK，才走真模型。"""
    if os.environ.get("MOCK_LLM") == "1":
        return True
    return not os.environ.get("ANTHROPIC_API_KEY")


# ────────────────────────────── MOCK 模型 ──────────────────────────────
# 一个"够用就好"的规则式桩。它不理解语言，只做关键词匹配 + 模板套用。
# 每个循环需要模型干的活都很窄，这样的桩足以把循环跑起来、把控制点讲清楚。

_REFUND_WORDS = ("退款", "退货", "投诉", "索赔", "差评", "骗", "垃圾", "态度")
_ORDER_RE = re.compile(r"(订单|order)\s*[#:：]?\s*([A-Za-z0-9]+)")


def mock_reply(system: str, user: str) -> dict:
    """
    返回一个结构化草稿，而不是一段纯文本。
    多带一个 confidence 和 cites_order，是为了让「验收清单」那一层有东西可查——
    真实系统里这些信号来自模型的 logprob、工具返回、检索命中，这里用规则模拟。
    """
    text = user.strip()
    hit_refund = any(w in text for w in _REFUND_WORDS)
    m = _ORDER_RE.search(text)
    # 提到订单号 → 我们"检索到了订单事实"，可引用；否则只能泛泛回答
    if m:
        order = m.group(2)
        draft = f"您好，订单 {order} 的信息已为您查到，本店可正常为您处理。"
        cites_order = True
    else:
        draft = "您好，本店营业时间 9:00–22:00，很高兴为您服务。"
        cites_order = False
    # 情绪/高风险意图 → 模型自己也"没底"，confidence 打低
    confidence = 0.45 if hit_refund else (0.9 if cites_order else 0.72)
    return {
        "draft": draft,
        "confidence": round(confidence, 2),
        "cites_order": cites_order,
        "intent_high_risk": hit_refund,
    }


def complete(system: str, user: str) -> str:
    """通用文本补全接口。MOCK 下返回草稿文本；真模型下调 Claude。"""
    if use_mock():
        return mock_reply(system, user)["draft"]
    return _claude_complete(system, user)


# ────────────────────────────── 真模型 ──────────────────────────────
def _claude_complete(system: str, user: str) -> str:
    from anthropic import Anthropic  # 延迟导入：MOCK 路径不需要装 anthropic
    client = Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text
