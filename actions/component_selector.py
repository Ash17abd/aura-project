"""
Component interaction system for 3D models.

Handles mouse clicks, component selection, highlighting, and detailed explanations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class ComponentInfo:
    """Information about a selected component."""
    id: str
    name: str
    description: str
    position: tuple[float, float, float]
    color: str
    component_type: str


class ComponentSelector:
    """Manages component selection and highlighting in 3D models."""

    def __init__(self):
        self.selected_component: Optional[ComponentInfo] = None
        self.highlighted_ids: set[str] = set()
        self.component_map: dict[str, ComponentInfo] = {}
        self.on_select_callback: Optional[Callable] = None

    def clear(self) -> None:
        """Clear all registered components and selection."""
        self.selected_component = None
        self.highlighted_ids.clear()
        self.component_map.clear()

    def register_component(self, component) -> None:
        """Register a component for selection."""
        if isinstance(component, dict):
            comp_id = component.get("id")
            if not comp_id:
                return
            pos = component.get("position", [0, 0, 0])
            if isinstance(pos, (list, tuple)) and len(pos) >= 3:
                position = (float(pos[0]), float(pos[1]), float(pos[2]))
            else:
                position = (0.0, 0.0, 0.0)

            info = ComponentInfo(
                id=comp_id,
                name=component.get("name", "Unknown Component"),
                description=component.get("description", "No description available."),
                position=position,
                color=component.get("color", "#00d4ff"),
                component_type=component.get("type", "sphere"),
            )
            self.component_map[comp_id] = info
        elif isinstance(component, ComponentInfo):
            self.component_map[component.id] = component

    def select_component(self, component_id: str) -> Optional[ComponentInfo]:
        """Select a component by ID."""
        if component_id not in self.component_map:
            return None

        self.selected_component = self.component_map[component_id]
        self.highlighted_ids = {component_id}

        if self.on_select_callback:
            self.on_select_callback(self.selected_component)

        return self.selected_component

    def clear_selection(self) -> None:
        """Clear current selection."""
        self.selected_component = None
        self.highlighted_ids.clear()

    def highlight_components(self, component_ids: list[str]) -> None:
        """Highlight multiple components."""
        self.highlighted_ids = set(component_ids)

    def find_nearest_component_screen(
        self, pixel_x: float, pixel_y: float, ax
    ) -> Optional[str]:
        """Find the nearest component using Matplotlib 3D-to-screen pixel projection."""
        if not self.component_map or ax is None:
            return None

        try:
            from mpl_toolkits.mplot3d import proj3d
            proj = ax.get_proj()
            min_dist = float("inf")
            nearest_id = None

            for comp_id, comp_info in self.component_map.items():
                x, y, z = comp_info.position
                x2d, y2d, _ = proj3d.proj_transform(x, y, z, proj)
                screen_pt = ax.transData.transform((x2d, y2d))
                dx = screen_pt[0] - pixel_x
                dy = screen_pt[1] - pixel_y
                dist = (dx * dx + dy * dy) ** 0.5

                if dist < min_dist and dist < 65:  # 65-pixel click radius
                    min_dist = dist
                    nearest_id = comp_id

            return nearest_id
        except Exception:
            return None

    def find_nearest_component(
        self, click_x: float, click_y: float, camera_pos: tuple = (0, 0, 0)
    ) -> Optional[str]:
        """Fallback 2D projection selection."""
        if not self.component_map:
            return None

        min_dist = float("inf")
        nearest_id = None

        for comp_id, comp_info in self.component_map.items():
            x, y, z = comp_info.position
            dist = ((x - click_x) ** 2 + (y - click_y) ** 2) ** 0.5

            if dist < min_dist and dist < 1.0:
                min_dist = dist
                nearest_id = comp_id

        return nearest_id

    def get_selected(self) -> Optional[ComponentInfo]:
        """Get currently selected component."""
        return self.selected_component
