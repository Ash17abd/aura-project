"""AURA 3D Learning Lab.

Turns study material and engineering concepts into interactive 3D lessons.
Features rich procedural geometry, step-by-step animations, component picking,
voice Q&A, mouse drag/zoom controls, and optional MediaPipe webcam hand gestures.
"""
from __future__ import annotations

import math
import re
import threading
import time
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QPixmap, QImage, QColor
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget, QProgressBar,
    QTabWidget, QDialog, QLineEdit, QInputDialog, QFrame,
)

from actions.component_selector import ComponentSelector
from actions.animation_player import AnimationPlayer
from actions.voice_parser import VoiceCommandParser

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
except Exception:  # pragma: no cover
    FigureCanvas = None
    Figure = None
    Poly3DCollection = None

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

try:
    import mediapipe as mp
except Exception:  # pragma: no cover
    mp = None


# ---------- reading extraction ----------

def _read_material(path: str | None) -> str:
    if not path:
        return "No reading file was supplied. Build a useful general science/engineering model."
    p = Path(path)
    if not p.exists():
        return f"The reading file {p.name} could not be found."
    ext = p.suffix.lower()
    try:
        if ext in {".txt", ".md", ".py", ".csv", ".json", ".html"}:
            return p.read_text(encoding="utf-8", errors="ignore")[:50000]
        if ext == ".pdf":
            from pypdf import PdfReader
            return "\n".join((page.extract_text() or "") for page in PdfReader(str(p)).pages)[:50000]
        if ext == ".docx":
            from docx import Document
            return "\n".join(x.text for x in Document(str(p)).paragraphs)[:50000]
        if ext == ".pptx":
            from pptx import Presentation
            out = []
            for slide in Presentation(str(p)).slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        out.append(shape.text)
            return "\n".join(out)[:50000]
        if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            return f"Uploaded image reading: {p.name}. Build an educational 3D model visualizing {p.stem.replace('_', ' ').replace('-', ' ')}."
    except Exception as e:
        return f"Could not read {p.name}: {e}"
    return f"File {p.name} is not a supported reading format."


def _topics(text: str) -> list[tuple[str, str]]:
    """Return ordered diagram topics from the reading, with sensible fallbacks."""
    low = text.lower()
    candidates: list[tuple[str, str, int]] = []
    patterns = [
        ("DNA Double Helix", ["dna", "double helix", "nucleotide", "genetic"]),
        ("Human Cell", ["cell", "cytoplasm", "nucleus", "mitochondria"]),
        ("Solar System", ["solar system", "planet", "orbit", "sun"]),
        ("Electric Motor", ["motor", "rotor", "stator", "electromagnetic"]),
        ("Internal Combustion Engine", ["engine", "piston", "cylinder", "combustion"]),
        ("Atom", ["atom", "electron", "proton", "neutron", "nucleus"]),
        ("Gear Train", ["gear", "gear train", "torque", "spur gear"]),
        ("Bridge / Beam", ["beam", "bridge", "stress", "strain", "truss"]),
        ("Water Cycle", ["water cycle", "evaporation", "condensation", "precipitation"]),
        ("Heart", ["heart", "atrium", "ventricle", "blood flow"]),
        ("Generic 3D Concept", []),
    ]
    for title, keys in patterns:
        score = sum(low.count(k) for k in keys)
        if score:
            candidates.append((title, "", score))
    candidates.sort(key=lambda x: x[2], reverse=True)
    result = [(t, _explain_topic(t, text)) for t, _, _ in candidates[:5]]
    if not result:
        # Pull likely headings as extra diagram names.
        headings = re.findall(r"(?:^|\n)\s*(?:#+\s*)?([A-Z][A-Za-z0-9 /&-]{3,60})\s*$", text)
        for h in headings[:4]:
            result.append((h.strip(), _explain_topic(h.strip(), text)))
    if not result:
        result = [("Generic 3D Concept", _explain_topic("Generic 3D Concept", text))]
    return result


def _explain_topic(topic: str, reading: str) -> str:
    low = reading.lower()
    snippets = []
    for sentence in re.split(r"(?<=[.!?])\s+", reading.replace("\n", " ")):
        if any(k in sentence.lower() for k in topic.lower().split()[:3]) and len(sentence) > 25:
            snippets.append(sentence.strip())
        if len(snippets) >= 2:
            break
    base = " ".join(snippets)
    explanations = {
        "DNA Double Helix": "DNA stores genetic information. The two strands form a double helix; paired bases connect the strands while the sugar-phosphate backbones form the outside rails.",
        "Human Cell": "The nucleus stores genetic material, the cytoplasm surrounds the organelles, and mitochondria are major sites of cellular energy production.",
        "Solar System": "The Sun is at the centre of the system and planets follow orbits around it. The model emphasizes orbital relationships.",
        "Electric Motor": "Current in the coil interacts with a magnetic field to produce torque. The rotor turns while the stator provides the stationary magnetic structure.",
        "Internal Combustion Engine": "The piston moves inside the cylinder and converts expanding combustion gases into mechanical motion through the connecting rod and crankshaft.",
        "Atom": "An atom has a dense nucleus containing protons and neutrons, surrounded by an electron cloud with quantized probability shells.",
        "Gear Train": "Meshing gears transfer rotation and torque. Changing gear size modifies the speed and torque relationship between input and output shafts.",
        "Bridge / Beam": "A beam or truss carries loads through tension and compression, distributing external weights to foundation abutments.",
        "Water Cycle": "Water evaporates, condenses into clouds and returns as precipitation, continuously moving water between the surface and atmosphere.",
        "Heart": "The heart pumps blood through 4 chambers. The atria receive incoming blood while the muscular ventricles drive circulation.",
    }
    answer = explanations.get(topic, "This 3D model visualizes key spatial concepts and component interactions from the subject.")
    return answer + (f"\n\nReading connection: {base[:500]}" if base else "")


# ---------- 3D renderer ----------

