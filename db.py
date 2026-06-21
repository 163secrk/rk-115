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
                unit_price REAL NOT NULL DEFAULT 0.0,
                total_cost REAL NOT NULL DEFAULT 0.0
            )
        """)
        try:
            cursor.execute("ALTER TABLE materials ADD COLUMN total_cost REAL NOT NULL DEFAULT 0.0")
        except sqlite3.OperationalError:
            pass
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
            "INSERT INTO materials (code, name, unit_price, total_cost) VALUES (?, ?, ?, ?)",
            (code, name, unit_price, unit_price),
        )
        return cursor.lastrowid


def update_material(material_id: int, code: str, name: str, unit_price: float):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE materials SET code = ?, name = ?, unit_price = ? WHERE id = ?",
            (code, name, unit_price, material_id),
        )
        update_material_total_cost(material_id, conn)
        update_parent_costs(material_id, conn)


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
    with get_conn() as conn:
        if _would_create_cycle(parent_id, child_id, conn):
            raise ValueError("添加该关系会造成循环依赖")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO bom_structure (parent_id, child_id, quantity) VALUES (?, ?, ?)",
            (parent_id, child_id, quantity),
        )
        update_material_total_cost(parent_id, conn)
        update_parent_costs(parent_id, conn)


def remove_bom_relation(parent_id: int, child_id: int):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM bom_structure WHERE parent_id = ? AND child_id = ?",
            (parent_id, child_id),
        )
        update_material_total_cost(parent_id, conn)
        update_parent_costs(parent_id, conn)


def update_bom_quantity(parent_id: int, child_id: int, quantity: float):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE bom_structure SET quantity = ? WHERE parent_id = ? AND child_id = ?",
            (quantity, parent_id, child_id),
        )
        update_material_total_cost(parent_id, conn)
        update_parent_costs(parent_id, conn)


def get_children(parent_id: int, conn=None):
    if conn is None:
        with get_conn() as conn:
            return get_children(parent_id, conn)
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


def get_parents(child_id: int, conn=None):
    if conn is None:
        with get_conn() as conn:
            return get_parents(child_id, conn)
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


def _would_create_cycle(parent_id: int, child_id: int, conn=None) -> bool:
    visited = set()
    stack = [child_id]
    while stack:
        current = stack.pop()
        if current == parent_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        children = get_children(current, conn)
        for c in children:
            stack.append(c["id"])
    return False


def calculate_material_cost(material_id: int, conn=None) -> float:
    if conn is None:
        with get_conn() as conn:
            return calculate_material_cost(material_id, conn)
    
    cursor = conn.cursor()
    cursor.execute("SELECT unit_price FROM materials WHERE id = ?", (material_id,))
    row = cursor.fetchone()
    self_price = float(row["unit_price"]) if row else 0.0
    
    children = get_children(material_id, conn)
    if not children:
        return self_price
    
    total = self_price
    for child in children:
        child_cost = calculate_material_cost(child["id"], conn)
        total += child_cost * float(child["quantity"])
    return total


def update_material_total_cost(material_id: int, conn=None):
    if conn is None:
        with get_conn() as conn:
            update_material_total_cost(material_id, conn)
            return
    
    cost = calculate_material_cost(material_id, conn)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE materials SET total_cost = ? WHERE id = ?",
        (cost, material_id),
    )


def update_parent_costs(child_id: int, conn=None):
    if conn is None:
        with get_conn() as conn:
            update_parent_costs(child_id, conn)
            return
    
    parents = get_parents(child_id, conn)
    for parent in parents:
        update_material_total_cost(parent["id"], conn)
        update_parent_costs(parent["id"], conn)


def recalculate_all_costs():
    with get_conn() as conn:
        materials = get_all_materials()
        for mat in materials:
            update_material_total_cost(mat["id"], conn)


def explode_bom(material_id: int, production_qty: float, conn=None):
    if conn is None:
        with get_conn() as conn:
            return explode_bom(material_id, production_qty, conn)

    requirements = {}
    _explode_bom_recursive(material_id, production_qty, 1.0, requirements, conn)

    result = []
    for mat_id, data in requirements.items():
        material = get_material_by_id(mat_id)
        if material:
            per_unit_qty = data["per_unit_qty"]
            total_qty = data["total_qty"]
            result.append({
                "id": mat_id,
                "code": material["code"],
                "name": material["name"],
                "per_unit_qty": per_unit_qty,
                "total_qty": total_qty,
                "unit_price": float(material["unit_price"]),
                "total_price": float(material["unit_price"]) * total_qty,
            })
    result.sort(key=lambda x: x["code"])
    return result


def _explode_bom_recursive(material_id: int, production_qty: float, path_multiplier: float,
                            requirements: dict, conn):
    children = get_children(material_id, conn)

    if not children:
        if material_id not in requirements:
            requirements[material_id] = {"per_unit_qty": 0.0, "total_qty": 0.0}
        requirements[material_id]["per_unit_qty"] += path_multiplier
        requirements[material_id]["total_qty"] += path_multiplier * production_qty
        return

    for child in children:
        child_qty = float(child["quantity"])
        new_multiplier = path_multiplier * child_qty
        child_children = get_children(child["id"], conn)
        if not child_children:
            if child["id"] not in requirements:
                requirements[child["id"]] = {"per_unit_qty": 0.0, "total_qty": 0.0}
            requirements[child["id"]]["per_unit_qty"] += new_multiplier
            requirements[child["id"]]["total_qty"] += new_multiplier * production_qty
        else:
            _explode_bom_recursive(child["id"], production_qty, new_multiplier, requirements, conn)
