"""
ModelSpec Schema & Robust Validation / Repair Pipeline.

Provides Pydantic models and automatic repair for AI-generated 3D model specifications
so the browser frontend receives guaranteed valid, fully structured data.
"""

from __future__ import annotations

import re
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


VALID_COMPONENT_TYPES = {"box", "cylinder", "sphere", "torus", "cone", "line", "tube", "plane", "ring"}
VALID_ANIMATION_ACTIONS = {
    "pulse", "rotate", "highlight", "move", "flow", "scale", "fade",
    "electrical_flow", "magnetic_flux", "mechanical_rotation", "fluid_flow",
    "heat_transfer", "signal_propagation", "force_motion", "biological_flow",
}
VALID_CONNECTION_TYPES = {"flow", "link", "signal", "conduit", "joint", "electrical", "hydraulic", "magnetic"}


class ComponentSpec(BaseModel):
    id: str
    name: str = "Component"
    type: str = "box"
    position: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    size: Any = Field(default_factory=lambda: [1.0, 1.0, 1.0])
    color: str = "#00d4ff"
    alpha: float = 0.9
    axis: Optional[str] = "z"
    endpoints: Optional[list[list[float]]] = None
    normal: Optional[list[float]] = None
    description: str = "Structural and functional component."
    material: Optional[str] = "standard"
    role: Optional[str] = "Structural"

    @field_validator("type", mode="before")
    @classmethod
    def clean_type(cls, v: Any) -> str:
        s = str(v).lower().strip()
        if s in VALID_COMPONENT_TYPES:
            return s
        if "cyl" in s:
            return "cylinder"
        if "sphere" in s or "ball" in s:
            return "sphere"
        if "ring" in s or "torus" in s or "coil" in s:
            return "torus"
        if "cone" in s or "nozzle" in s:
            return "cone"
        if "line" in s or "wire" in s:
            return "line"
        return "box"

    @field_validator("position", mode="before")
    @classmethod
    def clean_position(cls, v: Any) -> list[float]:
        if isinstance(v, (list, tuple)):
            out = []
            for item in list(v)[:3]:
                try:
                    out.append(float(item))
                except Exception:
                    out.append(0.0)
            while len(out) < 3:
                out.append(0.0)
            return out
        return [0.0, 0.0, 0.0]

    @field_validator("color", mode="before")
    @classmethod
    def clean_color(cls, v: Any) -> str:
        s = str(v).strip()
        if re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", s):
            return s
        named_colors = {
            "orange": "#ff8c00",
            "cyan": "#00d4ff",
            "blue": "#0284c7",
            "green": "#10b981",
            "red": "#ef4444",
            "gold": "#f59e0b",
            "yellow": "#eab308",
            "white": "#f8fafc",
            "gray": "#64748b",
            "steel": "#475569",
            "copper": "#d97706",
        }
        return named_colors.get(s.lower(), "#00d4ff")


class ConnectionSpec(BaseModel):
    from_id: str
    to_id: str
    type: str = "link"
    color: str = "#00d4ff"
    thickness: float = 2.0
    label: str = "Connection"

    @field_validator("thickness", mode="before")
    @classmethod
    def clean_thickness(cls, v: Any) -> float:
        try:
            val = float(v)
            return max(0.5, min(10.0, val))
        except Exception:
            return 2.0


class AnimationStepSpec(BaseModel):
    step: int
    description: str = "Operational phase"
    affected_components: list[str] = Field(default_factory=list)
    action: str = "pulse"
    duration: float = 1.5
    intensity: float = 1.0
    conduit_id: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action", mode="before")
    @classmethod
    def clean_action(cls, v: Any) -> str:
        s = str(v).lower().strip()
        return s if s in VALID_ANIMATION_ACTIONS else "pulse"


class ModelSpecData(BaseModel):
    topic: str
    explanation: str
    components: list[ComponentSpec]
    connections: list[ConnectionSpec] = Field(default_factory=list)
    animation_steps: list[AnimationStepSpec] = Field(default_factory=list)
    camera: Optional[dict[str, Any]] = None