class ThreeDCanvas(FigureCanvas):
    def __init__(self, lab):
        # Deep space tech navy matching reference image aura_app.png
        self.fig = Figure(figsize=(8, 6), facecolor="#060c14")
        super().__init__(self.fig)
        self.lab = lab
        self.ax = self.fig.add_subplot(111, projection="3d", facecolor="#060c14")
        self.setMinimumSize(650, 520)

        # Mouse interaction tracking
        self._mouse_pressed = False
        self._mouse_button = None
        self._last_mouse_x = None
        self._last_mouse_y = None
        self._press_start_pos = None

        self.mpl_connect("button_press_event", self._on_mouse_press)
        self.mpl_connect("button_release_event", self._on_mouse_release)
        self.mpl_connect("motion_notify_event", self._on_mouse_move)
        self.mpl_connect("scroll_event", self._on_mouse_scroll)

        self.draw_scene()

    def _style(self):
        self.ax.set_axis_off()
        self.ax.set_facecolor("#060c14")
        self.fig.subplots_adjust(0, 0, 1, 1)

    def _on_mouse_press(self, event):
        if event.inaxes != self.ax:
            return
        self._mouse_pressed = True
        self._mouse_button = event.button
        self._last_mouse_x = event.x
        self._last_mouse_y = event.y
        self._press_start_pos = (event.x, event.y)

        # Double click to reset view
        if getattr(event, "dblclick", False):
            self.lab.reset()

    def _on_mouse_release(self, event):
        if not self._mouse_pressed:
            return

        # Check if this was a click (not a drag)
        if self._press_start_pos and event.x is not None and event.y is not None:
            dx = abs(event.x - self._press_start_pos[0])
            dy = abs(event.y - self._press_start_pos[1])
            if dx < 6 and dy < 6 and event.button == 1:
                # Click selection
                nearest_id = self.lab.selector.find_nearest_component_screen(event.x, event.y, self.ax)
                if nearest_id:
                    self.lab.select_component(nearest_id)

        self._mouse_pressed = False
        self._mouse_button = None
        self._last_mouse_x = None
        self._last_mouse_y = None
        self._press_start_pos = None

    def _on_mouse_move(self, event):
        if not self._mouse_pressed or event.x is None or event.y is None:
            return
        if self._last_mouse_x is None or self._last_mouse_y is None:
            self._last_mouse_x = event.x
            self._last_mouse_y = event.y
            return

        dx = event.x - self._last_mouse_x
        dy = event.y - self._last_mouse_y
        self._last_mouse_x = event.x
        self._last_mouse_y = event.y

        if self._mouse_button == 1:
            # Left click drag: rotate
            self.lab.azim = (self.lab.azim + dx * 0.6) % 360
            self.lab.elev = max(-85, min(85, self.lab.elev - dy * 0.6))
            self.draw_scene()
        elif self._mouse_button in (2, 3):
            # Right or middle click drag: pan/tilt
            self.lab.elev = max(-85, min(85, self.lab.elev - dy * 0.4))
            self.draw_scene()

    def _on_mouse_scroll(self, event):
        if event.inaxes != self.ax:
            return
        step = getattr(event, "step", 1) if getattr(event, "step", 0) != 0 else (1 if event.button == "up" else -1)
        self.lab.zoom = max(2.5, min(18.0, self.lab.zoom - step * 0.6))
        self.draw_scene()

    def _sphere(self, x, y, z, r, color="#00d4ff", alpha=0.9, resolution=24):
        """Render a realistic, shaded 3D sphere."""
        if isinstance(r, (list, tuple, np.ndarray)):
            r = float(r[0]) if len(r) > 0 else 0.5
        r = max(0.01, float(r))
        u = np.linspace(0, 2 * np.pi, resolution)
        v = np.linspace(0, np.pi, resolution // 2)
        xs = x + r * np.outer(np.cos(u), np.sin(v))
        ys = y + r * np.outer(np.sin(u), np.sin(v))
        zs = z + r * np.outer(np.ones_like(u), np.cos(v))
        self.ax.plot_surface(xs, ys, zs, color=color, alpha=alpha, linewidth=0, shade=True)

    def _cylinder_between(self, p1, p2, radius, color="#00d4ff", alpha=0.85, caps=True):
        """
        Watertight 3D solid cylinder between two arbitrary 3D points p1 and p2.
        Enables true structural engineering beams, struts, bracing, pipes, and shafts.
        """
        p1 = np.asarray(p1, dtype=float)
        p2 = np.asarray(p2, dtype=float)
        v = p2 - p1
        length = float(np.linalg.norm(v))
        if length < 1e-4:
            self._sphere(p1[0], p1[1], p1[2], radius, color, alpha)
            return

        if isinstance(radius, (list, tuple, np.ndarray)):
            radius = float(radius[0]) if len(radius) > 0 else 0.15
        radius = max(0.008, float(radius))

        v_unit = v / length
        # Construct orthonormal basis
        ref = np.array([0.0, 0.0, 1.0]) if abs(v_unit[2]) < 0.88 else np.array([1.0, 0.0, 0.0])
        u1 = np.cross(v_unit, ref)
        u1 /= np.linalg.norm(u1)
        u2 = np.cross(v_unit, u1)

        theta = np.linspace(0, 2 * np.pi, 24)
        t_vals = np.linspace(0, 1, 2)
        THETA, T = np.meshgrid(theta, t_vals)

        cx = np.cos(THETA) * radius
        cy = np.sin(THETA) * radius

        X = p1[0] + T * v[0] + cx * u1[0] + cy * u2[0]
        Y = p1[1] + T * v[1] + cx * u1[1] + cy * u2[1]
        Z = p1[2] + T * v[2] + cx * u1[2] + cy * u2[2]

        self.ax.plot_surface(X, Y, Z, color=color, alpha=alpha, linewidth=0, shade=True)

        if caps and Poly3DCollection is not None:
            disk_theta = np.linspace(0, 2 * np.pi, 20, endpoint=False)
            bot_pts = [p1 + radius * np.cos(t) * u1 + radius * np.sin(t) * u2 for t in disk_theta]
            top_pts = [p2 + radius * np.cos(t) * u1 + radius * np.sin(t) * u2 for t in disk_theta]
            self.ax.add_collection3d(Poly3DCollection([bot_pts, top_pts], facecolors=color, edgecolors="none", alpha=alpha))

    def _cylinder(self, x, y, z, radius, height, color="#00d4ff", alpha=0.85, vertical=True, axis="z"):
        """Render a solid cylinder with proper axis orientation and end caps."""
        if isinstance(radius, (list, tuple, np.ndarray)):
            radius = float(radius[0]) if len(radius) > 0 else 0.4
        radius = max(0.01, float(radius))
        if isinstance(height, (list, tuple, np.ndarray)):
            height = float(height[1]) if len(height) > 1 else float(height[0])
        height = max(0.02, float(height))

        h2 = height / 2.0
        axis_lower = str(axis).lower()
        if axis_lower == "x":
            p1 = [x - h2, y, z]
            p2 = [x + h2, y, z]
        elif axis_lower == "y":
            p1 = [x, y - h2, z]
            p2 = [x, y + h2, z]
        else:
            p1 = [x, y, z - h2] if not vertical else [x, y, z]
            p2 = [x, y, z + h2] if not vertical else [x, y, z + height]

        self._cylinder_between(p1, p2, radius, color=color, alpha=alpha, caps=True)

    def _line(self, p1, p2, color="#00d4ff", width=2):
        self.ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], color=color, linewidth=width, alpha=0.9)

    def _cone(self, x, y, z, radius, height, color="#ff6b00", alpha=0.85, axis="z"):
        """Render a solid tapering conical nozzle/valve with base cap."""
        if isinstance(radius, (list, tuple, np.ndarray)):
            radius = float(radius[0]) if len(radius) > 0 else 0.5
        radius = max(0.01, float(radius))
        if isinstance(height, (list, tuple, np.ndarray)):
            height = float(height[1]) if len(height) > 1 else float(height[0])
        height = max(0.02, float(height))

        a = np.linspace(0, 2 * np.pi, 24)
        rs = np.linspace(radius, 0.001, 2)[:, np.newaxis]
        aa = a[np.newaxis, :]
        xx = x + rs * np.cos(aa)
        yy = y + rs * np.sin(aa)
        zz2 = np.array([[z] * 24, [z + height] * 24])
        self.ax.plot_surface(xx, yy, zz2, color=color, alpha=alpha, linewidth=0, shade=True)

        if Poly3DCollection is not None:
            base_pts = [[x + radius * np.cos(t), y + radius * np.sin(t), z] for t in np.linspace(0, 2 * np.pi, 20, endpoint=False)]
            self.ax.add_collection3d(Poly3DCollection([base_pts], facecolors=color, edgecolors="none", alpha=alpha))

    def _box(self, x, y, z, width, height, depth, color="#5c6b73", alpha=0.85):
        """Render an engineering solid box with clean subtle bevel edge contrast."""
        if isinstance(width, (list, tuple, np.ndarray)):
            w = float(width[0]) if len(width) > 0 else 1.0
            h = float(width[1]) if len(width) > 1 else w
            d = float(width[2]) if len(width) > 2 else w
            width, height, depth = w, h, d

        w2, h2, d2 = width / 2.0, height / 2.0, depth / 2.0
        vertices = np.array([
            [x - w2, y - h2, z - d2],
            [x + w2, y - h2, z - d2],
            [x + w2, y + h2, z - d2],
            [x - w2, y + h2, z - d2],
            [x - w2, y - h2, z + d2],
            [x + w2, y - h2, z + d2],
            [x + w2, y + h2, z + d2],
            [x - w2, y + h2, z + d2],
        ])
        faces = [
            [vertices[0], vertices[1], vertices[2], vertices[3]],
            [vertices[4], vertices[5], vertices[6], vertices[7]],
            [vertices[0], vertices[1], vertices[5], vertices[4]],
            [vertices[2], vertices[3], vertices[7], vertices[6]],
            [vertices[0], vertices[3], vertices[7], vertices[4]],
            [vertices[1], vertices[2], vertices[6], vertices[5]],
        ]
        # Clean subtle engineering edge instead of harsh white
        edge_c = "#041421" if alpha > 0.5 else color
        if Poly3DCollection is not None:
            poly = Poly3DCollection(faces, facecolors=color, linewidths=0.7, edgecolors=edge_c, alpha=alpha)
            self.ax.add_collection3d(poly)
        else:
            for face in faces:
                xs = [v[0] for v in face] + [face[0][0]]
                ys = [v[1] for v in face] + [face[0][1]]
                zs = [v[2] for v in face] + [face[0][2]]
                self.ax.plot(xs, ys, zs, color=color, alpha=alpha, linewidth=1.2)

    def _torus(self, x, y, z, major_radius, minor_radius, color="#00d4ff", alpha=0.8, normal=(0, 0, 1)):
        """
        Render a smooth torus with 3D orientation vector normal.
        Supports multi-angle orbital rings and angled winding coils matching aura_app.png.
        """
        if isinstance(major_radius, (list, tuple, np.ndarray)):
            major_radius = float(major_radius[0]) if len(major_radius) > 0 else 1.0
        major_radius = max(0.05, float(major_radius))

        if isinstance(minor_radius, (list, tuple, np.ndarray)):
            minor_radius = float(minor_radius[1]) if len(minor_radius) > 1 else float(minor_radius[0])
        minor_radius = float(minor_radius)
        if minor_radius >= major_radius or minor_radius <= 0:
            minor_radius = major_radius * 0.15

        u = np.linspace(0, 2 * np.pi, 30)
        v = np.linspace(0, 2 * np.pi, 16)
        u, v = np.meshgrid(u, v)
        xs0 = (major_radius + minor_radius * np.cos(v)) * np.cos(u)
        ys0 = (major_radius + minor_radius * np.cos(v)) * np.sin(u)
        zs0 = minor_radius * np.sin(v)

        norm_vec = np.asarray(normal, dtype=float)
        norm_len = float(np.linalg.norm(norm_vec))
        if norm_len > 1e-4:
            n_unit = norm_vec / norm_len
        else:
            n_unit = np.array([0.0, 0.0, 1.0])

        # Rotation matrix from [0, 0, 1] to n_unit
        if abs(n_unit[2] - 1.0) < 1e-4:
            xs, ys, zs = xs0 + x, ys0 + y, zs0 + z
        elif abs(n_unit[2] + 1.0) < 1e-4:
            xs, ys, zs = xs0 + x, ys0 + y, -zs0 + z
        else:
            ref = np.array([0.0, 0.0, 1.0])
            axis = np.cross(ref, n_unit)
            axis_len = np.linalg.norm(axis)
            axis_unit = axis / axis_len
            angle = np.arccos(np.clip(np.dot(ref, n_unit), -1.0, 1.0))
            # Rodrigues rotation
            c, s = np.cos(angle), np.sin(angle)
            R = (
                c * np.eye(3)
                + (1 - c) * np.outer(axis_unit, axis_unit)
                + s * np.array([
                    [0, -axis_unit[2], axis_unit[1]],
                    [axis_unit[2], 0, -axis_unit[0]],
                    [-axis_unit[1], axis_unit[0], 0],
                ])
            )
            pts = np.stack([xs0.ravel(), ys0.ravel(), zs0.ravel()], axis=0)
            pts_rot = R @ pts
            xs = pts_rot[0].reshape(xs0.shape) + x
            ys = pts_rot[1].reshape(ys0.shape) + y
            zs = pts_rot[2].reshape(zs0.shape) + z

        self.ax.plot_surface(xs, ys, zs, color=color, alpha=alpha, linewidth=0, shade=True)

    def _render_single_component(self, component, color=None, alpha=None):
        """Render a component respecting custom orientation, structural endpoints, and realistic materials."""
        comp_type = str(component.get("type", "sphere")).lower()
        pos = component.get("position", [0, 0, 0])
        x = float(pos[0]) if len(pos) > 0 else 0.0
        y = float(pos[1]) if len(pos) > 1 else 0.0
        z = float(pos[2]) if len(pos) > 2 else 0.0

        size = component.get("size", 1.0)
        c = color or component.get("color", "#00d4ff")
        a = alpha if alpha is not None else component.get("alpha", 0.85)

        if isinstance(size, (list, tuple, np.ndarray)):
            width = float(size[0]) if len(size) > 0 else 1.0
            height = float(size[1]) if len(size) > 1 else width
            depth = float(size[2]) if len(size) > 2 else width
        else:
            width = height = depth = float(size)

        # Check if component specifies physical structural endpoints
        endpoints = component.get("endpoints") or (
            [component.get("from_point"), component.get("to_point")]
            if component.get("from_point") and component.get("to_point")
            else None
        )
        if endpoints and len(endpoints) == 2 and endpoints[0] and endpoints[1]:
            radius = width if width < 0.6 else 0.12
            self._cylinder_between(endpoints[0], endpoints[1], radius, c, a, caps=True)
            return

        axis = component.get("axis", "z")
        normal = component.get("normal", (0, 0, 1))

        if comp_type in ("sphere", "atom", "point", "node", "nucleus"):
            self._sphere(x, y, z, width, c, a)
        elif comp_type in ("cylinder", "tube", "rod", "pipe", "shaft", "column", "piston"):
            self._cylinder(x, y, z, width, height, c, a, axis=axis)
        elif comp_type in ("cone", "valve", "emitter", "funnel", "nozzle"):
            self._cone(x, y, z, width, height, c, a, axis=axis)
        elif comp_type in ("box", "cube", "block", "chassis", "plate", "deck", "beam", "mount", "frame"):
            self._box(x, y, z, width, height, depth, c, a)
        elif comp_type in ("torus", "ring", "coil", "winding", "loop", "orbital"):
            minor_r = height if height != width and height < width else width * 0.12
            self._torus(x, y, z, width, minor_r, c, a, normal=normal)
        elif comp_type in ("line", "link", "arrow", "cable"):
            p1 = (x - width / 2.0, y, z)
            p2 = (x + width / 2.0, y, z)
            self._cylinder_between(p1, p2, 0.04, c, a)
        else:
            self._sphere(x, y, z, width, c, a)

    def _render_model_spec(self, model_spec):
        """Render ModelSpec with component selection, animations, 3D conduits, and smart non-overlapping labels."""
        if not model_spec:
            return

        animator = self.lab.animator
        selector = self.lab.selector
        affected_components = animator.get_affected_components() if animator.has_animation() else []
        selected_id = selector.get_selected().id if selector.get_selected() else None
        anim_action = animator.get_animation_action() if animator.has_animation() else None

        # 1. Render all solid components
        for component in model_spec.components:
            try:
                comp_id = component.get("id")
                color = component.get("color", "#00d4ff")
                alpha = component.get("alpha", 0.85)

                if comp_id == selected_id:
                    color = "#ffffff"
                    alpha = 1.0
                elif comp_id in affected_components:
                    if anim_action and anim_action.value == "pulse":
                        alpha = 0.5 + 0.5 * abs(math.sin(time.time() * 4))
                        color = "#ffcc00"
                    elif anim_action and anim_action.value == "highlight":
                        color = "#00ff88"
                        alpha = 1.0

                self._render_single_component(component, color, alpha)
            except Exception as e:
                print(f"[ThreeDCanvas] Error rendering component {component.get('id')}: {e}")

        # 2. Render solid physical conduits & connections
        component_positions = {}
        for c in model_spec.components:
            cid = c.get("id")
            pos = c.get("position", [0, 0, 0])
            if cid and len(pos) >= 3:
                component_positions[cid] = (float(pos[0]), float(pos[1]), float(pos[2]))

        for connection in model_spec.connections:
            from_id = connection.get("from")
            to_id = connection.get("to")
            if from_id in component_positions and to_id in component_positions:
                p1 = component_positions[from_id]
                p2 = component_positions[to_id]
                color = connection.get("color", "#00d4ff")
                thickness = float(connection.get("thickness", 2))

                if from_id in affected_components or to_id in affected_components:
                    color = "#ffcc00"
                    thickness = max(thickness, 4.0)

                # Physical solid cylindrical tube conduit
                tube_radius = max(0.02, 0.015 * thickness)
                self._cylinder_between(p1, p2, tube_radius, color=color, alpha=0.85, caps=True)
                # Joint node balls at junctions
                self._sphere(p1[0], p1[1], p1[2], tube_radius * 1.6, color=color, alpha=0.9, resolution=12)
                self._sphere(p2[0], p2[1], p2[2], tube_radius * 1.6, color=color, alpha=0.9, resolution=12)

        # 3. Smart Non-Overlapping Labels with Leader Lines
        # Prevents clutter and never blocks or covers the 3D model geometry
        if getattr(self.lab, "show_labels", True):
            comps_with_pos = [c for c in model_spec.components if len(c.get("position", [])) >= 3]
            if comps_with_pos:
                center_coords = np.mean([c.get("position") for c in comps_with_pos], axis=0)
            else:
                center_coords = np.array([0.0, 0.0, 0.0])

            # When model has many parts, label key parts and selected part to avoid visual clutter
            num_total = len(comps_with_pos)
            step_stride = 1 if num_total <= 8 else (2 if num_total <= 16 else 3)

            for idx, component in enumerate(comps_with_pos):
                cid = component.get("id")
                pos = component.get("position", [0, 0, 0])
                cx, cy, cz = float(pos[0]), float(pos[1]), float(pos[2])
                cname = component.get("name", cid)
                is_sel = (cid == selected_id)

                # If many parts exist, show selected part plus stride-filtered primary parts
                if not is_sel and (idx % step_stride != 0 and num_total > 10):
                    continue

                # Compute outward radial vector from model centroid
                delta = np.array([cx - center_coords[0], cy - center_coords[1], cz - center_coords[2]])
                dist = np.linalg.norm(delta)
                if dist > 0.15:
                    dir_vec = delta / dist
                else:
                    ang = (2 * np.pi * idx) / max(1, num_total)
                    dir_vec = np.array([np.cos(ang), np.sin(ang), 0.35])

                # Position label cleanly outside the model envelope
                leader_dist = 0.9 if not is_sel else 1.2
                lx = cx + dir_vec[0] * leader_dist
                ly = cy + dir_vec[1] * leader_dist
                lz = cz + dir_vec[2] * leader_dist + 0.3

                # Draw crisp leader line
                line_c = "#ff8c00" if is_sel else "#00e5ff"
                line_a = 0.9 if is_sel else 0.45
                self.ax.plot([cx, lx], [cy, ly], [cz, lz], color=line_c, linestyle=":", linewidth=1.1 if is_sel else 0.7, alpha=line_a)
                self.ax.plot([cx], [cy], [cz], marker="o", markersize=3, color=line_c, alpha=line_a)

                badge_bg = "#ff8c00" if is_sel else "#091724"
                badge_edge = "#ffffff" if is_sel else "#00e5ff"
                txt_color = "#ffffff" if is_sel else "#d4f4ff"
                self.ax.text(
                    lx, ly, lz,
                    f" {cname} ",
                    color=txt_color,
                    fontsize=7 if not is_sel else 8,
                    fontweight="bold",
                    ha="center",
                    va="bottom",
                    bbox=dict(
                        boxstyle="round,pad=0.25",
                        facecolor=badge_bg,
                        edgecolor=badge_edge,
                        alpha=0.92,
                        linewidth=1.2 if is_sel else 0.8,
                    ),
                )

    def _draw_interactive_backdrop(self):
        """
        Futuristic holographic blueprint workspace grid.
        Sleek dark cyan and teal lines on deep-space navy background matching aura_app.png.
        """
        floor_z = -3.2
        grid_range = np.linspace(-4.5, 4.5, 11)
        for gx in grid_range:
            is_center = abs(gx) < 0.1
            c = "#00d4ff" if is_center else "#0b2636"
            a = 0.4 if is_center else 0.18
            lw = 1.1 if is_center else 0.6
            self.ax.plot([gx, gx], [-4.5, 4.5], [floor_z, floor_z], color=c, alpha=a, linewidth=lw)
        for gy in grid_range:
            is_center = abs(gy) < 0.1
            c = "#2ec4b6" if is_center else "#0b2636"
            a = 0.4 if is_center else 0.18
            lw = 1.1 if is_center else 0.6
            self.ax.plot([-4.5, 4.5], [gy, gy], [floor_z, floor_z], color=c, alpha=a, linewidth=lw)

        # Concentric distance target rings on floor
        for rad in (2.0, 4.0):
            th = np.linspace(0, 2 * np.pi, 60)
            self.ax.plot(rad * np.cos(th), rad * np.sin(th), floor_z, color="#0b2636", alpha=0.22, linewidth=0.7)

    def draw_scene(self):
        self.ax.clear()
        self._style()
        self._draw_interactive_backdrop()

        if hasattr(self.lab, "model_spec") and self.lab.model_spec:
            self._render_model_spec(self.lab.model_spec)
        else:
            topic = self.lab.topic
            if topic == "DNA Double Helix": self._dna()
            elif topic == "Human Cell": self._cell()
            elif topic == "Solar System": self._solar()
            elif topic == "Electric Motor": self._motor()
            elif topic == "Internal Combustion Engine": self._engine()
            elif topic == "Atom": self._atom()
            elif topic == "Gear Train": self._gears()
            elif topic == "Bridge / Beam": self._bridge()
            elif topic == "Water Cycle": self._water()
            elif topic == "Heart": self._heart()
            else: self._generic()

        self.ax.view_init(elev=self.lab.elev, azim=self.lab.azim)
        self.ax.dist = max(3.0, min(16.0, self.lab.zoom))
        self.draw_idle()

    def _atom(self):
        """
        High-fidelity Rutherford-Bohr atom model matching reference image aura_app.png.
        Features a dense multi-particle nucleus and 3 smooth tilted orbital rings with electrons.
        """
        # Central dense nucleus with clustered protons and neutrons
        np.random.seed(42)
        n_particles = 12
        for i in range(n_particles):
            ang1 = np.random.uniform(0, 2 * np.pi)
            ang2 = np.random.uniform(-np.pi / 2, np.pi / 2)
            rad = np.random.uniform(0.08, 0.42)
            px = rad * np.cos(ang2) * np.cos(ang1)
            py = rad * np.cos(ang2) * np.sin(ang1)
            pz = rad * np.sin(ang2)
            color = "#ff3355" if i % 2 == 0 else "#8ffcff"
            self._sphere(px, py, pz, 0.22, color=color, alpha=0.95, resolution=16)

        # 3 smooth tilted electron orbital rings matching aura_app.png
        ring_normals = [
            (0.3, 0.4, 1.0),
            (-0.5, 0.6, 1.0),
            (0.8, -0.2, 0.6),
        ]
        ring_colors = ["#00e5ff", "#22d3ee", "#00ff88"]
        electron_phases = [0.4, 2.1, 4.3]

        for norm, col, ph in zip(ring_normals, ring_colors, electron_phases):
            self._torus(0, 0, 0, major_radius=2.4, minor_radius=0.035, color=col, alpha=0.85, normal=norm)
            # Electron particle sphere riding on orbital ring
            n_u = np.asarray(norm, dtype=float)
            n_u /= np.linalg.norm(n_u)
            ref = np.array([0.0, 0.0, 1.0]) if abs(n_u[2]) < 0.88 else np.array([1.0, 0.0, 0.0])
            u1 = np.cross(n_u, ref)
            u1 /= np.linalg.norm(u1)
            u2 = np.cross(n_u, u1)
            e_pos = 2.4 * np.cos(ph) * u1 + 2.4 * np.sin(ph) * u2
            self._sphere(e_pos[0], e_pos[1], e_pos[2], 0.16, color="#ffcc00", alpha=1.0, resolution=16)

    def _bridge(self):
        """Structurally complete 3D Warren truss bridge with piers, chords, cross-braces, and deck."""
        # Twin foundation pier abutments
        self._box(-3.2, 0, -1.0, 0.9, 2.2, 1.6, color="#2d3748", alpha=0.95)
        self._box(3.2, 0, -1.0, 0.9, 2.2, 1.6, color="#2d3748", alpha=0.95)

        # Bottom tension chords
        self._cylinder_between((-3.0, -0.7, 0.0), (3.0, -0.7, 0.0), 0.08, color="#00d4ff", alpha=0.95)
        self._cylinder_between((-3.0, 0.7, 0.0), (3.0, 0.7, 0.0), 0.08, color="#00d4ff", alpha=0.95)

        # Top compression chords
        self._cylinder_between((-2.0, -0.7, 1.6), (2.0, -0.7, 1.6), 0.08, color="#ff8c00", alpha=0.95)
        self._cylinder_between((-2.0, 0.7, 1.6), (2.0, 0.7, 1.6), 0.08, color="#ff8c00", alpha=0.95)

        # Roadway deck
        self._box(0, 0, -0.08, 6.2, 1.5, 0.16, color="#64748b", alpha=0.95)

        # Warren triangulated web struts
        pts_s = [(-3.0, 0.0), (-2.0, 1.6), (-1.0, 0.0), (0.0, 1.6), (1.0, 0.0), (2.0, 1.6), (3.0, 0.0)]
        for i in range(len(pts_s) - 1):
            p1_s = (pts_s[i][0], -0.7, pts_s[i][1])
            p2_s = (pts_s[i+1][0], -0.7, pts_s[i+1][1])
            col_s = "#ff3355" if i in (0, len(pts_s)-2) else ("#ffcc00" if i % 2 == 0 else "#00ff88")
            self._cylinder_between(p1_s, p2_s, 0.06, color=col_s, alpha=0.9)

            p1_n = (pts_s[i][0], 0.7, pts_s[i][1])
            p2_n = (pts_s[i+1][0], 0.7, pts_s[i+1][1])
            self._cylinder_between(p1_n, p2_n, 0.06, color=col_s, alpha=0.9)

        # Lateral portal sway bracing
        for x_c in (-2.0, 0.0, 2.0):
            self._cylinder_between((x_c, -0.7, 1.6), (x_c, 0.7, 1.6), 0.05, color="#cbd5e1", alpha=0.9)

    def _engine(self):
        """Four-stroke combustion cylinder with crankcase, piston, wrist pin, connecting rod, and valves."""
        self._box(0, 0, -1.2, 2.4, 1.8, 1.4, color="#1e293b", alpha=0.92) # Crankcase
        self._cylinder(0, 0, 0.4, radius=1.1, height=2.2, color="#0c2d48", alpha=0.45, axis="z") # Cylinder bore
        self._cylinder(0, 0, 0.9, radius=0.95, height=0.6, color="#ff8c00", alpha=0.95, axis="z") # Piston
        self._cylinder(0, 0, 0.9, radius=0.18, height=1.5, color="#cbd5e1", alpha=0.95, axis="y") # Wrist pin
        self._cylinder_between((0, 0, 0.9), (0.55, 0, -1.0), 0.14, color="#d8f8ff", alpha=0.95) # Connecting rod
        self._sphere(0.55, 0, -1.0, 0.42, color="#00d4ff", alpha=0.95) # Crankpin
        self._box(-0.4, 0, -1.0, 0.8, 0.35, 1.1, color="#475569", alpha=0.92) # Counterweight
        self._cylinder(0, 0, -1.0, radius=0.25, height=2.6, color="#00d4ff", alpha=0.95, axis="y") # Crankshaft
        self._box(0, 0, 2.2, 2.2, 1.6, 0.6, color="#334155", alpha=0.92) # Cylinder head
        self._cone(-0.55, 0, 1.8, radius=0.35, height=0.55, color="#00ff88", alpha=0.9, axis="z") # Intake valve
        self._cone(0.55, 0, 1.8, radius=0.35, height=0.55, color="#ff3355", alpha=0.9, axis="z") # Exhaust valve
        self._cylinder(0, 0, 2.4, radius=0.15, height=0.75, color="#ffcc00", alpha=0.98, axis="z") # Spark plug

    def _motor(self):
        """Industrial electric motor with cast-iron base, stator shoes, armature, and commutator."""
        self._box(0, 0, -1.7, 3.6, 2.6, 0.4, color="#1e293b", alpha=0.95) # Bedplate
        self._cylinder(0, 0, 0, radius=1.6, height=2.4, color="#0c3245", alpha=0.45, axis="y") # Stator housing
        self._box(-1.1, 0, 0, 0.5, 2.0, 1.2, color="#ff3355", alpha=0.9) # Stator N pole
        self._box(1.1, 0, 0, 0.5, 2.0, 1.2, color="#00d4ff", alpha=0.9)  # Stator S pole
        self._cylinder(0, 0, 0, radius=0.22, height=4.4, color="#cbd5e1", alpha=0.95, axis="y") # Rotor shaft
        self._cylinder(0, 0, 0, radius=0.85, height=1.8, color="#ff8c00", alpha=0.9, axis="y") # Armature core
        self._box(0, -1.3, 0, 0.7, 0.35, 0.7, color="#475569", alpha=0.9) # Front bearing
        self._box(0, 1.3, 0, 0.7, 0.35, 0.7, color="#475569", alpha=0.9)  # Rear bearing
        self._cylinder(0, 1.5, 0, radius=0.42, height=0.5, color="#ffcc00", alpha=0.95, axis="y") # Commutator
        self._box(-0.55, 1.5, 0, 0.22, 0.25, 0.35, color="#00ff88", alpha=0.95) # Brush +
        self._box(0.55, 1.5, 0, 0.22, 0.25, 0.35, color="#00ff88", alpha=0.95)  # Brush -

    def _gears(self):
        """Intermeshing dual-gear transmission showing torque and speed coupling."""
        self._box(0, 0, -1.5, 3.8, 1.4, 0.35, color="#1e293b", alpha=0.95) # Foundation
        self._gear(-1.1, 0, 0, 1.1, 14, color="#00d4ff") # Driving spur gear
        self._gear(1.3, 0, 0, 1.5, 20, color="#ff8c00")  # Driven spur gear
        self._cylinder(-1.1, 0, 0, 0.16, 2.2, color="#cbd5e1", alpha=0.95, axis="y") # Input shaft
        self._cylinder(1.3, 0, 0, 0.2, 2.2, color="#cbd5e1", alpha=0.95, axis="y")  # Output shaft

    def _gear(self, x, y, z, r, teeth, color):
        self._cylinder(x, y, z, radius=r, height=0.35, color=color, alpha=0.9, axis="y")
        for i in range(teeth):
            ang = 2 * np.pi * i / teeth
            tx = x + (r + 0.14) * np.cos(ang)
            tz = z + (r + 0.14) * np.sin(ang)
            self._box(tx, y, tz, 0.16, 0.35, 0.16, color=color, alpha=0.9)

    def _dna(self):
        """DNA double helix with helical backbone strands and colored A-T / G-C base pairs."""
        t = np.linspace(-2.4, 2.4, 45)
        for ti in t:
            x1 = 0.9 * np.sin(2.4 * ti)
            y1 = 0.9 * np.cos(2.4 * ti)
            x2 = -x1
            y2 = -y1
            self._sphere(x1, y1, ti, 0.12, "#00d4ff", 0.9)
            self._sphere(x2, y2, ti, 0.12, "#00ff88", 0.9)
            # Cross-rungs (hydrogen base pair bonds)
            pair_col = "#ff3355" if int(ti * 4) % 2 == 0 else "#ffcc00"
            self._cylinder_between((x1, y1, ti), (x2, y2, ti), 0.04, color=pair_col, alpha=0.85)

    def _cell(self):
        """Cellular biology model with cytoplasm, nucleus, mitochondria, and membrane."""
        self._sphere(0, 0, 0, 2.2, "#0ea5e9", 0.3)  # Cell membrane & cytoplasm
        self._sphere(0, 0, 0, 0.9, "#a855f7", 0.9)  # Nucleus
        self._sphere(0.15, 0.15, 0.1, 0.4, "#7c3aed", 0.95) # Nucleolus
        # Mitochondria
        self._cylinder(-1.0, 0.6, 0.3, radius=0.3, height=0.7, color="#f97316", alpha=0.95, axis="x")
        self._cylinder(1.0, -0.6, -0.3, radius=0.3, height=0.7, color="#f97316", alpha=0.95, axis="y")
        # Endoplasmic reticulum loop
        self._torus(0, 0, 0.1, major_radius=1.3, minor_radius=0.1, color="#10b981", alpha=0.8)

    def _solar(self):
        """Sun at center with elliptical planetary orbits."""
        self._sphere(0, 0, 0, 0.8, "#ffcc00", 0.95)  # Sun
        planets = [(1.3, 0.18, "#ff6b00"), (2.0, 0.28, "#00d4ff"), (2.7, 0.22, "#ff3355"), (3.5, 0.45, "#eab308")]
        for d, r, c in planets:
            self._torus(0, 0, 0, major_radius=d, minor_radius=0.015, color="#1e3a5f", alpha=0.6)
            self._sphere(d, 0, 0, r, c, 0.95)

    def _water(self):
        """Hydrological water cycle with ocean, cloud, and precipitation conduits."""
        self._box(0, 0, -1.5, 4.0, 4.0, 0.4, color="#005588", alpha=0.85) # Ocean
        self._sphere(-1.2, 0, 1.4, 0.75, "#cbd5e1", 0.9) # Cloud 1
        self._sphere(1.2, 0, 1.4, 0.85, "#cbd5e1", 0.9)  # Cloud 2
        # Conduits for evaporation and rainfall
        self._cylinder_between((-1.2, 0, -1.2), (-1.2, 0, 1.1), 0.05, color="#00e5ff", alpha=0.8)
        self._cylinder_between((1.2, 0, 1.1), (1.2, 0, -1.2), 0.05, color="#0088ff", alpha=0.8)
        self._torus(0, 0, 0.2, major_radius=2.0, minor_radius=0.06, color="#00d4ff", alpha=0.85, normal=(0, 1, 0))

    def _heart(self):
        """Four-chamber cardiac anatomy with ventricles, atria, and aortic arch."""
        self._sphere(-0.6, 0, 0.4, 0.85, "#ff3355", 0.9)  # Right atrium
        self._sphere(0.6, 0, 0.4, 0.85, "#ff3355", 0.9)   # Left atrium
        self._sphere(-0.5, 0, -0.7, 1.05, "#cc1133", 0.92) # Right ventricle
        self._sphere(0.5, 0, -0.7, 1.15, "#b30024", 0.95)  # Left ventricle
        # Aortic arch & pulmonary artery
        self._torus(0, 0, 1.4, major_radius=0.75, minor_radius=0.22, color="#ff3355", alpha=0.92)
        self._cylinder(0, 0, 1.2, radius=0.25, height=1.0, color="#00d4ff", alpha=0.9)

    def _generic(self):
        """Robust articulated engineering mechanism fallback with chassis, columns, and actuator."""
        self._box(0, 0, -1.6, 3.6, 2.4, 0.4, color="#1e293b", alpha=0.95) # Base foundation
        self._cylinder(-1.4, 0, -0.4, 0.15, 2.0, color="#5c6b73", alpha=0.9) # Column left
        self._cylinder(1.4, 0, -0.4, 0.15, 2.0, color="#5c6b73", alpha=0.9)  # Column right
        self._box(0, 0, 0.7, 3.2, 0.5, 0.35, color="#00d4ff", alpha=0.9)     # Top cross girder
        self._cylinder(0, 0, -0.2, radius=0.65, height=1.2, color="#ff6b00", alpha=0.95) # Core mechanism
        self._torus(0, 0, -0.2, major_radius=1.1, minor_radius=0.12, color="#00ff88", alpha=0.85)


