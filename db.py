import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bom.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                unit_price REAL NOT NULL DEFAULT 0.0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bom_structure (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER NOT NULL,
                child_id INTEGER NOT NULL,
                quantity REAL NOT NULL DEFAULT 1.0,
                FOREIGN KEY (parent_id) REFERENCES materials(id) ON DELETE CASCADE,
                FOREIGN KEY (child_id) REFERENCES materials(id) ON DELETE CASCADE,
                UNIQUE(parent_id, child_id)
            )
        """)


def add_material(code: str, name: str, unit_price: float):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO materials (code, name, unit_price) VALUES (?, ?, ?)",
            (code, name, unit_price),
        )
        return cursor.lastrowid


def update_material(material_id: int, code: str, name: str, unit_price: float):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE materials SET code = ?, name = ?, unit_price = ? WHERE id = ?",
            (code, name, unit_price, material_id),
        )


def delete_material(material_id: int):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))


def get_all_materials():
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials ORDER BY code")
        return [dict(row) for row in cursor.fetchall()]


def get_material_by_id(material_id: int):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_bom_relation(parent_id: int, child_id: int, quantity: float):
    if parent_id == child_id:
        raise ValueError("不能将物料设为自身的子件")
    if _would_create_cycle(parent_id, child_id):
        raise ValueError("添加该关系会造成循环依赖")
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO bom_structure (parent_id, child_id, quantity) VALUES (?, ?, ?)",
            (parent_id, child_id, quantity),
        )


def remove_bom_relation(parent_id: int, child_id: int):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM bom_structure WHERE parent_id = ? AND child_id = ?",
            (parent_id, child_id),
        )


def update_bom_quantity(parent_id: int, child_id: int, quantity: float):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE bom_structure SET quantity = ? WHERE parent_id = ? AND child_id = ?",
            (quantity, parent_id, child_id),
        )


def get_children(parent_id: int):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT m.*, bs.quantity
            FROM bom_structure bs
            JOIN materials m ON bs.child_id = m.id
            WHERE bs.parent_id = ?
            ORDER BY m.code
            """,
            (parent_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_parents(child_id: int):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT m.*, bs.quantity
            FROM bom_structure bs
            JOIN materials m ON bs.parent_id = m.id
            WHERE bs.child_id = ?
            ORDER BY m.code
            """,
            (child_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_root_materials():
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM materials
            WHERE id NOT IN (SELECT DISTINCT child_id FROM bom_structure)
            ORDER BY code
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def _would_create_cycle(parent_id: int, child_id: int) -> bool:
    visited = set()
    stack = [child_id]
    while stack:
        current = stack.pop()
        if current == parent_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        children = get_children(current)
        for c in children:
            stack.append(c["id"])
    return False
