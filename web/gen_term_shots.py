"""
把四种循环的真实终端输出，渲染成终端风格的 HTML（供 puppeteer 截成 PNG）。
配套 web/term_shots.sh。产出 web/_term/*.html，再由 term_capture.js 截图到 shots/。

这些图是演示手册（演示手册-step-by-step.md）里引用的真机截屏。
"""
from __future__ import annotations
import sys, os, io, html, subprocess, contextlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("MOCK_LLM", "1")
sys.path.insert(0, REPO)
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_term")
os.makedirs(OUTDIR, exist_ok=True)

# 终端配色（与网页 UI / deck 代码卡一致）
PAL = {"31": "#ff8a7a", "32": "#7ee08a", "33": "#f5c85a", "36": "#66d9ef",
       "35": "#c792ea", "2": "#8aa0b5"}


def ansi_to_html(text: str) -> str:
    """把我们只用到的那几个 ANSI SGR 码转成 span。"""
    out, i, n = [], 0, len(text)
    color, bold, dim = None, False, False

    def span(s):
        if not s:
            return ""
        style = []
        c = color or ("#ffffff" if bold else None)
        if dim:
            c = PAL["2"]
        if c:
            style.append(f"color:{c}")
        if bold:
            style.append("font-weight:700")
        esc = html.escape(s)
        return f'<span style="{";".join(style)}">{esc}</span>' if style else esc

    buf = ""
    while i < n:
        if text[i] == "\033" and text[i:i + 2] == "\033[":
            j = text.find("m", i)
            if j != -1:
                out.append(span(buf)); buf = ""
                code = text[i + 2:j]
                for c in code.split(";"):
                    if c in ("0", ""):
                        color, bold, dim = None, False, False
                    elif c == "1":
                        bold = True
                    elif c == "2":
                        dim = True
                    elif c in PAL and c not in ("2",):
                        color = PAL[c]
                    elif c in PAL:
                        color = PAL[c]
                i = j + 1
                continue
        buf += text[i]; i += 1
    out.append(span(buf))
    return "".join(out)


TPL = """<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a1626;padding:26px;font-family:"SF Mono","Cascadia Code",Consolas,monospace}}
.term{{width:940px;background:#0b1f33;border-radius:12px;overflow:hidden;
  box-shadow:0 18px 50px rgba(0,0,0,.45);border:1px solid #1c3350}}
.bar{{display:flex;align-items:center;gap:8px;padding:11px 15px;background:#0e2540;border-bottom:1px solid #1c3350}}
.dot{{width:12px;height:12px;border-radius:50%}}
.r{{background:#ff5f56}}.y{{background:#ffbd2e}}.g{{background:#27c93f}}
.ttl{{color:#8fb0cc;font-size:12.5px;margin-left:10px}}
pre{{padding:16px 20px;color:#e8eef4;font-size:13.5px;line-height:1.62;white-space:pre-wrap;word-break:break-word}}
</style></head><body>
<div class="term"><div class="bar"><span class="dot r"></span><span class="dot y"></span>
<span class="dot g"></span><span class="ttl">{title}</span></div>
<pre>{body}</pre></div></body></html>"""


def cmd_line(cmd: str) -> str:
    return f'<span style="color:#66d9ef">$ {html.escape(cmd)}</span>\n'


def run_capture(argv) -> str:
    r = subprocess.run(argv, cwd=REPO, capture_output=True, text=True,
                       env={**os.environ, "MOCK_LLM": "1"})
    return r.stdout + r.stderr


def run_capture_env(argv, extra) -> str:
    r = subprocess.run(argv, cwd=REPO, capture_output=True, text=True,
                       env={**os.environ, "MOCK_LLM": "1", **extra})
    return r.stdout + r.stderr


def write(name, title, body_html):
    with open(os.path.join(OUTDIR, name + ".html"), "w", encoding="utf-8") as f:
        f.write(TPL.format(title=html.escape(title), body=body_html))
    print("wrote", name)


def main():
    PY = sys.executable
    # 1) smoke
    body = cmd_line("MOCK_LLM=1 python3 scripts/smoke_all.py") + ansi_to_html(run_capture([PY, "scripts/smoke_all.py"]))
    write("shot-smoke", "scripts/smoke_all.py · 七条断言守四个控制点", body)

    # 2) tree
    ls = run_capture(["ls", "loops/"])
    head = run_capture(["head", "-16", "loops/loop1_dialog.py"])
    body = (cmd_line("ls loops/") + ansi_to_html(ls) + "\n"
            + cmd_line("head -16 loops/loop1_dialog.py") + ansi_to_html(head))
    write("shot-tree", "一个循环就是一个文件", body)

    # 3-6) 四种循环
    for key, n in [("loop1_dialog", 1), ("loop2_goal", 2), ("loop3_scheduled", 3), ("loop4_pipeline", 4)]:
        body = cmd_line(f"MOCK_LLM=1 python3 loops/{key}.py") + ansi_to_html(run_capture([PY, f"loops/{key}.py"]))
        write(f"shot-loop{n}", f"loops/{key}.py · 真实运行轨迹", body)

    # 7) 关掉控制点（NO_CONTROL=1）→ smoke 翻红
    out = run_capture_env([PY, "scripts/smoke_all.py"], {"NO_CONTROL": "1"})
    # 让失败行真正“红”起来，匹配“翻红”叙事（错误标记行整行标红）
    marks = ("FAIL", "Traceback", "Error", "assert", "line ")
    red_lines = "\n".join(
        (f"\033[31m{ln}\033[0m" if any(m in ln for m in marks) else ln)
        for ln in out.splitlines())
    write("shot-delred", "关掉控制点（NO_CONTROL=1）→ smoke 立刻翻红",
          cmd_line("NO_CONTROL=1 python3 scripts/smoke_all.py") + ansi_to_html(red_lines))


if __name__ == "__main__":
    main()