# ---------- gesture control ----------

class GestureWorker(QObject):
    event = pyqtSignal(str)
    status = pyqtSignal(str)
    frame_ready = pyqtSignal(object)  # Emits QImage for live camera preview HUD

    HAND_CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),        # Index
        (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
        (9, 13), (13, 14), (14, 15), (15, 16), # Ring
        (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
        (0, 17),                               # Palm base
    ]

    def __init__(self, lab):
        super().__init__()
        self.lab = lab
        self.running = True
        self.last_xy = None
        self.last_pinch_y = None
        self.last_switch = 0
        self.cap = None

    def stop(self):
        self.running = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def _open_camera(self):
        """Open camera with DirectShow/MSMF on Windows for fast initialization."""
        if cv2 is None:
            return None
        import os
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if os.name == "nt" else [cv2.CAP_ANY]
        for backend in backends:
            try:
                cap = cv2.VideoCapture(0, backend)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    return cap
                cap.release()
            except Exception:
                pass
        # Try default 0
        try:
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                return cap
        except Exception:
            pass
        return None

    def _init_detector(self):
        """Initialize MediaPipe Tasks HandLandmarker or legacy solutions."""
        # 1. Try MediaPipe Tasks HandLandmarker (Python 3.13 / MediaPipe 1.0+)
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_tasks
            from mediapipe.tasks.python import vision
            base_dir = Path(__file__).resolve().parent.parent
            model_path = base_dir / "config" / "hand_landmarker.task"
            if model_path.exists():
                base_options = mp_tasks.BaseOptions(model_asset_path=str(model_path))
                options = vision.HandLandmarkerOptions(
                    base_options=base_options,
                    num_hands=1,
                    min_hand_detection_confidence=0.45,
                    min_tracking_confidence=0.45,
                )
                detector = vision.HandLandmarker.create_from_options(options)
                return "tasks", detector, mp
        except Exception as e:
            pass

        # 2. Try legacy mp.solutions.hands
        try:
            import mediapipe as mp
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):
                hands = mp.solutions.hands.Hands(
                    max_num_hands=1,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
                return "solutions", hands, mp
        except Exception:
            pass

        # 3. Fallback to OpenCV vision tracker
        return "opencv", None, None

    def _extract_landmarks_tasks(self, detector, mp_module, frame_rgb):
        """Extract landmarks from MediaPipe Tasks HandLandmarker."""
        try:
            mp_image = mp_module.Image(image_format=mp_module.ImageFormat.SRGB, data=frame_rgb)
            result = detector.detect(mp_image)
            if result.hand_landmarks and len(result.hand_landmarks) > 0:
                return result.hand_landmarks[0]
        except Exception:
            pass
        return None

    def _extract_landmarks_solutions(self, hands_detector, frame_rgb):
        """Extract landmarks from legacy MediaPipe solutions."""
        try:
            res = hands_detector.process(frame_rgb)
            if res.multi_hand_landmarks and len(res.multi_hand_landmarks) > 0:
                return res.multi_hand_landmarks[0].landmark
        except Exception:
            pass
        return None

    def _fingers_extended(self, lm):
        """Check extended state of 4 main fingers [index, middle, ring, pinky]."""
        return [
            lm[8].y < lm[6].y,   # Index
            lm[12].y < lm[10].y, # Middle
            lm[16].y < lm[14].y, # Ring
            lm[20].y < lm[18].y, # Pinky
        ]

    def _draw_hud(self, frame, landmarks, gesture_text):
        """Draw HUD annotations (skeleton, joints, badge) on camera frame."""
        h, w, _ = frame.shape

        # Draw semi-transparent header bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 42), (0, 10, 18), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        if landmarks is not None:
            pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

            # Draw bones (Green)
            for p1_idx, p2_idx in self.HAND_CONNECTIONS:
                if p1_idx < len(pts) and p2_idx < len(pts):
                    cv2.line(frame, pts[p1_idx], pts[p2_idx], (0, 230, 118), 2, cv2.LINE_AA)

            # Draw joints (Orange & White/Green)
            for idx, pt in enumerate(pts):
                color = (0, 140, 255) if idx in (4, 8, 12, 16, 20) else (255, 255, 255)
                radius = 5 if idx in (4, 8, 12, 16, 20) else 3
                cv2.circle(frame, pt, radius, color, -1, cv2.LINE_AA)

            # Highlight index & thumb pinch line (Orange)
            if len(pts) > 8:
                cv2.line(frame, pts[4], pts[8], (0, 140, 255), 2, cv2.LINE_AA)

        # Status text in HUD (Orange)
        text = gesture_text if gesture_text else "GESTURES ACTIVE — Move hand into view"
        cv2.putText(frame, text, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 140, 255), 2, cv2.LINE_AA)

        # Draw corner sci-fi border lines (Orange & Green)
        cv2.line(frame, (10, 10), (30, 10), (0, 140, 255), 2)
        cv2.line(frame, (10, 10), (10, 30), (0, 140, 255), 2)
        cv2.line(frame, (w - 10, 10), (w - 30, 10), (0, 140, 255), 2)
        cv2.line(frame, (w - 10, 10), (w - 10, 30), (0, 140, 255), 2)
        cv2.line(frame, (10, h - 10), (30, h - 10), (0, 230, 118), 2)
        cv2.line(frame, (10, h - 10), (10, h - 30), (0, 230, 118), 2)
        cv2.line(frame, (w - 10, h - 10), (w - 30, h - 10), (0, 230, 118), 2)
        cv2.line(frame, (w - 10, h - 10), (w - 10, h - 30), (0, 230, 118), 2)


    def run(self):
        if cv2 is None:
            self.status.emit("GESTURES OFF — OpenCV not installed")
            return

        self.cap = self._open_camera()
        if self.cap is None or not self.cap.isOpened():
            self.status.emit("GESTURES OFF — webcam unavailable")
            return

        mode, detector, mp_mod = self._init_detector()
        self.status.emit(f"GESTURES ACTIVE [{mode.upper()}] — index: rotate · pinch: zoom · palm: next/prev · fist: reset")

        active_gesture_banner = "Tracking hand..."
        while self.running:
            ok, frame = self.cap.read()
            if not ok or frame is None:
                time.sleep(0.03)
                continue

            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            landmarks = None
            if mode == "tasks" and detector:
                landmarks = self._extract_landmarks_tasks(detector, mp_mod, frame_rgb)
            elif mode == "solutions" and detector:
                landmarks = self._extract_landmarks_solutions(detector, frame_rgb)
            elif mode == "opencv":
                # OpenCV skin contour fallback
                landmarks = self._opencv_hand_tracking(frame)

            gesture_label = ""
            now = time.time()

            if landmarks is not None and len(landmarks) >= 21:
                lm = landmarks
                x, y = lm[8].x, lm[8].y
                tips = self._fingers_extended(lm)
                palm_open = all(tips)
                pinch_dist = math.hypot(lm[4].x - lm[8].x, lm[4].y - lm[8].y)
                pinch = pinch_dist < 0.075

                if pinch:
                    gesture_label = "PINCH: ZOOMING"
                    if self.last_pinch_y is not None:
                        dy = y - self.last_pinch_y
                        if abs(dy) > 0.006:
                            self.event.emit("zoom_out" if dy > 0 else "zoom_in")
                    self.last_pinch_y = y
                    self.last_xy = None

                elif sum(tips) == 1 and tips[0]:  # Index pointing only
                    gesture_label = "INDEX POINT: ROTATING"
                    if self.last_xy:
                        dx = x - self.last_xy[0]
                        dy = y - self.last_xy[1]
                        if abs(dx) > 0.004:
                            self.event.emit(f"rotate_y:{dx:.4f}")
                        if abs(dy) > 0.004:
                            self.event.emit(f"rotate_x:{dy:.4f}")
                    self.last_xy = (x, y)
                    self.last_pinch_y = None

                elif tips[0] and tips[1] and not tips[2] and not tips[3]:  # Peace / Victory sign
                    gesture_label = "PEACE: ANIMATION STEP"
                    if now - self.last_switch > 0.9:
                        self.event.emit("next_anim")
                        self.last_switch = now
                    self.last_xy = None
                    self.last_pinch_y = None

                elif palm_open:
                    if now - self.last_switch > 0.9:
                        if x > 0.6:
                            self.event.emit("next")
                            gesture_label = "PALM: NEXT MODEL"
                            self.last_switch = now
                        elif x < 0.4:
                            self.event.emit("previous")
                            gesture_label = "PALM: PREVIOUS MODEL"
                            self.last_switch = now
                        else:
                            gesture_label = "OPEN PALM: SWIPE LEFT/RIGHT"
                    else:
                        gesture_label = "PALM ACTIVE"
                    self.last_xy = None
                    self.last_pinch_y = None

                elif sum(tips) == 0 and now - self.last_switch > 0.8:
                    gesture_label = "FIST: RESET VIEW"
                    self.event.emit("reset")
                    self.last_switch = now
                    self.last_xy = None
                    self.last_pinch_y = None
                else:
                    gesture_label = "HAND DETECTED"
                    self.last_xy = (x, y)
            else:
                gesture_label = "Searching for hand in camera..."
                self.last_xy = None
                self.last_pinch_y = None

            # Render HUD and stream frame to Qt preview
            self._draw_hud(frame, landmarks, gesture_label)
            rgb_hud = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_hud.shape
            q_img = QImage(rgb_hud.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.frame_ready.emit(q_img)

            time.sleep(0.02)

        # Cleanup on stop
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.status.emit("GESTURES OFF")

    def _opencv_hand_tracking(self, frame):
        """Skin color & contour based landmark generator fallback."""
        try:
            ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
            mask = cv2.inRange(
                ycrcb,
                np.array([0, 133, 77], dtype=np.uint8),
                np.array([255, 173, 127], dtype=np.uint8),
            )
            mask = cv2.GaussianBlur(mask, (5, 5), 0)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return None

            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) < 3500:
                return None

            M = cv2.moments(c)
            if M["m00"] == 0:
                return None
            cx = float(M["m10"] / M["m00"])
            cy = float(M["m01"] / M["m00"])
            h, w, _ = frame.shape

            # Create mock landmark objects with .x and .y attributes
            class MockLandmark:
                def __init__(self, x_norm, y_norm):
                    self.x = max(0.0, min(1.0, float(x_norm)))
                    self.y = max(0.0, min(1.0, float(y_norm)))

            norm_cx, norm_cy = cx / w, cy / h
            # Generate 21 structured points relative to centroid
            lms = []
            for i in range(21):
                lms.append(MockLandmark(norm_cx + (i - 10) * 0.005, norm_cy + (i % 5 - 2) * 0.02))
            # Set index tip (8) and pip (6)
            top_pt = tuple(c[c[:, :, 1].argmin()][0])
            lms[8] = MockLandmark(top_pt[0] / w, top_pt[1] / h)
            lms[6] = MockLandmark(top_pt[0] / w, (top_pt[1] + 30) / h)
            lms[4] = MockLandmark((top_pt[0] - 25) / w, (top_pt[1] + 20) / h)
            return lms
        except Exception:
            return None



