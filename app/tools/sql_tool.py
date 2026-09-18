"""Text-to-SQL 工具：自然语言 -> SQL -> 执行 -> 返回数据"""
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import SQL_SYSTEM_PROMPT as SYSTEM_PROMPT
from app.db.engine import get_all_schemas, run_query
from app.llm import get_llm

# 只允许只读查询
FORBIDDEN_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|truncate|alter|create|replace|grant|revoke)\b",
    re.IGNORECASE,
)

MAX_RETRY = 3


@dataclass
class SQLResult:
    question: str
    sql: str = ""
    data: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    attempts: int = 0

    @property
    def ok(self) -> bool:
        return bool(self.sql) and not self.error


# ---------- 1. Schema 描述 ----------

def build_schema_text(datasource_id: str | None = None) -> str:
    """把所有表结构格式化成文本，喂给 LLM"""
    schemas = get_all_schemas(datasource_id)
    lines = []
    for table, columns in schemas.items():
        lines.append(f"表名: {table}")
        for col in columns:
            nullable = "" if col["nullable"] else " NOT NULL"
            lines.append(f"  - {col['name']} ({col['type']}{nullable})")
        lines.append("")
    return "\n".join(lines).strip()


# ---------- 2. SQL 提取与校验 ----------

def extract_sql(text: str) -> str:
    fence = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1)
    return text.strip().rstrip(";").strip()


def is_safe(sql: str) -> tuple[bool, str]:
    stripped = sql.strip().lower()
    if not stripped.startswith("select") and not stripped.startswith("with"):
        return False, "只允许 SELECT 查询"
    if FORBIDDEN_KEYWORDS.search(sql):
        return False, "SQL 中包含被禁止的写操作关键字"
    return True, ""


# ---------- 3. 主流程 ----------

def text_to_sql(
    question: str,
    datasource_id: str | None = None,
) -> SQLResult:
    """自然语言 -> SQL -> 执行，带自我纠错"""
    result = SQLResult(question=question)
    llm = get_llm()
    schema = build_schema_text(datasource_id)

    system_msg = SystemMessage(content=SYSTEM_PROMPT.format(schema=schema))
    messages = [system_msg, HumanMessage(content=question)]

    for attempt in range(1, MAX_RETRY + 1):
        result.attempts = attempt
        resp = llm.invoke(messages)
        sql = extract_sql(resp.content)
        result.sql = sql

        safe, reason = is_safe(sql)
        if not safe:
            result.error = f"SQL 未通过安全校验: {reason}"
            return result

        try:
            data = run_query(sql, datasource_id=datasource_id)
            result.data = data
            result.error = ""
            return result
        except Exception as e:
            err = str(e)
            result.error = err
            messages.append(resp)
            messages.append(HumanMessage(
                content=f"执行报错：{err}\n请修正 SQL 后重新输出，只输出 SQL。"
            ))

    return result


# ---------- 4. 便捷入口 ----------

def ask(
    question: str,
    datasource_id: str | None = None,
    verbose: bool = True,
) -> SQLResult:
    result = text_to_sql(question, datasource_id=datasource_id)
    if verbose:
        print(f"[问] {question}")
        print(f"[SQL] {result.sql}")
        if result.error:
            print(f"[错误] {result.error}")
        else:
            print(f"[结果] {len(result.data)} 行")
            for row in result.data[:5]:
                print(f"   {row}")
            if len(result.data) > 5:
                print(f"   ... 另有 {len(result.data) - 5} 行")
        print()
    return result