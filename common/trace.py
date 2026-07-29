"""
玻璃罩 —— 把循环的每一圈打印出来。

循环工程最怕的是"黑箱自动运行"。教学演示更要让人**看见**每一圈：
这一轮是谁触发的、模型给了什么、闸门放行还是拦下、状态往哪走。
所有循环共用这一个打印器，终端里就有一致的观感。

同一套调用还能被"录制"成结构化事件（record/dump），喂给网页 UI ——
终端和 UI 共用一份真实运行数据，不会各写一套而对不上。
"""
from __future__ import annotations

# ── 事件录制：网页 UI 用同一份真实运行数据 ──
_REC: list | None = None


def record_on() -> None:
    global _REC
    _REC = []


def record_dump() -> list:
    global _REC
    ev = _REC or []
    _REC = None
    return ev


def _emit(ev: dict) -> None:
    if _REC is not None:
        _REC.append(ev)


# 轻量 ANSI 上色；不支持颜色的终端里就是普通文字，不影响阅读。
_C = {
    "dim": "\033[2m", "bold": "\033[1m", "reset": "\033[0m",
    "green": "\033[32m", "red": "\033[31m", "yellow": "\033[33m",
    "cyan": "\033[36m", "plum": "\033[35m",
}


def _c(s: str, color: str) -> str:
    return f"{_C.get(color,'')}{s}{_C['reset']}"


def banner(loop_no: str, name: str, one_line: str) -> None:
    _emit({"t": "banner", "no": loop_no, "name": name, "sub": one_line})
    print()
    print(_c("━" * 68, "dim"))
    print(f"{_c('循环 ' + loop_no, 'bold')} · {_c(name, 'cyan')}")
    print(_c(one_line, "dim"))
    print(_c("━" * 68, "dim"))


def tick(n: int, note: str = "") -> None:
    """一圈的开头。"""
    _emit({"t": "tick", "n": n, "note": note})
    tag = _c(f"┌ 第 {n} 圈", "bold")
    print(f"\n{tag}  {_c(note,'dim')}")


def step(label: str, value: str = "") -> None:
    _emit({"t": "step", "label": label, "value": value})
    print(f"│  {label:<14}{value}")


def gate(passed: bool, reason: str) -> None:
    """闸门判定 —— 循环里最关键的一行，单独标红/绿。"""
    _emit({"t": "gate", "passed": bool(passed), "reason": reason})
    if passed:
        print(f"│  {_c('✔ 放行', 'green')}       {reason}")
    else:
        print(f"│  {_c('✘ 拦下', 'red')}       {reason}")


def escalate(reason: str) -> None:
    _emit({"t": "escalate", "reason": reason})
    print(f"│  {_c('⇢ 转人工', 'yellow')}     {reason}")


def close(note: str = "") -> None:
    _emit({"t": "close", "note": note})
    print(f"└ {_c(note,'dim')}")


def summary(lines: list[str]) -> None:
    _emit({"t": "summary", "lines": list(lines)})
    print()
    print(_c("── 本轮小结 " + "─" * 54, "plum"))
    for ln in lines:
        print("   " + ln)
    print()
