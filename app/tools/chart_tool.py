"""图表生成工具：让 LLM 根据数据自动选图表类型并用 matplotlib 出图"""
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # 无窗口后端，必须放在 pyplot 之前
import matplotlib.pyplot as plt
import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.llm import get_llm

# 中文字体（Windows 常见）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

MAX_RETRY = 3


@dataclass
class ChartResult:
    question: str
    chart_type: str = ""
    code: str = ""
    file_path: str = ""
    error: str = ""
    attempts: int = 0

    @property
    def ok(self) -> bool:
        return bool(self.file_path) and not self.error


# ---------- 提示词 ----------

from app.agent.prompts import CHART_SYSTEM_PROMPT as SYSTEM_PROMPT

# ---------- 工具函数 ----------

def _strip_fence(code: str) -> str:
    fence = re.search(r"```(?:python)?\s*(.*?)```", code, re.DOTALL | re.IGNORECASE)
    return fence.group(1).strip() if fence else code.strip()


def _output_path(prefix: str = "chart") -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return settings.output_dir / f"{prefix}_{ts}.png"


# ---------- 主流程 ----------

def build_chart(
    question: str,
    data: list[dict[str, Any]],
    max_retry: int = MAX_RETRY,
) -> ChartResult:
    result = ChartResult(question=question)

    if not data:
        result.error = "输入数据为空"
        return result

    df = pd.DataFrame(data)
    llm = get_llm()
    out_path = _output_path()
    result.file_path = str(out_path)

    system_msg = SystemMessage(content=SYSTEM_PROMPT.format(
        columns=list(df.columns),
        preview=df.head(3).to_string(),
    ))
    messages = [system_msg, HumanMessage(content=question)]

    for attempt in range(1, max_retry + 1):
        result.attempts = attempt
        resp = llm.invoke(messages)
        code = _strip_fence(resp.content)
        result.code = code

        namespace = {
            "pd": pd, "np": __import__("numpy"), "plt": plt,
            "df": df.copy(),
            "OUTPUT_PATH": str(out_path),
        }

        try:
            exec(code, namespace)
        except Exception as e:
            result.error = f"{type(e).__name__}: {e}"
            messages.append(resp)
            messages.append(HumanMessage(
                content=f"执行报错：{result.error}\n请修正代码后重新输出，只输出 Python 代码。"
            ))
            continue

        if not out_path.exists():
            result.error = "代码执行完毕但未生成图片，请检查是否调用了 plt.savefig"
            continue

        result.error = ""
        result.chart_type = _infer_type(question, code)
        return result

    return result


def _infer_type(question: str, code: str) -> str:
    text = (question + " " + code).lower()
    for key, name in [
        ("pie", "饼图"), ("bar", "柱状图"), ("hist", "直方图"),
        ("scatter", "散点图"), ("plot", "折线图"),
    ]:
        if key in text:
            return name
    return "其他"


# ---------- 便捷入口 ----------

def ask(question: str, data: list[dict[str, Any]], verbose: bool = True) -> ChartResult:
    result = build_chart(question, data)
    if verbose:
        print(f"[问] {question}")
        if result.error:
            print(f"[错误] {result.error}")
        else:
            print(f"[图表] {result.chart_type} -> {result.file_path}")
        print()
    return result