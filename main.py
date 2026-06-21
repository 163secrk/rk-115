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
    QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QBrush, QColor

import db


class MaterialDialog(QDialog):
    def __init__(self, parent=None, material=None):
        super().__init__(parent)
        self.material = material
        self.setWindowTitle("新建物料" if material is None else "编辑物料")
        self.resize(380, 220)

        layout = QFormLayout(self)

        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 10000000)
        self.price_spin.setDecimals(4)
        self.price_spin.setSingleStep(0.01)

        self.type_combo = QComboBox()
        self.type_combo.addItem("组件（可维护 BOM 子件）", db.TYPE_COMPONENT)
        self.type_combo.addItem("零件（基础物料，无子件）", db.TYPE_PART)

        layout.addRow("物料编码:", self.code_edit)
        layout.addRow("物料名称:", self.name_edit)
        layout.addRow("物料类型:", self.type_combo)
        layout.addRow("单价:", self.price_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if material is not None:
            self.code_edit.setText(material["code"])
            self.name_edit.setText(material["name"])
            self.price_spin.setValue(float(material["unit_price"]))
            mat_type = material.get("material_type", db.TYPE_COMPONENT)
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == mat_type:
                    self.type_combo.setCurrentIndex(i)
                    break

    def get_data(self):
        return {
            "code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "material_type": self.type_combo.currentData(),
            "unit_price": self.price_spin.value(),
        }


class BomRelationDialog(QDialog):
    def __init__(self, parent=None, default_parent_id=None, default_child_id=None):
        super().__init__(parent)
        self.setWindowTitle("建立子件关系")
        self.resize(420, 200)

        layout = QFormLayout(self)

        all_materials = db.get_all_materials()
        self.parent_map = {
            f"{m['code']} - {m['name']}": m["id"]
            for m in all_materials
            if m.get("material_type") == db.TYPE_COMPONENT
        }
        self.child_map = {
            f"{m['code']} - {m['name']}": m["id"] for m in all_materials
        }

        self.parent_combo = QComboBox()
        self.parent_combo.addItems(list(self.parent_map.keys()))
        self.child_combo = QComboBox()
        self.child_combo.addItems(list(self.child_map.keys()))

        if default_parent_id is not None:
            for label, mid in self.parent_map.items():
                if mid == default_parent_id:
                    self.parent_combo.setCurrentText(label)
                    break

        if default_child_id is not None:
            for label, mid in self.child_map.items():
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
            "parent_id": self.parent_map.get(parent_label),
            "child_id": self.child_map.get(child_label),
            "quantity": self.quantity_spin.value(),
        }


class ProductionQtyDialog(QDialog):
    def __init__(self, parent=None, material_info=""):
        super().__init__(parent)
        self.setWindowTitle("需求分析 - 输入生产数量")
        self.resize(400, 180)

        layout = QVBoxLayout(self)

        if material_info:
            info_label = QLabel(f"选中产品：{material_info}")
            info_label.setStyleSheet("color: #333; font-weight: bold; padding: 6px;")
            info_label.setWordWrap(True)
            layout.addWidget(info_label)

        form = QFormLayout()
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(1, 10000000)
        self.qty_spin.setDecimals(4)
        self.qty_spin.setValue(1.0)
        self.qty_spin.setSingleStep(1.0)
        form.addRow("生产数量:", self.qty_spin)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("开始计算")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_quantity(self):
        return self.qty_spin.value()


