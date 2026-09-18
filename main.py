"""智数析言：智能数据分析 Agent —— 命令行入口"""
import argparse
import time
import uuid

from app.agent.graph import run
from app.config import settings


BANNER = """
╔══════════════════════════════════════════════════════════╗
║  智数析言 · 智能数据分析 Agent                            ║
║  自然语言提问 → SQL 查询 → Python 分析 → 图表 → 结论       ║
╚══════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
用法：
  python main.py                          # 进入交互模式（带会话记忆）
  python main.py "你的问题"                # 单次提问（不带记忆）
  python main.py --session <id> "问题"     # 指定会话 ID 提问

交互模式下：
  exit / quit / q    退出
  new                开启新会话（清空历史）
  history            查看当前会话历史
  help / h / ?       显示帮助

示例问题：
  - 各地区总销售额是多少？
  - 那华东呢？           （追问，依赖上一轮）
  - 换成饼图             （追加需求，依赖上一轮）
"""


def _print_header(session_id: str = "") -> None:
    print(BANNER)
    print(f"模型:    {settings.deepseek_model}")
    print(f"数据库:  {settings.db_type} ({settings.database_url})")
    print(f"输出:    {settings.output_dir}")
    tracing = "开启" if settings.langchain_tracing_v2 else "关闭"
    print(f"追踪:    LangSmith {tracing}")
    if session_id:
        print(f"会话:    {session_id}")
    print()


def _print_state(state: dict, elapsed: float) -> None:
    print("=" * 64)
    print(f"[问题] {state['question']}")

    rewritten = state.get("rewritten_question")
    if rewritten and rewritten != state["question"]:
        print(f"[改写] {rewritten}")
    print()

    print("[执行步骤]")
    for i, s in enumerate(state.get("steps", []), 1):
        print(f"  {i}. {s}")
    print()

    if state.get("sql"):
        print(f"[SQL]\n{state['sql']}\n")

    if state.get("python_result") is not None:
        print(f"[Python 分析]\n{state['python_result']}\n")

    if state.get("chart_path"):
        print(f"[图表] {state['chart_path']}\n")

    print("[结论]")
    print(state.get("conclusion", "(无)"))
    print()
    print(f"[耗时] {elapsed:.2f}s")
    print()


def ask_once(question: str, session_id: str = "") -> None:
    t0 = time.time()
    try:
        state = run(question, session_id=session_id, verbose=False)
    except Exception as e:
        print(f"[错误] 执行失败: {type(e).__name__}: {e}")
        return
    _print_state(state, time.time() - t0)


def interactive_loop() -> None:
    session_id = "cli_" + uuid.uuid4().hex[:8]
    _print_header(session_id)
    print("请输入你的数据问题（输入 help 查看用法，exit 退出，new 开新会话）")
    print()

    while True:
        try:
            question = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        if not question:
            continue

        cmd = question.lower()
        if cmd in {"exit", "quit", "q"}:
            print("再见。")
            break
        if cmd in {"help", "h", "?"}:
            print(HELP_TEXT)
            continue
        if cmd == "new":
            session_id = "cli_" + uuid.uuid4().hex[:8]
            print(f"[新会话] {session_id}\n")
            continue
        if cmd == "history":
            from app.agent.memory import get_store
            hist = get_store().get(session_id)
            if not hist:
                print("[历史] 当前会话暂无记录\n")
            else:
                for i, turn in enumerate(hist, 1):
                    print(f"  {i}. 问: {turn['question']}")
                    print(f"     答: {turn['answer'][:80]}...")
                print()
            continue

        try:
            ask_once(question, session_id=session_id)
        except KeyboardInterrupt:
            print("\n[中断] 已取消当前问题。\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="智数析言：智能数据分析 Agent",
        add_help=False,
    )
    parser.add_argument("question", nargs="?", help="要分析的问题")
    parser.add_argument("-q", "--question", dest="question_opt", help="同位置参数")
    parser.add_argument("-s", "--session", dest="session_id", default="", help="会话 ID")
    parser.add_argument("-h", "--help", action="store_true", help="显示帮助")
    args = parser.parse_args()

    if args.help:
        print(HELP_TEXT)
        return

    question = args.question_opt or args.question
    if question:
        _print_header(args.session_id)
        ask_once(question, session_id=args.session_id)
    else:
        interactive_loop()


if __name__ == "__main__":
    main()