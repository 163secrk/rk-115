import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QLabel,
    QHeaderView,
    QSplitter,
    QMessageBox,
    QComboBox,
    QGroupBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QBrush, QColor

import db


class MaterialDialog(QDialog):
    def __init__(self, parent=None, material=None):
        super().__init__(parent)
        self.material = material
        self.setWindowTitle("新建物料" if material is None else "编辑物料")
        self.resize(350, 180)

        layout = QFormLayout(self)

        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 10000000)
        self.price_spin.setDecimals(4)
        self.price_spin.setSingleStep(0.01)

        layout.addRow("物料编码:", self.code_edit)
        layout.addRow("物料名称:", self.name_edit)
        layout.addRow("单价:", self.price_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if material is not None:
            self.code_edit.setText(material["code"])
            self.name_edit.setText(material["name"])
            self.price_spin.setValue(float(material["unit_price"]))

    def get_data(self):
        return {
            "code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "unit_price": self.price_spin.value(),
        }


class BomRelationDialog(QDialog):
    def __init__(self, parent=None, default_parent_id=None, default_child_id=None):
        super().__init__(parent)
        self.setWindowTitle("建立子件关系")
        self.resize(420, 200)

        layout = QFormLayout(self)

        materials = db.get_all_materials()
        self.material_map = {f"{m['code']} - {m['name']}": m["id"] for m in materials}
        options = list(self.material_map.keys())

        self.parent_combo = QComboBox()
        self.parent_combo.addItems(options)
        self.child_combo = QComboBox()
        self.child_combo.addItems(options)

        if default_parent_id is not None:
            for label, mid in self.material_map.items():
                if mid == default_parent_id:
                    self.parent_combo.setCurrentText(label)
                    break

        if default_child_id is not None:
            for label, mid in self.material_map.items():
                if mid == default_child_id:
                    self.child_combo.setCurrentText(label)
                    break

        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.0001, 10000000)
        self.quantity_spin.setDecimals(4)
        self.quantity_spin.setValue(1.0)
        self.quantity_spin.setSingleStep(0.1)

        layout.addRow("父件物料:", self.parent_combo)
        layout.addRow("子件物料:", self.child_combo)
        layout.addRow("用量:", self.quantity_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        parent_label = self.parent_combo.currentText()
        child_label = self.child_combo.currentText()
        return {
            "parent_id": self.material_map.get(parent_label),
            "child_id": self.material_map.get(child_label),
            "quantity": self.quantity_spin.value(),
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("工业级 BOM 管理系统")
        self.resize(1200, 750)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        title = QLabel("工业级 BOM 管理系统")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignHCenter)
        main_layout.addWidget(title)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)

        splitter.addWidget(self._create_material_panel())
        splitter.addWidget(self._create_bom_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([400, 800])

        self.refresh_all()

    def _create_material_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        group = QGroupBox("物料列表")
        group_layout = QVBoxLayout(group)

        self.material_table = QTableWidget(0, 4)
        self.material_table.setHorizontalHeaderLabels(["物料编码", "物料名称", "单价", "总成本"])
        self.material_table.verticalHeader().setVisible(False)
        self.material_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.material_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.material_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.material_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.material_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.material_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.material_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.material_table.itemSelectionChanged.connect(self._on_material_selected)

        group_layout.addWidget(self.material_table, 1)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("新建物料")
        self.btn_edit = QPushButton("编辑物料")
        self.btn_delete = QPushButton("删除物料")
        self.btn_add.clicked.connect(self.add_material)
        self.btn_edit.clicked.connect(self.edit_material)
        self.btn_delete.clicked.connect(self.delete_material)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        group_layout.addLayout(btn_layout)

        layout.addWidget(group, 1)
        return panel

    def _create_bom_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        group = QGroupBox("产品 BOM 层级结构")
        group_layout = QVBoxLayout(group)

        self.bom_tree = QTreeWidget()
        self.bom_tree.setHeaderLabels(["物料编码", "物料名称", "用量", "单价", "子件成本", "总成本"])
        self.bom_tree.setColumnWidth(0, 140)
        self.bom_tree.setColumnWidth(1, 200)
        self.bom_tree.setColumnWidth(2, 80)
        self.bom_tree.setColumnWidth(3, 100)
        self.bom_tree.setColumnWidth(4, 120)
        self.bom_tree.setColumnWidth(5, 120)
        self.bom_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.bom_tree.itemSelectionChanged.connect(self._on_bom_selected)

        group_layout.addWidget(self.bom_tree, 1)

        btn_layout = QHBoxLayout()
        self.btn_add_child = QPushButton("设为子件...")
        self.btn_remove_relation = QPushButton("移除关系")
        self.btn_edit_qty = QPushButton("修改用量")
        self.btn_refresh_tree = QPushButton("刷新树")
        self.btn_add_child.clicked.connect(self.add_bom_relation)
        self.btn_remove_relation.clicked.connect(self.remove_bom_relation)
        self.btn_edit_qty.clicked.connect(self.edit_bom_quantity)
        self.btn_refresh_tree.clicked.connect(self.refresh_tree)
        btn_layout.addWidget(self.btn_add_child)
        btn_layout.addWidget(self.btn_edit_qty)
        btn_layout.addWidget(self.btn_remove_relation)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_refresh_tree)
        group_layout.addLayout(btn_layout)

        info_layout = QHBoxLayout()
        self.info_label = QLabel("提示：在左侧选中物料后可点击「设为子件」建立关系")
        self.info_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch(1)
        group_layout.addLayout(info_layout)

        layout.addWidget(group, 1)
        return panel

    def refresh_all(self):
        self.refresh_material_table()
        self.refresh_tree()

    def refresh_material_table(self):
        materials = db.get_all_materials()
        self.material_table.setRowCount(0)
        for m in materials:
            row = self.material_table.rowCount()
            self.material_table.insertRow(row)
            self.material_table.setItem(row, 0, QTableWidgetItem(m["code"]))
            self.material_table.setItem(row, 1, QTableWidgetItem(m["name"]))
            self.material_table.setItem(row, 2, QTableWidgetItem(f"{m['unit_price']:.4f}"))
            self.material_table.setItem(row, 3, QTableWidgetItem(f"{m['total_cost']:.4f}"))
            for col in range(4):
                item = self.material_table.item(row, col)
                item.setData(Qt.UserRole, m["id"])

    def refresh_tree(self):
        self.bom_tree.clear()
        roots = db.get_root_materials()
        for root in roots:
            item = self._build_tree_item(root, 1.0, None)
            self.bom_tree.addTopLevelItem(item)
        self.bom_tree.expandAll()

    def _build_tree_item(self, material, quantity, parent_id):
        price = float(material["unit_price"])
        total_cost = float(material["total_cost"])
        subtotal = total_cost * float(quantity)
        children = db.get_children(material["id"])
        
        children_cost = 0.0
        if children:
            for child in children:
                child_total = float(child["total_cost"])
                children_cost += child_total * float(child["quantity"])
        
        item = QTreeWidgetItem([
            material["code"],
            material["name"],
            f"{quantity:.4f}",
            f"{price:.4f}",
            f"{children_cost:.4f}",
            f"{subtotal:.4f}",
        ])
        item.setData(0, Qt.UserRole, material["id"])
        item.setData(1, Qt.UserRole, parent_id)
        item.setData(2, Qt.UserRole, quantity)
        
        if not children:
            for col in range(6):
                item.setBackground(col, QBrush(QColor(240, 248, 255)))
        else:
            font = item.font(5)
            font.setBold(True)
            item.setFont(5, font)
        
        for child in children:
            child_item = self._build_tree_item(child, child["quantity"], material["id"])
            item.addChild(child_item)
        return item

    def _get_selected_material_id(self):
        items = self.material_table.selectedItems()
        if items:
            return items[0].data(Qt.UserRole)
        return None

    def _get_selected_bom_ids(self):
        items = self.bom_tree.selectedItems()
        if not items:
            return None, None, None
        item = items[0]
        mat_id = item.data(0, Qt.UserRole)
        parent_id = item.data(1, Qt.UserRole)
        qty = item.data(2, Qt.UserRole)
        return mat_id, parent_id, qty

    def _on_material_selected(self):
        pass

    def _on_bom_selected(self):
        pass

    def add_material(self):
        dlg = MaterialDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data["code"] or not data["name"]:
                QMessageBox.warning(self, "提示", "物料编码和名称不能为空")
                return
            try:
                db.add_material(data["code"], data["name"], data["unit_price"])
                self.refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"新建物料失败：{e}")

    def edit_material(self):
        mat_id = self._get_selected_material_id()
        if mat_id is None:
            QMessageBox.information(self, "提示", "请先在左侧选择一个物料")
            return
        material = db.get_material_by_id(mat_id)
        dlg = MaterialDialog(self, material)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data["code"] or not data["name"]:
                QMessageBox.warning(self, "提示", "物料编码和名称不能为空")
                return
            try:
                db.update_material(mat_id, data["code"], data["name"], data["unit_price"])
                self.refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"编辑物料失败：{e}")

    def delete_material(self):
        mat_id = self._get_selected_material_id()
        if mat_id is None:
            QMessageBox.information(self, "提示", "请先在左侧选择一个物料")
            return
        material = db.get_material_by_id(mat_id)
        reply = QMessageBox.question(
            self, "确认",
            f"确定要删除物料「{material['code']} - {material['name']}」吗？相关 BOM 关系将一并删除。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                db.delete_material(mat_id)
                self.refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除物料失败：{e}")

    def add_bom_relation(self):
        materials = db.get_all_materials()
        if len(materials) < 2:
            QMessageBox.information(self, "提示", "至少需要两个物料才能建立子件关系")
            return

        default_parent = None
        default_child = None

        mat_id = self._get_selected_material_id()
        bom_id, bom_parent, _ = self._get_selected_bom_ids()

        if mat_id is not None and bom_id is not None:
            default_parent = bom_id
            default_child = mat_id
        elif mat_id is not None:
            default_child = mat_id
        elif bom_id is not None:
            default_parent = bom_id

        dlg = BomRelationDialog(self, default_parent, default_child)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if data["parent_id"] is None or data["child_id"] is None:
                QMessageBox.warning(self, "提示", "请选择有效的父件和子件物料")
                return
            try:
                db.add_bom_relation(data["parent_id"], data["child_id"], data["quantity"])
                self.refresh_tree()
            except ValueError as e:
                QMessageBox.warning(self, "提示", str(e))
            except Exception as e:
                QMessageBox.critical(self, "错误", f"建立关系失败：{e}")

    def remove_bom_relation(self):
        mat_id, parent_id, _ = self._get_selected_bom_ids()
        if mat_id is None:
            QMessageBox.information(self, "提示", "请先在右侧树中选择一个节点")
            return
        if parent_id is None:
            QMessageBox.information(self, "提示", "根节点没有父件关系，请删除物料本身")
            return
        mat = db.get_material_by_id(mat_id)
        reply = QMessageBox.question(
            self, "确认",
            f"确定要移除该子件关系吗？（物料本身不会被删除）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                db.remove_bom_relation(parent_id, mat_id)
                self.refresh_tree()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"移除关系失败：{e}")

    def edit_bom_quantity(self):
        mat_id, parent_id, cur_qty = self._get_selected_bom_ids()
        if mat_id is None:
            QMessageBox.information(self, "提示", "请先在右侧树中选择一个节点")
            return
        if parent_id is None:
            QMessageBox.information(self, "提示", "根节点没有用量可编辑")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("修改用量")
        dlg.resize(300, 120)
        layout = QFormLayout(dlg)
        spin = QDoubleSpinBox()
        spin.setRange(0.0001, 10000000)
        spin.setDecimals(4)
        spin.setValue(float(cur_qty) if cur_qty else 1.0)
        spin.setSingleStep(0.1)
        mat = db.get_material_by_id(mat_id)
        layout.addRow(f"用量（{mat['code']} - {mat['name']}）:", spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addRow(buttons)

        if dlg.exec() == QDialog.Accepted:
            try:
                db.update_bom_quantity(parent_id, mat_id, spin.value())
                self.refresh_tree()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"修改用量失败：{e}")


def main():
    db.init_db()
    db.recalculate_all_costs()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
