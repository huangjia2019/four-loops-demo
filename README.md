# four-loops-demo

四种 Agent 循环的最小可运行示例：**对话式、目标式、定时式、流水线式**。
每种循环只演示一处控制点；控制点可以一键关掉，看循环「裸奔」。

## 跑起来

默认走 MOCK 假模型，**零依赖、纯标准库**，不用装包、不用 API key。

```bash
# 冒烟：四种循环各跑一遍，七条断言守四个控制点
MOCK_LLM=1 python3 scripts/smoke_all.py

# 单独看一种循环的运行轨迹
MOCK_LLM=1 python3 loops/loop1_dialog.py

# 关掉控制点，看循环裸奔（断言会翻红）
NO_CONTROL=1 python3 scripts/smoke_all.py

# 网页演示台（能点、可交互）
bash web/serve.sh        # 起服务，浏览器打开它打印的网址
```

## 四种循环

| 循环 | 文件 | 控制点 |
|:--|:--|:--|
| ① 对话式 | `loops/loop1_dialog.py` | 发送前验收清单 |
| ② 目标式 | `loops/loop2_goal.py` | 独立验证器 + 预算双上限 |
| ③ 定时式 | `loops/loop3_scheduled.py` | 游标 + 幂等键 |
| ④ 流水线式 | `loops/loop4_pipeline.py` | 例外队列 + 补偿 |

关掉任一控制点（`NO_CONTROL=1`，或注释掉源码里标了「手动关」的规则块），
对应的断言立刻变红 —— 这就是控制点存在的意义。

## 结构

```
loops/     四种循环，每种一个自包含文件
common/    MOCK 模型桩 · 玻璃罩 trace · 控制点开关(switch.py)
scripts/   smoke_all.py 冒烟测试
web/       网页演示台(serve.sh 启动)
```

接真模型：装 `anthropic`、设 `ANTHROPIC_API_KEY`、去掉 `MOCK_LLM`。
循环的骨架和控制点与模型无关 —— 换不换真模型，控制点该拦的照样拦。

## License

MIT
