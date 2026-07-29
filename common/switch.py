"""
控制点总开关 —— 把「删掉控制点看后果」做成一个运行时开关，不用手改代码。

    NO_CONTROL=1 python3 loops/loop1_dialog.py    # 关掉控制点跑一遍
    NO_CONTROL=1 python3 scripts/smoke_all.py     # 四条断言当场翻红

四种循环各自在自己那处控制点检查这个开关：开关一开，控制点被跳过，
循环退回「裸奔」，危险行为当场出现（退款被自动发出、模型谎报完成被采信、
重复投递二次入账、超额自动打款）。

为什么要有它：手动注释代码极易改错 —— 比如只注释掉调用、漏了赋值，
就会 NameError 崩掉，而不是「看到裸奔」。一个开关，干净、可逆、可现场演示。
"""
from __future__ import annotations
import os


def control_off() -> bool:
    """控制点是否被关闭。NO_CONTROL=1 时返回 True。"""
    return os.environ.get("NO_CONTROL") == "1"


def banner_note():
    """若控制点已关闭，返回一句醒目提示（供 trace 显示），否则 None。"""
    if control_off():
        return "⚠ 控制点已关闭（NO_CONTROL=1）—— 循环在裸奔"
    return None
