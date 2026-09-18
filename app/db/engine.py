"""数据库连接层：按数据源 ID 缓存引擎"""
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.db.registry import get_datasource, get_default_id

_engines: dict[str, Engine] = {}


def get_engine(datasource_id: str | None = None) -> Engine:
    """按数据源 ID 返回引擎；不传则用默认数据源"""
    ds_id = datasource_id or get_default_id()
    if ds_id not in _engines:
        ds = get_datasource(ds_id)
        _engines[ds_id] = create_engine(
            ds.url,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
    return _engines[ds_id]


def dispose_engine(datasource_id: str) -> None:
    """释放某个数据源的连接池（删除数据源时调用）"""
    engine = _engines.pop(datasource_id, None)
    if engine is not None:
        engine.dispose()


@contextmanager
def get_connection(datasource_id: str | None = None):
    engine = get_engine(datasource_id)
    conn = engine.connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------- 查询接口：全部加 datasource_id 参数 ----------

def run_query(sql: str, params: dict | None = None,
              datasource_id: str | None = None) -> list[dict[str, Any]]:
    with get_connection(datasource_id) as conn:
        result = conn.execute(text(sql), params or {})
        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in result.fetchall()]


def run_statement(sql: str, params: dict | None = None,
                  datasource_id: str | None = None) -> int:
    with get_connection(datasource_id) as conn:
        result = conn.execute(text(sql), params or {})
        return result.rowcount


def list_tables(datasource_id: str | None = None) -> list[str]:
    return inspect(get_engine(datasource_id)).get_table_names()


def get_table_schema(table: str, datasource_id: str | None = None) -> list[dict[str, Any]]:
    inspector = inspect(get_engine(datasource_id))
    columns = inspector.get_columns(table)
    return [
        {
            "name": col["name"],
            "type": str(col["type"]),
            "nullable": col.get("nullable", True),
            "default": col.get("default"),
        }
        for col in columns
    ]


def get_all_schemas(datasource_id: str | None = None) -> dict[str, list[dict[str, Any]]]:
    return {
        t: get_table_schema(t, datasource_id)
        for t in list_tables(datasource_id)
    }