class RequirementListDialog(QDialog):
    def __init__(self, parent=None, product_info="", production_qty=0, requirements=None):
        super().__init__(parent)
        self.setWindowTitle("物料总需求清单")
        self.resize(900, 600)

        self.requirements = requirements or []
        self.production_qty = production_qty
        self.product_info = product_info

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header_layout = QVBoxLayout()
        title = QLabel("物料总需求清单")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignHCenter)
        header_layout.addWidget(title)

        info_text = f"产品：{product_info}    |    生产数量：{production_qty:.4f}"
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #444; padding: 4px;")
        info_label.setAlignment(Qt.AlignHCenter)
        header_layout.addWidget(info_label)

        layout.addLayout(header_layout)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "序号", "物料编码", "物料名称", "单支用量", "总需求数量", "单价", "总金额"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        summary_layout = QHBoxLayout()
        total_amount = sum(r["total_price"] for r in self.requirements)
        total_items = len(self.requirements)
        summary_label = QLabel(
            f"物料种类：{total_items} 种    |    物料总金额：¥{total_amount:.4f}"
        )
        summary_label.setStyleSheet(
            "font-weight: bold; color: #2b5797; padding: 6px;"
        )
        summary_layout.addWidget(summary_label)
        summary_layout.addStretch(1)

        self.btn_export = QPushButton("导出为文本")
        self.btn_export.clicked.connect(self.export_text)
        summary_layout.addWidget(self.btn_export)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText("关闭")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        summary_layout.addWidget(buttons)

        layout.addLayout(summary_layout)

        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(0)
        for idx, req in enumerate(self.requirements, 1):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(idx)))
            self.table.setItem(row, 1, QTableWidgetItem(req["code"]))
            self.table.setItem(row, 2, QTableWidgetItem(req["name"]))
            self.table.setItem(row, 3, QTableWidgetItem(f"{req['per_unit_qty']:.4f}"))
            item_qty = QTableWidgetItem(f"{req['total_qty']:.4f}")
            item_qty.setForeground(QBrush(QColor("#2b5797")))
            f = item_qty.font()
            f.setBold(True)
            item_qty.setFont(f)
            self.table.setItem(row, 4, item_qty)
            self.table.setItem(row, 5, QTableWidgetItem(f"{req['unit_price']:.4f}"))
            item_price = QTableWidgetItem(f"{req['total_price']:.4f}")
            item_price.setForeground(QBrush(QColor("#c00000")))
            self.table.setItem(row, 6, item_price)

            for col in range(7):
                item = self.table.item(row, col)
                if col == 4 or col == 6:
                    bg = QBrush(QColor(248, 250, 252))
                    item.setBackground(bg)

    def export_text(self):
        lines = []
        lines.append("=" * 70)
        lines.append("物料总需求清单")
        lines.append("=" * 70)
        lines.append(f"产品：{self.product_info}")
        lines.append(f"生产数量：{self.production_qty:.4f}")
        lines.append("-" * 70)
        lines.append(
            f"{'序号':<6}{'物料编码':<16}{'物料名称':<20}{'单支用量':>12}{'总需求':>14}"
        )
        lines.append("-" * 70)
        for idx, req in enumerate(self.requirements, 1):
            lines.append(
                f"{idx:<6}{req['code']:<16}{req['name']:<20}"
                f"{req['per_unit_qty']:>12.4f}{req['total_qty']:>14.4f}"
            )
        lines.append("-" * 70)
        total_amount = sum(r["total_price"] for r in self.requirements)
        lines.append(f"物料种类：{len(self.requirements)} 种")
        lines.append(f"物料总金额：¥{total_amount:.4f}")
        lines.append("=" * 70)

        dlg = QDialog(self)
        dlg.setWindowTitle("导出结果")
        dlg.resize(650, 500)
        dlg_layout = QVBoxLayout(dlg)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Consolas", 9))
        text_edit.setPlainText("\n".join(lines))
        dlg_layout.addWidget(text_edit)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(dlg.accept)
        dlg_layout.addWidget(btn_box)
        dlg.exec()


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

        self.material_table = QTableWidget(0, 5)
        self.material_table.setHorizontalHeaderLabels(["物料编码", "物料名称", "物料类型", "单价", "总成本"])
        self.material_table.verticalHeader().setVisible(False)
        self.material_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.material_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.material_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.material_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.material_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.material_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.material_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.material_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.material_table.itemSelectionChanged.connect(self._on_material_selected)

        group_layout.addWidget(self.material_table, 1)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("新建物料")
        self.btn_edit = QPushButton("编辑物料")
        self.btn_delete = QPushButton("删除物料")
        self.btn_requirement = QPushButton("需求分析")
        self.btn_requirement.setStyleSheet(
            "QPushButton { background-color: #2b5797; color: white; padding: 6px 12px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #1e3f70; }"
        )
        self.btn_add.clicked.connect(self.add_material)
        self.btn_edit.clicked.connect(self.edit_material)
        self.btn_delete.clicked.connect(self.delete_material)
        self.btn_requirement.clicked.connect(self.requirement_analysis)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_requirement)
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
        self.btn_refresh_tree.clicked.connect(self.refresh_all)
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
        selected_id = self._get_selected_material_id()
        materials = db.get_all_materials()
        self.material_table.blockSignals(True)
        self.material_table.setRowCount(0)
        select_row = -1
        for m in materials:
            row = self.material_table.rowCount()
            self.material_table.insertRow(row)
            self.material_table.setItem(row, 0, QTableWidgetItem(m["code"]))
            self.material_table.setItem(row, 1, QTableWidgetItem(m["name"]))

            is_component = m.get("material_type") == db.TYPE_COMPONENT
            type_label = "组件" if is_component else "零件"
            type_item = QTableWidgetItem(type_label)
            if is_component:
                type_item.setForeground(QBrush(QColor("#2b5797")))
                type_font = type_item.font()
                type_font.setBold(True)
                type_item.setFont(type_font)
            else:
                type_item.setForeground(QBrush(QColor("#888888")))
            self.material_table.setItem(row, 2, type_item)

            self.material_table.setItem(row, 3, QTableWidgetItem(f"{m['unit_price']:.4f}"))
            self.material_table.setItem(row, 4, QTableWidgetItem(f"{m['total_cost']:.4f}"))
            for col in range(5):
                item = self.material_table.item(row, col)
                item.setData(Qt.UserRole, m["id"])
            if m["id"] == selected_id:
                select_row = row
        if select_row >= 0:
            self.material_table.selectRow(select_row)
        self.material_table.blockSignals(False)

    def refresh_tree(self):
        self.bom_tree.clear()
        mat_id = self._get_selected_material_id()

        if mat_id is None:
            self._set_bom_panel_enabled(True)
            self.info_label.setText("提示：在左侧选中「组件」可查看/维护其 BOM 树")
            roots = db.get_root_materials()
            for root in roots:
                item = self._build_tree_item(root, 1.0, None)
                self.bom_tree.addTopLevelItem(item)
            self.bom_tree.expandAll()
            return

        material = db.get_material_by_id(mat_id)
        if material is None:
            self._set_bom_panel_enabled(False)
            self.info_label.setText("基础零件无需维护 BOM")
            return

        if material.get("material_type") == db.TYPE_PART:
            self._set_bom_panel_enabled(False)
            self.info_label.setText(
                f"「{material['name']}」为基础零件，无需维护 BOM"
            )
            return

        self._set_bom_panel_enabled(True)
        self.info_label.setText(
            f"当前组件：{material['code']} - {material['name']} 的 BOM 结构"
        )
        item = self._build_tree_item(material, 1.0, None)
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
        self.refresh_tree()

    def _on_bom_selected(self):
        pass

    def _set_bom_panel_enabled(self, enabled):
        self.bom_tree.setEnabled(enabled)
        self.btn_add_child.setEnabled(enabled)
        self.btn_remove_relation.setEnabled(enabled)
        self.btn_edit_qty.setEnabled(enabled)

    def add_material(self):
        dlg = MaterialDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data["code"] or not data["name"]:
                QMessageBox.warning(self, "提示", "物料编码和名称不能为空")
                return
            try:
                db.add_material(
                    data["code"], data["name"], data["unit_price"], data["material_type"]
                )
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
                db.update_material(
                    mat_id,
                    data["code"],
                    data["name"],
                    data["unit_price"],
                    data["material_type"],
                )
                self.refresh_all()
            except ValueError as e:
                QMessageBox.warning(self, "提示", str(e))
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
        components = [m for m in materials if m.get("material_type") == db.TYPE_COMPONENT]
        if not components:
            QMessageBox.information(self, "提示", "请先创建「组件」类型的物料作为父件")
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
                self.refresh_all()
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
                self.refresh_all()
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
                self.refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"修改用量失败：{e}")

    def requirement_analysis(self):
        mat_id = self._get_selected_material_id()
        if mat_id is None:
            QMessageBox.information(self, "提示", "请先在左侧物料列表中选择一个产品")
            return

        material = db.get_material_by_id(mat_id)
        if material is None:
            QMessageBox.warning(self, "提示", "未找到选中的物料信息")
            return

        material_info = f"{material['code']} - {material['name']}"
        children = db.get_children(mat_id)
        if not children:
            reply = QMessageBox.question(
                self, "确认",
                f"物料「{material_info}」目前没有定义子件（BOM结构为空）。\n"
                f"是否仍然继续进行需求分析？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        qty_dlg = ProductionQtyDialog(self, material_info)
        if qty_dlg.exec() != QDialog.Accepted:
            return

        production_qty = qty_dlg.get_quantity()
        if production_qty <= 0:
            QMessageBox.warning(self, "提示", "生产数量必须大于 0")
            return

        try:
            requirements = db.explode_bom(mat_id, production_qty)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"BOM 展开计算失败：{e}")
            return

        result_dlg = RequirementListDialog(
            self,
            product_info=material_info,
            production_qty=production_qty,
            requirements=requirements,
        )
        result_dlg.exec()


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
