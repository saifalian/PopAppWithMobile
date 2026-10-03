"""
Interactive node-based flowchart canvas using QGraphicsView.
Handles drawing boxes, connecting lines, and dragging nodes.
"""
import uuid
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QPainterPath, QPen, QBrush, QColor, QFont
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsPathItem,
    QGraphicsTextItem, QGraphicsRectItem, QFrame, QHBoxLayout, QPushButton,
    QLabel, QVBoxLayout
)

from backend.macro.node_types import NODE_REGISTRY

class ConnectionPort(QGraphicsRectItem):
    """
    A small interactive circle on a node that acts as a connection point.
    """
    def __init__(self, node, name: str, parent=None):
        super().__init__(-6, -6, 12, 12, parent)
        self.node = node
        self.name = name # "top", "bottom", "left", "right"
        self.setBrush(QBrush(QColor("#94a3b8")))
        self.setPen(QPen(Qt.GlobalColor.transparent))
        self.setAcceptHoverEvents(True)
        self.setZValue(10)

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor("#facc15"))) # Yellow on hover
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(QColor("#94a3b8")))
        super().hoverLeaveEvent(event)


class MacroNodeItem(QGraphicsRectItem):
    """
    Visual representation of a macro node on the canvas.
    """
    def __init__(self, n_type: str, n_id: str, label: str, config: dict, x: float = 0, y: float = 0):
        super().__init__(-75, -25, 150, 50) # x, y, w, h
        
        self.n_type = n_type
        self.n_id = n_id
        self.label_text = label
        self.config = config

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        self.setPos(x, y)
        self.setAcceptHoverEvents(True)

        self.cls = NODE_REGISTRY.get(self.n_type)
        self.color_hex = getattr(self.cls, "NODE_COLOR", "#475569")
        self.icon_str = getattr(self.cls, "NODE_ICON", "⚙")

        base_color = QColor(self.color_hex)
        border_color = base_color.darker(150)
        
        self.setBrush(QBrush(base_color))
        self.setPen(QPen(border_color, 2))
        
        # Add label
        self.text_item = QGraphicsTextItem(f"{self.icon_str} {self.label_text}", self)
        self.text_item.setDefaultTextColor(Qt.GlobalColor.white)
        f = QFont("Segoe UI", 9, QFont.Weight.Bold)
        self.text_item.setFont(f)
        
        # Center text horizontally
        br = self.text_item.boundingRect()
        self.text_item.setPos(-br.width()/2, -br.height()/2)

        # Ports
        self.ports = {
            "top":    ConnectionPort(self, "top", self),
            "bottom": ConnectionPort(self, "bottom", self),
            "left":   ConnectionPort(self, "left", self),
            "right":  ConnectionPort(self, "right", self)
        }
        self.ports["top"].setPos(0, -25)
        self.ports["bottom"].setPos(0, 25)
        self.ports["left"].setPos(-75, 0)
        self.ports["right"].setPos(75, 0)

    def paint(self, painter, option, widget):
        if self.isSelected():
            self.setPen(QPen(QColor("#facc15"), 3))
        else:
            base_color = QColor(self.color_hex)
            self.setPen(QPen(base_color.darker(150), 2))
        super().paint(painter, option, widget)

    def update_data(self, data: dict):
        self.label_text = data.get("label", self.n_type)
        self.config = data.get("config", self.config)
        self.text_item.setPlainText(f"{self.icon_str} {self.label_text}")
        br = self.text_item.boundingRect()
        self.text_item.setPos(-br.width()/2, -br.height()/2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self.scene():
                self.scene().update_connections(self)
        return super().itemChange(change, value)


class ConnectionLine(QGraphicsPathItem):
    """
    A bezier curve connecting two ports.
    """
    def __init__(self, src_p: ConnectionPort, dst_p: ConnectionPort):
        super().__init__()
        self.src_p = src_p
        self.dst_p = dst_p
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setPen(QPen(QColor("#cbd5e1"), 2, Qt.PenStyle.SolidLine))
        self.update_path()

    def paint(self, painter, option, widget):
        if self.isSelected():
            self.setPen(QPen(QColor("#facc15"), 3, Qt.PenStyle.SolidLine))
        else:
            self.setPen(QPen(QColor("#cbd5e1"), 2, Qt.PenStyle.SolidLine))
        super().paint(painter, option, widget)

    def shape(self) -> QPainterPath:
        # Create a wider path for easier clicking
        from PyQt6.QtGui import QPainterPathStroker
        stroker = QPainterPathStroker()
        stroker.setWidth(10)
        return stroker.createStroke(self.path())

    def update_path(self):
        p1 = self.src_p.scenePos()
        p2 = self.dst_p.scenePos()
        
        # Calculate distance-dependent offset for control points
        dist = (p2 - p1).manhattanLength()
        offset = max(60, dist * 0.4)
        
        # Directions for each port name
        dirs = {
            "top": QPointF(0, -offset),
            "bottom": QPointF(0, offset),
            "left": QPointF(-offset, 0),
            "right": QPointF(offset, 0)
        }
        
        # Pull control points out from the source and destination ports
        c1 = p1 + dirs.get(self.src_p.name, QPointF(0, 0))
        c2 = p2 + dirs.get(self.dst_p.name, QPointF(0, 0))
        
        path = QPainterPath(p1)
        path.cubicTo(c1, c2, p2)
        self.setPath(path)


class NodeScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.nodes = [] # List of MacroNodeItem
        self.connections = []

    def add_macro_node(self, n_type: str, n_id: str=None, label: str=None, config: dict=None, x: float=0, y: float=0) -> MacroNodeItem:
        if not n_id: 
            n_id = f"node_{uuid.uuid4().hex[:8]}"
        if not label:
            label = n_type.replace("_", " ").title()
        if not config:
            config = {}

        item = MacroNodeItem(n_type, n_id, label, config, x, y)
        self.addItem(item)
        self.nodes.append(item)
        return item

    def update_connections(self, node: MacroNodeItem):
        for conn in self.connections:
            if conn.src_p.node == node or conn.dst_p.node == node:
                conn.update_path()

class ZoomOverlay(QFrame):
    """
    Floating zoom controls for the NodeCanvas.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: rgba(30, 41, 59, 220);
                border: 1px solid #475569;
                border-radius: 8px;
            }
            QPushButton {
                background: transparent;
                color: #cbd5e1;
                font-size: 16px;
                font-weight: bold;
                border: none;
                padding: 4px;
                min-width: 24px;
            }
            QPushButton:hover {
                color: #f8fafc;
                background: rgba(255, 255, 255, 20);
            }
            QLabel {
                color: #94a3b8;
                font-size: 11px;
                font-weight: 600;
                padding: 0 4px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)
        
        self.btn_reset = QPushButton("↺")
        self.btn_reset.setToolTip("Reset View (100%)")
        
        self.btn_minus = QPushButton("-")
        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setFixedWidth(40)
        self.lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_plus = QPushButton("+")
        
        layout.addWidget(self.btn_reset)
        layout.addWidget(self._v_sep())
        layout.addWidget(self.btn_minus)
        layout.addWidget(self.lbl_zoom)
        layout.addWidget(self.btn_plus)

    def _v_sep(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background: #475569;")
        sep.setFixedWidth(1)
        sep.setFixedHeight(16)
        return sep

    def set_zoom(self, percent: int):
        self.lbl_zoom.setText(f"{percent}%")


class NodeCanvas(QGraphicsView):
    node_selected = pyqtSignal(str, dict)
    connection_selected = pyqtSignal(object) # Emits ConnectionLine item

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = NodeScene(self)
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
        # Zoom Controls
        self.zoom_overlay = ZoomOverlay(self)
        self.zoom_overlay.btn_plus.clicked.connect(self.zoom_in)
        self.zoom_overlay.btn_minus.clicked.connect(self.zoom_out)
        self.zoom_overlay.btn_reset.clicked.connect(self.reset_view)
        
        self.update_zoom_label()

        # Drag-to-connect state
        self.dragging_port = None
        self.temp_line = QGraphicsPathItem()
        self.temp_line.setPen(QPen(QColor("#facc15"), 2, Qt.PenStyle.DashLine))
        self.temp_line.setZValue(100)
        self.scene.addItem(self.temp_line)
        self.temp_line.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep overlay in bottom-right
        margin = 20
        self.zoom_overlay.move(
            self.width() - self.zoom_overlay.width() - margin,
            self.height() - self.zoom_overlay.height() - margin
        )

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)
        self.update_zoom_label()

    def zoom_in(self):
        self.scale(1.25, 1.25)
        self.update_zoom_label()

    def zoom_out(self):
        self.scale(0.8, 0.8)
        self.update_zoom_label()

    def reset_view(self):
        self.resetTransform()
        self.update_zoom_label()
        # Center on content if any, else (0,0)
        items = self.scene.items()
        if items:
            rect = self.scene.itemsBoundingRect()
            self.centerOn(rect.center())
        else:
            self.centerOn(0, 0)

    def update_zoom_label(self):
        # transform().m11() gives the current scale factor
        scale = self.transform().m11()
        self.zoom_overlay.set_zoom(int(scale * 100))

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        
        # 1. Handle Connection Reconnection (dragging an endpoint)
        if isinstance(item, ConnectionLine):
            p = self.mapToScene(event.pos())
            # Check if close to src or dst
            if (p - item.src_p.scenePos()).manhattanLength() < 25:
                # Detach SRC, keep DST
                self.dragging_port = item.dst_p
                self.dragging_is_src = True # We are dragging the NEW source
                self.dragging_conn = item
                self.temp_line.show()
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                return
            elif (p - item.dst_p.scenePos()).manhattanLength() < 25:
                # Detach DST, keep SRC
                self.dragging_port = item.src_p
                self.dragging_is_src = False # We are dragging the NEW destination
                self.dragging_conn = item
                self.temp_line.show()
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                return

        # 2. Start new connection
        if isinstance(item, ConnectionPort):
            self.dragging_port = item
            self.dragging_is_src = False # If we drag from a port, it's the SRC, we drag the DST end
            self.dragging_conn = None
            self.temp_line.show()
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging_port:
            p1 = self.dragging_port.scenePos()
            p2 = self.mapToScene(event.pos())
            path = QPainterPath(p1)
            path.lineTo(p2)
            self.temp_line.setPath(path)
            self.scene.update()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging_port:
            self.temp_line.hide()
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            item = self.itemAt(event.pos())
            
            # If we released on a valid port
            if isinstance(item, ConnectionPort) and item.node != self.dragging_port.node:
                if self.dragging_conn:
                    # UPDATE existing connection
                    if self.dragging_is_src:
                        self.dragging_conn.src_p = item
                    else:
                        self.dragging_conn.dst_p = item
                    self.dragging_conn.update_path()
                else:
                    # CREATE new connection (dragging_port was SRC, item is DST)
                    exists = any(c.src_p == self.dragging_port and c.dst_p == item for c in self.scene.connections)
                    if not exists:
                        conn = ConnectionLine(self.dragging_port, item)
                        self.scene.addItem(conn)
                        self.scene.connections.append(conn)
            
            self.dragging_port = None
            self.dragging_conn = None
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key.Key_Delete, Qt.Key.Key_Backspace]:
            for item in self.scene.selectedItems():
                if isinstance(item, ConnectionLine):
                    self.scene.removeItem(item)
                    if item in self.scene.connections:
                        self.scene.connections.remove(item)
                elif isinstance(item, MacroNodeItem):
                    # Use existing delete logic if node is selected
                    self.delete_node(item.n_id)
            return

        super().keyPressEvent(event)

    def on_selection_changed(self):
        sel = self.scene.selectedItems()
        if not sel:
            return

        if isinstance(sel[0], MacroNodeItem):
            item = sel[0]
            data = {
                "id": item.n_id,
                "type": item.n_type,
                "label": item.label_text,
                "config": item.config
            }
            self.node_selected.emit(item.n_id, data)
        elif isinstance(sel[0], ConnectionLine):
            self.connection_selected.emit(sel[0])

    def add_node_type(self, n_type: str):
        # Calculate a default drop position, slightly below the last node
        y_offset = len(self.scene.nodes) * 100
        self.scene.add_macro_node(n_type, x=0, y=y_offset)

    def update_node_data(self, node_id: str, data: dict):
        for item in self.scene.nodes:
            if item.n_id == node_id:
                item.update_data(data)
                break

    def delete_node(self, node_id: str):
        for i, item in enumerate(self.scene.nodes):
            if item.n_id == node_id:
                # Remove connections
                to_remove = [c for c in self.scene.connections if c.src_p.node == item or c.dst_p.node == item]
                for c in to_remove:
                    self.scene.removeItem(c)
                    self.scene.connections.remove(c)
                
                # Remove node
                self.scene.removeItem(item)
                self.scene.nodes.remove(item)
                break

    def clear(self):
        self.scene.clear()
        self.scene.nodes.clear()
        self.scene.connections.clear()
        # Re-add temp line after scene clear
        self.temp_line = QGraphicsPathItem()
        self.temp_line.setPen(QPen(QColor("#facc15"), 2, Qt.PenStyle.DashLine))
        self.temp_line.setZValue(100)
        self.scene.addItem(self.temp_line)
        self.temp_line.hide()

    def get_pipeline_json(self) -> dict:
        nodes = [ {
            "id": n.n_id,
            "type": n.n_type,
            "label": n.label_text,
            "config": n.config,
            "x": n.x(),
            "y": n.y()
        } for n in self.scene.nodes ]
        
        conns = [ {
            "src": c.src_p.node.n_id,
            "src_port": c.src_p.name,
            "dst": c.dst_p.node.n_id,
            "dst_port": c.dst_p.name
        } for c in self.scene.connections ]
        
        return {"nodes": nodes, "connections": conns}

    def load_pipeline_json(self, payload: dict):
        self.clear()
        # Support both old format (list of nodes) and new format (dict with nodes/connections)
        if isinstance(payload, list):
            nodes_data = payload
            conns_data = []
        else:
            nodes_data = payload.get("nodes", [])
            conns_data = payload.get("connections", [])
        
        # Build nodes
        node_map = {}
        for n_dict in nodes_data:
            item = self.scene.add_macro_node(
                n_type=n_dict.get("type", "log_message"),
                n_id=n_dict.get("id"),
                label=n_dict.get("label"),
                config=n_dict.get("config", {}),
                x=n_dict.get("x", 0), 
                y=n_dict.get("y", 0)
            )
            item.setPos(n_dict.get("x", 0), n_dict.get("y", 0))
            node_map[item.n_id] = item
            
        # Build connections
        for c_dict in conns_data:
            src = node_map.get(c_dict.get("src"))
            dst = node_map.get(c_dict.get("dst"))
            if src and dst:
                src_port = src.ports.get(c_dict.get("src_port", "bottom"))
                dst_port = dst.ports.get(c_dict.get("dst_port", "top"))
                if src_port and dst_port:
                    conn = ConnectionLine(src_port, dst_port)
                    self.scene.addItem(conn)
                    self.scene.connections.append(conn)