# ---------- Web Reference & Schematic Image Searcher & Downloader ----------

def _fetch_diagram_images(topic: str) -> list[dict]:
    try:
        from actions.image_search import search_diagram_images
        results = search_diagram_images(topic, max_results=6)
        for r in results:
            if "url" not in r and "image" in r:
                r["url"] = r["image"]
        return results
    except Exception as e:
        print(f"[ThreeDLab] Schematic search error: {e}")
        return []


def _download_pixmap(url: str) -> QPixmap | None:
    if not url:
        return None
    try:
        from actions.image_search import download_image_bytes
        data = download_image_bytes(url)
        if data:
            pix = QPixmap()
            if pix.loadFromData(data):
                return pix
    except Exception as e:
        print(f"[ThreeDLab] Download pixmap error: {e}")
    return None


# ---------- Web Reference & Schematic Image Viewer ----------

class WebDiagramWidget(QWidget):
    """Interactive web schematic & diagram image viewer for AURA 3D Learning Lab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._images: list[dict] = []
        self._current_index: int = 0
        self._current_pixmap: QPixmap | None = None
        self._current_topic: str = ""
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)

        header = QHBoxLayout()
        title_lbl = QLabel("🌐 WEB SCHEMATICS & DIAGRAMS")
        title_lbl.setStyleSheet("color:#ff8c00; font-weight:bold; font-size:11px;")
        header.addWidget(title_lbl)

        self.count_lbl = QLabel("0 / 0")
        self.count_lbl.setStyleSheet("color:#00ff88; font-size:10px;")
        header.addWidget(self.count_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        lay.addLayout(header)

        # Image display container
        self.img_lbl = QLabel("Searching web for reference diagrams…")
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setMinimumHeight(240)
        self.img_lbl.setStyleSheet("""
            QLabel {
                background: #161310;
                border: 1px solid #382d24;
                border-radius: 6px;
                color: #ffffff;
                font-size: 11px;
                padding: 4px;
            }
            QLabel:hover {
                border: 1px solid #ff8c00;
            }
        """)
        self.img_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.img_lbl.mousePressEvent = self._on_image_clicked
        lay.addWidget(self.img_lbl, 1)

        # Caption
        self.caption_lbl = QLabel("")
        self.caption_lbl.setStyleSheet("color:#ffffff; font-size:10px;")
        self.caption_lbl.setWordWrap(True)
        self.caption_lbl.setMaximumHeight(35)
        lay.addWidget(self.caption_lbl)

        # Controls row
        ctrl_row = QHBoxLayout()
        self.prev_btn = QPushButton("◀ PREV")
        self.prev_btn.setFixedHeight(26)
        self.prev_btn.clicked.connect(self.previous_image)
        ctrl_row.addWidget(self.prev_btn)

        self.next_btn = QPushButton("NEXT ▶")
        self.next_btn.setFixedHeight(26)
        self.next_btn.clicked.connect(self.next_image)
        ctrl_row.addWidget(self.next_btn)

        self.search_btn = QPushButton("🔍 SEARCH")
        self.search_btn.setFixedHeight(26)
        self.search_btn.clicked.connect(self._custom_search_dialog)
        ctrl_row.addWidget(self.search_btn)

        lay.addLayout(ctrl_row)

    def load_topic(self, topic: str):
        self._current_topic = topic
        self.img_lbl.setText(f"Searching schematics for: {topic}…")
        self.caption_lbl.setText("")
        self.count_lbl.setText("Searching…")
        threading.Thread(target=self._fetch_images_worker, args=(topic,), daemon=True).start()

    def _fetch_images_worker(self, topic: str):
        try:
            images = _fetch_diagram_images(topic)
            self._images = images
            self._current_index = 0
            if images:
                self._load_image_at_index(0)
            else:
                QTimer.singleShot(0, lambda: self.img_lbl.setText(f"No web diagrams found for: {topic}\nClick [🔍 SEARCH] to search custom keywords"))
                QTimer.singleShot(0, lambda: self.count_lbl.setText("0 / 0"))
        except Exception as e:
            print(f"[WebDiagramWidget] Fetch error: {e}")

    def _load_image_at_index(self, index: int):
        if not self._images or index < 0 or index >= len(self._images):
            return
        self._current_index = index
        img_info = self._images[index]
        pix = _download_pixmap(img_info.get("url", ""))
        self._current_pixmap = pix
        QTimer.singleShot(0, self._display_current)

    def _display_current(self):
        if not self._images:
            return
        total = len(self._images)
        curr = self._current_index + 1
        self.count_lbl.setText(f"{curr} / {total}")
        info = self._images[self._current_index]
        self.caption_lbl.setText(f"[{curr}/{total}] {info.get('title', '')}")

        if self._current_pixmap and not self._current_pixmap.isNull():
            w = max(100, self.img_lbl.width() - 8)
            h = max(100, self.img_lbl.height() - 8)
            scaled = self._current_pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.img_lbl.setPixmap(scaled)
        else:
            self.img_lbl.setText(f"Failed to load image [{curr}/{total}]\nClick [NEXT ▶] to view next result")

    def next_image(self):
        if self._images:
            self._current_index = (self._current_index + 1) % len(self._images)
            threading.Thread(target=self._load_image_at_index, args=(self._current_index,), daemon=True).start()

    def previous_image(self):
        if self._images:
            self._current_index = (self._current_index - 1) % len(self._images)
            threading.Thread(target=self._load_image_at_index, args=(self._current_index,), daemon=True).start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current_pixmap and not self._current_pixmap.isNull():
            self._display_current()

    def _on_image_clicked(self, event):
        if self._current_pixmap and not self._current_pixmap.isNull():
            dlg = QDialog(self)
            dlg.setWindowTitle("AURA — Web Schematic Diagram High-Res Preview")
            dlg.resize(920, 720)
            dlg.setStyleSheet("background:#0d0b09; color:#ffffff;")
            d_lay = QVBoxLayout(dlg)
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scaled = self._current_pixmap.scaled(
                890, 670,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            lbl.setPixmap(scaled)
            d_lay.addWidget(lbl)
            dlg.exec()

    def _custom_search_dialog(self):
        text, ok = QInputDialog.getText(self, "Search Web Diagrams", "Enter diagram or schematic query:")
        if ok and text.strip():
            self.load_topic(text.strip())


# ---------- main 3D Lab Window ----------

class ThreeDLab(QMainWindow):
    def __init__(self, reading_path: str | None = None, reading_text: str | None = None, speak=None, model_spec=None):
        super().__init__()
        self.setWindowTitle("AURA — 3D LEARNING LAB")
        self.resize(1320, 800)
        self.setStyleSheet("""
            QMainWindow, QWidget { background:#060b10; color:#e2f1f8; font-family: 'Segoe UI', Arial, sans-serif; }
            QPushButton { background:#0d1d2b; color:#00e5ff; border:1px solid #153c54; padding:7px 12px; border-radius:4px; font-weight:bold; }
            QPushButton:hover { border:1px solid #00e5ff; background:#122d42; color:#ffffff; }
            QListWidget, QTextEdit { background:#09141f; color:#e2f1f8; border:1px solid #153c54; border-radius:4px; }
            QTabWidget::pane { border: 1px solid #153c54; background: #071018; }
            QTabBar::tab { background: #0d1d2b; color: #7a9cb0; border: 1px solid #153c54; padding: 6px 14px; font-weight: bold; }
            QTabBar::tab:selected { background: #122d42; color: #00e5ff; border-bottom: 2px solid #00e5ff; }
            QProgressBar { background:#09141f; border:1px solid #153c54; text-align:center; color:#ffffff; border-radius:3px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d4ff, stop:1 #00ff88); }
        """)
        self.speak = speak
        self.model_spec = model_spec
        self.show_labels: bool = True

        self.selector = ComponentSelector()
        self.animator = AnimationPlayer()
        self.voice_parser = VoiceCommandParser()

        self.elev = 20.0
        self.azim = -60.0
        self.zoom = 7.0
        self.worker = None
        self.thread = None
        self.animation_timer = None

        self.tour_timer = QTimer(self)
        self.tour_timer.timeout.connect(self._step_parts_tour)
        self.tour_index: int = 0
        self.is_tour_running: bool = False

        self._init_models(reading_path, reading_text, model_spec)
        self._build()
        self._refresh()

        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.setInterval(120)

    def _init_models(self, reading_path, reading_text, model_spec):
        self.selector.clear()
        if model_spec:
            self.models = [(model_spec.topic, model_spec.explanation)]
            self.index = 0
            self.topic = model_spec.topic
            self.explanation = model_spec.explanation

            for comp in model_spec.components:
                self.selector.register_component(comp)
            self.voice_parser.update_component_map(model_spec.components)
            self.animator.load_animation_steps(model_spec.animation_steps)
        else:
            text = reading_text if reading_text is not None else _read_material(reading_path)
            self.models = _topics(text)
            self.index = 0
            self.topic, self.explanation = self.models[0]

    def update_model(self, model_spec=None, reading_path=None, reading_text=None):
        """Update the lab with a new model specification or reading."""
        self.model_spec = model_spec
        self._init_models(reading_path, reading_text, model_spec)

        self.list.blockSignals(True)
        self.list.clear()
        for topic, _ in self.models:
            self.list.addItem(QListWidgetItem(topic))
        self.list.setCurrentRow(self.index)
        self.list.blockSignals(False)

        if hasattr(self, "anim_box"):
            self.anim_box.setVisible(self.animator.has_animation())

        self.comp_info.clear()
        self._refresh()

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        lay = QHBoxLayout(root)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        # Left Panel (Controls & Topic List)
        left = QVBoxLayout()
        left.setSpacing(6)

        title = QLabel("◈ AURA 3D LEARNING LAB")
        title.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
        left.addWidget(title)

        self.file_lbl = QLabel("Interactive 3D Simulation & Concept Map")
        self.file_lbl.setStyleSheet("color:#3a8a9a")
        left.addWidget(self.file_lbl)

        # 3D Model Search & Generation bar
        search_box = QWidget()
        search_lay = QVBoxLayout(search_box)
        search_lay.setContentsMargins(0, 2, 0, 4)
        search_lay.setSpacing(4)

        search_lbl = QLabel("🔍 SEARCH / GENERATE 3D MODEL")
        search_lbl.setStyleSheet("color:#ff8c00; font-weight:bold; font-size:10px;")
        search_lay.addWidget(search_lbl)

        search_row = QHBoxLayout()
        search_row.setSpacing(4)
        self.model_search_input = QLineEdit()
        self.model_search_input.setPlaceholderText("e.g. Electric Motor, Drone, DNA...")
        self.model_search_input.setStyleSheet("background:#161310; border:1px solid #382d24; padding:5px; color:#ffffff; border-radius:3px;")
        self.model_search_input.returnPressed.connect(self._on_search_3d_model)
        search_row.addWidget(self.model_search_input)

        self.model_search_btn = QPushButton("GO")
        self.model_search_btn.setFixedWidth(40)
        self.model_search_btn.setStyleSheet("background:#2e1500; color:#ff8c00; border:1px solid #ff8c00; font-weight:bold; padding:4px;")
        self.model_search_btn.clicked.connect(self._on_search_3d_model)
        search_row.addWidget(self.model_search_btn)
        search_lay.addLayout(search_row)
        left.addWidget(search_box)

        self.list = QListWidget()
        for topic, _ in self.models:
            self.list.addItem(QListWidgetItem(topic))
        self.list.currentRowChanged.connect(self._select)
        left.addWidget(self.list, 1)

        self.label_btn = QPushButton("🏷️ 3D LABELS: ON")
        self.label_btn.clicked.connect(self._toggle_labels)
        left.addWidget(self.label_btn)

        for text, fn in [
            ("◀ PREVIOUS", self.previous),
            ("NEXT ▶", self.next),
            ("⟳ RESET VIEW", self.reset),
            ("📚 BROWSE EXAMPLES", self._browse_examples),
            ("✋ GESTURES", self.toggle_gestures),
        ]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            left.addWidget(b)

        # Animation Controls Container
        self.anim_box = QWidget()
        anim_lay = QVBoxLayout(self.anim_box)
        anim_lay.setContentsMargins(0, 4, 0, 4)
        anim_lay.setSpacing(4)

        anim_lbl = QLabel("⏯ ANIMATION CONTROL")
        anim_lbl.setStyleSheet("color:#ff8c00; font-weight:bold")
        anim_lay.addWidget(anim_lbl)

        btn_row = QHBoxLayout()
        for text, fn in [("▶ PLAY", self._play_anim), ("⏸ PAUSE", self._pause_anim), ("🔄 RESTART", self._restart_anim)]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            btn_row.addWidget(b)
        anim_lay.addLayout(btn_row)

        self.anim_progress = QProgressBar()
        anim_lay.addWidget(self.anim_progress)
        self.anim_status = QLabel("Animation: Ready")
        self.anim_status.setStyleSheet("color:#00ff88; font-size:11px;")
        anim_lay.addWidget(self.anim_status)
        left.addWidget(self.anim_box)
        self.anim_box.setVisible(self.animator.has_animation())

        self.gesture_lbl = QLabel("GESTURES: OFF")
        self.gesture_lbl.setWordWrap(True)
        self.gesture_lbl.setStyleSheet("color:#ff8c00; font-weight:bold;")
        left.addWidget(self.gesture_lbl)

        # Compact live camera thumbnail preview
        self.cam_preview = QLabel("📷 CAMERA FEED\nClick [✋ GESTURES] to start")
        self.cam_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cam_preview.setStyleSheet("background:#161310; border:1px solid #382d24; color:#ffffff; border-radius:4px; font-size:10px; padding:4px;")
        self.cam_preview.setFixedHeight(120)
        left.addWidget(self.cam_preview)

        lay.addLayout(left, 1)

        # Center 3D Canvas
        if FigureCanvas is None:
            self.canvas = None
            err = QLabel("Matplotlib is not installed. Run: pip install matplotlib")
            err.setWordWrap(True)
            lay.addWidget(err, 4)
        else:
            self.canvas = ThreeDCanvas(self)
            lay.addWidget(self.canvas, 4)

        # Right Panel (Tabbed: Model & Parts Breakdown | Web Schematics | Camera HUD)
        right = QVBoxLayout()
        right.setSpacing(6)

        self.tabs = QTabWidget()

        # --- Tab 1: Overview & Parts Breakdown ---
        parts_tab = QWidget()
        parts_lay = QVBoxLayout(parts_tab)
        parts_lay.setContentsMargins(6, 6, 6, 6)
        parts_lay.setSpacing(6)

        self.topic_lbl = QLabel()
        self.topic_lbl.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
        self.topic_lbl.setStyleSheet("color:#ff8c00;")
        self.topic_lbl.setWordWrap(True)
        parts_lay.addWidget(self.topic_lbl)

        self.explain = QTextEdit()
        self.explain.setReadOnly(True)
        self.explain.setMaximumHeight(85)
        parts_lay.addWidget(self.explain)

        # Explain all parts voice tour button
        self.tour_btn = QPushButton("🗣️ EXPLAIN ALL PARTS (VOICE TOUR)")
        self.tour_btn.setStyleSheet("background:#002914; color:#00ff88; border:1px solid #00ff88; padding:8px; font-weight:bold;")
        self.tour_btn.clicked.connect(self.toggle_parts_tour)
        parts_lay.addWidget(self.tour_btn)

        # Interactive Parts Breakdown List
        parts_header = QLabel("◆ SYSTEM COMPONENTS & PARTS")
        parts_header.setStyleSheet("color:#ff8c00; font-weight:bold; font-size:11px;")
        parts_lay.addWidget(parts_header)

        self.parts_list = QListWidget()
        self.parts_list.setMaximumHeight(140)
        self.parts_list.itemClicked.connect(self._on_part_item_clicked)
        parts_lay.addWidget(self.parts_list)

        # Selected Component Box
        comp_info_lbl = QLabel("◆ SELECTED COMPONENT DETAILS")
        comp_info_lbl.setStyleSheet("color:#00ff88; font-weight:bold; font-size:11px;")
        parts_lay.addWidget(comp_info_lbl)

        self.comp_info = QTextEdit()
        self.comp_info.setReadOnly(True)
        self.comp_info.setMaximumHeight(120)
        self.comp_info.setPlaceholderText("Click any 3D part or list item to view full engineering function and hear explanation...")
        parts_lay.addWidget(self.comp_info)

        self.tabs.addTab(parts_tab, "📋 MODEL & PARTS")

        # --- Tab 2: Web Schematics & Reference Diagrams ---
        self.diagram_widget = WebDiagramWidget(self)
        self.tabs.addTab(self.diagram_widget, "🌐 WEB SCHEMATICS")

        # --- Tab 3: Live Camera & Gesture HUD ---
        hud_tab = QWidget()
        hud_lay = QVBoxLayout(hud_tab)
        hud_lay.setContentsMargins(6, 6, 6, 6)
        hud_lay.setSpacing(6)

        hud_title = QLabel("📷 WEBCAM GESTURE TRACKING HUD")
        hud_title.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        hud_title.setStyleSheet("color:#ff8c00;")
        hud_lay.addWidget(hud_title)

        self.hud_cam_preview = QLabel("Webcam Feed Off\nClick [✋ GESTURES] to start camera tracking")
        self.hud_cam_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hud_cam_preview.setStyleSheet("background:#161310; border:1px solid #ff8c00; border-radius:4px; color:#ffffff; min-height:180px;")
        hud_lay.addWidget(self.hud_cam_preview, 1)

        guide_box = QTextEdit()
        guide_box.setReadOnly(True)
        guide_box.setMaximumHeight(120)
        guide_box.setHtml("""
        <div style='color:#ffffff; font-size:11px; line-height:1.4;'>
        <b style='color:#ff8c00;'>GESTURE CONTROLS GUIDE:</b><br/>
        • <b style='color:#00ff88;'>☝️ Point (1 Finger):</b> Drag to rotate 3D model (yaw & pitch)<br/>
        • <b style='color:#00ff88;'>🤏 Pinch (Thumb + Index):</b> Move up/down to Zoom In / Zoom Out<br/>
        • <b style='color:#00ff88;'>✋ Open Palm:</b> Sweep Right for Next Model · Sweep Left for Previous<br/>
        • <b style='color:#00ff88;'>✊ Fist (Closed):</b> Reset 3D camera to default orientation<br/>
        • <b style='color:#00ff88;'>✌️ Peace Sign:</b> Advance animation step
        </div>
        """)
        hud_lay.addWidget(guide_box)

        self.tabs.addTab(hud_tab, "📷 CAMERA HUD")

        right.addWidget(self.tabs, 1)

        self.hint = QLabel("Controls: Left-drag = rotate · Scroll = zoom · Click = select component · Double-click = reset")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color:#a3988c; font-size:10px;")

        right.addWidget(self.hint)

        close = QPushButton("CLOSE 3D LAB")
        close.clicked.connect(self.close)
        right.addWidget(close)

        lay.addLayout(right, 2)

    def _toggle_labels(self):
        self.show_labels = not self.show_labels
        self.label_btn.setText("🏷️ 3D LABELS: ON" if self.show_labels else "🏷️ 3D LABELS: OFF")
        if self.canvas:
            self.canvas.draw_scene()

    def _populate_parts_list(self):
        self.parts_list.clear()
        components = list(self.selector.component_map.values())
        for comp in components:
            item = QListWidgetItem(f"◆ {comp.name} [{comp.component_type.upper()}]")
            item.setData(Qt.ItemDataRole.UserRole, comp.id)
            self.parts_list.addItem(item)

    def _on_part_item_clicked(self, item: QListWidgetItem):
        cid = item.data(Qt.ItemDataRole.UserRole)
        if cid:
            self.select_component(cid)

    def toggle_parts_tour(self):
        if self.is_tour_running:
            self.tour_timer.stop()
            self.is_tour_running = False
            self.tour_btn.setText("🗣️ EXPLAIN ALL PARTS (VOICE TOUR)")
            self.tour_btn.setStyleSheet("background:#00293d; color:#00ff88; border:1px solid #00ff88; padding:8px;")
        else:
            components = list(self.selector.component_map.values())
            if not components:
                if self.speak: self.speak("No components available to explain.")
                return
            self.tour_index = 0
            self.is_tour_running = True
            self.tour_btn.setText("⏹ STOP VOICE TOUR")
            self.tour_btn.setStyleSheet("background:#330a10; color:#ff3355; border:1px solid #ff3355; padding:8px;")
            self._step_parts_tour()
            self.tour_timer.start(5500)

    def _step_parts_tour(self):
        components = list(self.selector.component_map.values())
        if not components or self.tour_index >= len(components):
            self.toggle_parts_tour()
            return
        comp = components[self.tour_index]
        self.select_component(comp.id)
        if self.parts_list.count() > self.tour_index:
            self.parts_list.setCurrentRow(self.tour_index)
        self.tour_index += 1

    def _play_anim(self):
        self.animator.play()
        self.animation_timer.start()
        if self.canvas: self.canvas.draw_scene()

    def _pause_anim(self):
        self.animator.pause()
        self.animation_timer.stop()
        if self.canvas: self.canvas.draw_scene()

    def _restart_anim(self):
        self.animator.stop()
        if self.canvas: self.canvas.draw_scene()

    def _on_search_3d_model(self):
        query = self.model_search_input.text().strip() if hasattr(self, "model_search_input") else ""
        if not query:
            return
        self.file_lbl.setText(f"Generating 3D model: {query}…")
        def _worker():
            try:
                from actions.model_generator import AIModelGenerator
                gen = AIModelGenerator()
                spec = gen.generate_model(query)
                if spec:
                    QTimer.singleShot(0, lambda: self.update_model(model_spec=spec))
                    if self.speak:
                        self.speak(f"Loaded {spec.topic} 3D model.")
                else:
                    QTimer.singleShot(0, lambda: self.file_lbl.setText(f"Could not generate model for: {query}"))
            except Exception as e:
                print(f"[ThreeDLab] 3D search/generate error: {e}")
                QTimer.singleShot(0, lambda: self.file_lbl.setText(f"Error: {e}"))
        threading.Thread(target=_worker, daemon=True).start()

    def _browse_examples(self):
        try:
            from actions.lab_ui_components import ExamplePromptsBrowser
            from actions.model_generator import AIModelGenerator

            def on_example_selected(prompt):
                generator = AIModelGenerator()
                spec = generator.generate_model(prompt)
                if spec:
                    self.update_model(model_spec=spec)
                    if self.speak:
                        self.speak(f"Loaded {spec.topic} 3D model.")

            browser = ExamplePromptsBrowser(self, on_select_callback=on_example_selected)
            browser.show()
        except Exception as e:
            print(f"[ThreeDLab] Browse examples error: {e}")

    def _select(self, i):
        if i < 0 or i >= len(self.models): return
        self.index = i
        self.topic, self.explanation = self.models[i]
        self._refresh()

    def _refresh(self):
        self.topic_lbl.setText(f"{self.topic}")
        self.explain.setText(self.explanation)
        if self.list.currentRow() != self.index:
            self.list.setCurrentRow(self.index)
        self._populate_parts_list()
        if hasattr(self, "diagram_widget"):
            self.diagram_widget.load_topic(self.topic)
        if self.canvas:
            self.canvas.draw_scene()
        if self.speak:
            self.speak(f"{self.topic}. {self.explanation.split(chr(10))[0]}")

    def next(self):
        if self.models:
            self.index = (self.index + 1) % len(self.models)
            self._refresh()

    def previous(self):
        if self.models:
            self.index = (self.index - 1) % len(self.models)
            self._refresh()

    def reset(self):
        self.elev = 20.0
        self.azim = -60.0
        self.zoom = 7.0
        if self.canvas:
            self.canvas.draw_scene()

    def _gesture(self, cmd):
        if cmd == "next":
            self.next()
        elif cmd == "previous":
            self.previous()
        elif cmd == "reset":
            self.reset()
        elif cmd == "next_anim":
            if self.animator.has_animation():
                self.animator.next_step()
                if hasattr(self, "anim_progress"):
                    self.anim_progress.setValue(int(self.animator.get_progress() * 100))
                if hasattr(self, "anim_status"):
                    self.anim_status.setText(self.animator.get_step_description())
                if self.canvas:
                    self.canvas.draw_scene()
        elif cmd == "zoom_in":
            self.zoom = max(2.5, self.zoom - 0.4)
            if self.canvas: self.canvas.draw_scene()
        elif cmd == "zoom_out":
            self.zoom = min(18.0, self.zoom + 0.4)
            if self.canvas: self.canvas.draw_scene()
        elif cmd.startswith("rotate_y:"):
            self.azim = (self.azim + float(cmd.split(":")[1]) * 160) % 360
            if self.canvas: self.canvas.draw_scene()
        elif cmd.startswith("rotate_x:"):
            self.elev = max(-85, min(85, self.elev - float(cmd.split(":")[1]) * 140))
            if self.canvas: self.canvas.draw_scene()

    def _on_gesture_frame(self, q_img):
        """Update live camera preview thumbnails with HUD overlay."""
        if not q_img or q_img.isNull():
            return
        pix = QPixmap.fromImage(q_img)
        if hasattr(self, "cam_preview") and self.cam_preview:
            w = max(100, self.cam_preview.width() - 4)
            h = max(80, self.cam_preview.height() - 4)
            self.cam_preview.setPixmap(
                pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
            )
        if hasattr(self, "hud_cam_preview") and self.hud_cam_preview and self.hud_cam_preview.isVisible():
            w = max(180, self.hud_cam_preview.width() - 6)
            h = max(140, self.hud_cam_preview.height() - 6)
            self.hud_cam_preview.setPixmap(
                pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
            )

    def toggle_gestures(self):
        if self.thread and self.thread.is_alive():
            if self.worker:
                self.worker.stop()
            self.gesture_lbl.setText("GESTURES: STOPPING…")
            if hasattr(self, "cam_preview"):
                self.cam_preview.setText("📷 CAMERA FEED\nStopped")
            if hasattr(self, "hud_cam_preview"):
                self.hud_cam_preview.setText("Webcam Feed Off\nClick [✋ GESTURES] to start camera tracking")
            return
        self.worker = GestureWorker(self)
        self.worker.event.connect(self._gesture)
        self.worker.status.connect(self.gesture_lbl.setText)
        self.worker.frame_ready.connect(self._on_gesture_frame)
        self.thread = threading.Thread(target=self.worker.run, daemon=True)
        self.thread.start()


    def _update_animation(self):
        if not self.animator.is_playing or not self.animator.has_animation():
            return
        self.animator.next_step()
        if hasattr(self, "anim_progress"):
            self.anim_progress.setValue(int(self.animator.get_progress() * 100))
        if hasattr(self, "anim_status"):
            self.anim_status.setText(self.animator.get_step_description())
        if self.canvas:
            self.canvas.draw_scene()

    def select_component(self, component_id: str):
        """Select a component and show its detailed explanation."""
        comp_info = self.selector.select_component(component_id)
        if comp_info:
            info_text = f"<b style='color:#00d4ff; font-size:13px;'>{comp_info.name}</b><br/>"
            info_text += f"<span style='color:#3a8a9a;'>Type: {comp_info.component_type.upper()} · Position: {comp_info.position}</span><br/><br/>"
            info_text += f"<span style='color:#d8f8ff;'>{comp_info.description}</span>"
            self.comp_info.setHtml(info_text)

            if self.speak:
                self.speak(f"Part: {comp_info.name}. {comp_info.description}")

            if self.canvas:
                self.canvas.draw_scene()

    def process_voice_command(self, text: str):
        """Process voice commands for component interaction and animation."""
        anim_cmd = self.voice_parser.parse_animation_command(text)
        if anim_cmd:
            if anim_cmd == "play": self._play_anim()
            elif anim_cmd == "pause": self._pause_anim()
            elif anim_cmd == "next":
                self.animator.next_step()
                if self.canvas: self.canvas.draw_scene()
            elif anim_cmd == "previous":
                self.animator.previous_step()
                if self.canvas: self.canvas.draw_scene()
            elif anim_cmd == "reset": self._restart_anim()
            return

        if self.voice_parser.is_component_query(text):
            component_id = self.voice_parser.parse_component_query(text)
            if component_id:
                self.select_component(component_id)
                return

        gesture_cmd = self.voice_parser.parse_gesture_command(text)
        if gesture_cmd:
            if gesture_cmd == "rotate": self.azim = (self.azim + 35) % 360
            elif gesture_cmd == "zoom_in": self.zoom = max(3.0, self.zoom - 0.8)
            elif gesture_cmd == "zoom_out": self.zoom = min(15.0, self.zoom + 0.8)
            if self.canvas: self.canvas.draw_scene()

    def closeEvent(self, event):
        global _active_lab
        if self.animation_timer:
            self.animation_timer.stop()
        if self.worker:
            self.worker.stop()
        if _active_lab is self:
            _active_lab = None
        event.accept()


_active_lab: ThreeDLab | None = None


def open_3d_lab(parameters=None, player=None, speak=None, model_spec=None):
    """Open or refresh the AURA 3D Learning Lab from uploaded reading or model spec."""
    global _active_lab
    parameters = parameters or {}
    path = parameters.get("file_path") or getattr(player, "current_file", None)
    if callable(path):
        try:
            path = path()
        except Exception:
            path = None
    text = parameters.get("text") or parameters.get("topic")
    model_spec = model_spec or parameters.get("model_spec")

    if _active_lab is not None and _active_lab.isVisible():
        _active_lab.update_model(model_spec=model_spec, reading_path=path, reading_text=text)
        _active_lab.raise_()
        _active_lab.activateWindow()
        return f"AURA 3D Learning Lab updated with {_active_lab.topic}."

    _active_lab = ThreeDLab(reading_path=path, reading_text=text, speak=speak, model_spec=model_spec)
    _active_lab.show()
    _active_lab.raise_()
    _active_lab.activateWindow()
    return f"3D Learning Lab opened with {len(_active_lab.models)} interactive diagram(s)."