def validate_and_repair_model_spec(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Validates any AI-generated or raw dictionary into a guaranteed valid ModelSpec.
    Performs deep automatic repair of missing fields, malformed coordinates,
    dangling connections, and animation references.
    """
    if not isinstance(raw, dict):
        raw = {}

    topic = str(raw.get("topic") or "Dynamic 3D Engineering Model").strip()
    explanation = str(raw.get("explanation") or f"Interactive 3D model demonstrating {topic}.").strip()

    raw_components = raw.get("components") or []
    if not isinstance(raw_components, list):
        raw_components = []

    validated_components: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for idx, c in enumerate(raw_components):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or f"comp_{idx + 1}").strip().replace(" ", "_").lower()
        if cid in seen_ids:
            cid = f"{cid}_{idx}"
        seen_ids.add(cid)

        # Sanitize position
        pos = c.get("position", [0.0, 0.0, 0.0])
        if not isinstance(pos, (list, tuple)) or len(pos) < 3:
            pos = [0.0, 0.0, 0.0]
        else:
            pos = [float(pos[0]), float(pos[1]), float(pos[2])]

        # Sanitize size
        size = c.get("size")
        if size is None:
            size = [1.0, 1.0, 1.0] if c.get("type") == "box" else 0.5
        elif isinstance(size, (list, tuple)):
            size = [max(0.05, float(x)) for x in size]
        else:
            try:
                size = max(0.05, float(size))
            except Exception:
                size = 0.5

        # Sanitize endpoints if provided
        endpoints = c.get("endpoints")
        clean_endpoints = None
        if isinstance(endpoints, (list, tuple)) and len(endpoints) >= 2:
            try:
                p1 = [float(x) for x in endpoints[0][:3]]
                p2 = [float(x) for x in endpoints[1][:3]]
                clean_endpoints = [p1, p2]
            except Exception:
                clean_endpoints = None

        comp_dict = {
            "id": cid,
            "name": str(c.get("name") or f"Part {idx + 1}").strip(),
            "type": c.get("type", "box"),
            "position": pos,
            "size": size,
            "color": c.get("color", "#00d4ff"),
            "alpha": max(0.1, min(1.0, float(c.get("alpha", 0.9)))),
            "axis": str(c.get("axis") or "z").lower(),
            "endpoints": clean_endpoints,
            "description": str(c.get("description") or f"Engineered component for {topic}.").strip(),
            "role": str(c.get("role") or "Core Assembly").strip(),
            "material": str(c.get("material") or "metal").strip(),
        }

        try:
            validated_c = ComponentSpec(**comp_dict)
            validated_components.append(validated_c.model_dump())
        except Exception:
            # Fallback default
            validated_components.append(comp_dict)

    # Fallback if no components survived
    if not validated_components:
        validated_components = [
            {
                "id": "base_plate",
                "name": "Chassis Foundation Base",
                "type": "box",
                "position": [0.0, 0.0, -1.2],
                "size": [4.0, 4.0, 0.2],
                "color": "#334155",
                "alpha": 1.0,
                "axis": "z",
                "description": "Rigid foundation supporting the mechanical assembly.",
                "role": "Foundation",
                "material": "steel",
            },
            {
                "id": "primary_unit",
                "name": f"{topic} Core Unit",
                "type": "cylinder",
                "position": [0.0, 0.0, 0.2],
                "size": [0.8, 2.0],
                "color": "#ff8c00",
                "alpha": 0.95,
                "axis": "z",
                "description": f"Main operational component of {topic}.",
                "role": "Active Core",
                "material": "copper",
            },
        ]
        seen_ids = {"base_plate", "primary_unit"}

    # Sanitize connections
    raw_connections = raw.get("connections") or []
    validated_connections: list[dict[str, Any]] = []
    if isinstance(raw_connections, list):
        for conn in raw_connections:
            if not isinstance(conn, dict):
                continue
            from_id = str(conn.get("from") or conn.get("from_id", "")).strip().replace(" ", "_").lower()
            to_id = str(conn.get("to") or conn.get("to_id", "")).strip().replace(" ", "_").lower()
            if from_id in seen_ids and to_id in seen_ids and from_id != to_id:
                validated_connections.append({
                    "from_id": from_id,
                    "to_id": to_id,
                    "type": str(conn.get("type", "link")).lower(),
                    "color": conn.get("color", "#00d4ff"),
                    "thickness": float(conn.get("thickness", 2.5)),
                    "label": str(conn.get("label", "Interaction / Conduit")),
                })

    # Sanitize animation steps
    raw_steps = raw.get("animation_steps") or []
    validated_steps: list[dict[str, Any]] = []
    if isinstance(raw_steps, list):
        for s_idx, step in enumerate(raw_steps):
            if not isinstance(step, dict):
                continue
            affected = [
                str(x).strip().replace(" ", "_").lower()
                for x in step.get("affected_components", [])
                if str(x).strip().replace(" ", "_").lower() in seen_ids
            ]
            if not affected and validated_components:
                affected = [validated_components[s_idx % len(validated_components)]["id"]]

            action = str(step.get("action", "pulse")).lower()
            if action not in VALID_ANIMATION_ACTIONS:
                action = "pulse"

            step_params = step.get("params") or {}
            if not isinstance(step_params, dict):
                step_params = {}

            # Populate defaults for specific semantic actions
            if action == "mechanical_rotation" and "rpm" not in step_params:
                step_params["rpm"] = 45.0
                step_params["axis"] = step.get("axis", "z")
            elif action == "electrical_flow" and "speed" not in step_params:
                step_params["speed"] = 1.2
                step_params["color"] = "#00ffff"
            elif action == "fluid_flow" and "speed" not in step_params:
                step_params["speed"] = 1.0
                step_params["color"] = "#00e5ff"
            elif action == "magnetic_flux" and "frequency" not in step_params:
                step_params["frequency"] = 1.5
                step_params["color"] = "#ffaa00"
            elif action == "heat_transfer" and "color" not in step_params:
                step_params["color"] = "#ff3300"

            validated_steps.append({
                "step": s_idx + 1,
                "description": str(step.get("description") or f"Phase {s_idx + 1}: Operation of {', '.join(affected)}"),
                "affected_components": affected,
                "action": action,
                "duration": float(step.get("duration", 1.5)),
                "intensity": float(step.get("intensity", 1.0)),
                "conduit_id": step.get("conduit_id"),
                "params": step_params,
            })

    # If no animation steps, generate realistic concept-based semantic sequential steps
    if not validated_steps:
        topic_low = topic.lower()
        if any(k in topic_low for k in ["motor", "engine", "turbine", "gear", "wheel", "rotor", "fan"]):
            default_action = "mechanical_rotation"
        elif any(k in topic_low for k in ["transformer", "circuit", "battery", "coil", "resistor", "inductor"]):
            default_action = "electrical_flow"
        elif any(k in topic_low for k in ["hydraulic", "pipe", "fluid", "pump", "valve", "cooling"]):
            default_action = "fluid_flow"
        elif any(k in topic_low for k in ["heart", "cell", "lung", "blood", "organ", "neuron"]):
            default_action = "biological_flow"
        else:
            default_action = "pulse"

        for idx, comp in enumerate(validated_components[:5]):
            actions = [default_action, "highlight", "pulse"]
            cur_act = actions[idx % len(actions)]
            params = {}
            if cur_act == "mechanical_rotation":
                params = {"rpm": 30.0, "axis": comp.get("axis", "z")}
            elif cur_act == "electrical_flow":
                params = {"speed": 1.2, "color": "#00ffff"}
            elif cur_act == "fluid_flow":
                params = {"speed": 1.0, "color": "#0ea5e9"}

            validated_steps.append({
                "step": idx + 1,
                "description": f"Phase {idx + 1}: Engaging {comp['name']} ({cur_act.replace('_', ' ')}).",
                "affected_components": [comp["id"]],
                "action": cur_act,
                "duration": 1.8,
                "intensity": 1.0,
                "params": params,
            })

    # Calculate 3D Bounding Box & Optimal Camera Framing
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")

    for c in validated_components:
        px, py, pz = c["position"]
        s = c["size"]
        if isinstance(s, (list, tuple)) and len(s) >= 3:
            sx, sy, sz = float(s[0]), float(s[1]), float(s[2])
        elif isinstance(s, (list, tuple)) and len(s) == 2:
            sx = sy = float(s[0])
            sz = float(s[1])
        else:
            try:
                sx = sy = sz = float(s)
            except Exception:
                sx = sy = sz = 1.0

        min_x = min(min_x, px - sx / 2)
        max_x = max(max_x, px + sx / 2)
        min_y = min(min_y, py - sy / 2)
        max_y = max(max_y, py + sy / 2)
        min_z = min(min_z, pz - sz / 2)
        max_z = max(max_z, pz + sz / 2)

    if min_x == float("inf"):
        min_x, min_y, min_z = -2.0, -2.0, -2.0
        max_x, max_y, max_z = 2.0, 2.0, 2.0

    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    cz = (min_z + max_z) / 2.0
    diag = ((max_x - min_x) ** 2 + (max_y - min_y) ** 2 + (max_z - min_z) ** 2) ** 0.5
    radius = max(2.5, diag / 2.0)

    computed_camera = {
        "fov": 45,
        "target": [round(cx, 2), round(cy, 2), round(cz, 2)],
        "position": [round(cx + radius * 1.8, 2), round(cy + radius * 1.3, 2), round(cz + radius * 1.8, 2)],
        "bounding_radius": round(radius, 2),
        "bounding_center": [round(cx, 2), round(cy, 2), round(cz, 2)],
    }

    # Merge with custom camera if present
    custom_cam = raw.get("camera") or {}
    if isinstance(custom_cam, dict) and "position" in custom_cam:
        computed_camera["position"] = custom_cam["position"]
    if isinstance(custom_cam, dict) and "target" in custom_cam:
        computed_camera["target"] = custom_cam["target"]

    return {
        "topic": topic,
        "explanation": explanation,
        "components": validated_components,
        "connections": validated_connections,
        "animation_steps": validated_steps,
        "reference_images": raw.get("reference_images", []),
        "camera": computed_camera,
    }


class ModelSpecSchema:
    """Convenience validator class wrapping ModelSpecData and validate_and_repair_model_spec."""

    @classmethod
    def validate_spec(cls, data: dict[str, Any]) -> tuple[bool, list[str]]:
        errors = []
        if not isinstance(data, dict):
            return False, ["ModelSpec must be a dictionary"]
        if "topic" not in data or not str(data.get("topic", "")).strip():
            errors.append("Missing required field: 'topic'")
        if "explanation" not in data or not str(data.get("explanation", "")).strip():
            errors.append("Missing required field: 'explanation'")
        if "components" not in data or not isinstance(data.get("components"), list) or len(data.get("components", [])) == 0:
            errors.append("Missing or empty required field: 'components'")

        return len(errors) == 0, errors

    @classmethod
    def repair(cls, data: dict[str, Any]) -> dict[str, Any]:
        return validate_and_repair_model_spec(data)

