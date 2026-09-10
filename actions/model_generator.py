"""
AI-powered procedural 3D model generator.

Converts natural language instructions into dynamic 3D educational models
using Gemini AI, OpenRouter, and procedural geometry catalogs.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("model_generator")

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

legacy_genai = None



def _get_api_keys() -> dict[str, str]:
    """Load API keys from config."""
    base_dir = Path(__file__).resolve().parent.parent
    api_file = base_dir / "config" / "api_keys.json"
    try:
        with open(api_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class ModelSpec:
    """Specification for a procedurally generated 3D model."""

    def __init__(
        self,
        topic: str,
        components: list[dict[str, Any]],
        connections: list[dict[str, Any]],
        explanation: str,
        animation_steps: list[dict[str, Any]] | None = None,
    ):
        self.topic = topic
        self.components = components
        self.connections = connections
        self.explanation = explanation
        self.animation_steps = animation_steps or []

    @classmethod
    def from_json(cls, data: dict) -> ModelSpec:
        """Create ModelSpec from JSON data."""
        return cls(
            topic=data.get("topic", "Custom Model"),
            components=data.get("components", []),
            connections=data.get("connections", []),
            explanation=data.get("explanation", ""),
            animation_steps=data.get("animation_steps", []),
        )

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "components": self.components,
            "connections": self.connections,
            "explanation": self.explanation,
            "animation_steps": self.animation_steps,
        }


class AIModelGenerator:
    """Generates 3D model specifications from natural language instructions."""

    SYSTEM_PROMPT = """You are an elite educational 3D mechanical and physical system designer.

Your job is to convert user requests into comprehensive, high-fidelity 3D model specifications in JSON format.

When a user asks to create or visualize any concept, device, or system, respond with ONLY valid JSON (no markdown outside the JSON, no commentary) following this exact schema:

{
  "topic": "Precise name of the system (e.g., 'Step-Down Electrical Transformer', 'Turbofan Jet Engine')",
  "components": [
    {
      "id": "unique_component_id",
      "type": "cylinder|box|sphere|torus|cone|line",
      "name": "Human-readable Part Name (e.g., 'Primary Winding Coil', 'Caliper Piston')",
      "position": [x, y, z],
      "size": [width, height, depth] or radius or [radius, height],
      "color": "#RRGGBB (vibrant hex color)",
      "alpha": 0.5-1.0,
      "axis": "x|y|z (optional alignment for cylinders/boxes)",
      "endpoints": [[x1, y1, z1], [x2, y2, z2]] (optional: for structural beams, struts, bracing, pipes directly between joints),
      "normal": [nx, ny, nz] (optional: for tilted torus orbital rings or coils),
      "description": "Detailed 1-2 sentence engineering/scientific explanation of this part's exact role and how it operates within the system."
    }
  ],
  "connections": [
    {
      "from": "component_id_1",
      "to": "component_id_2",
      "type": "flow|link|signal",
      "color": "#RRGGBB",
      "thickness": 2-5,
      "label": "Interaction or flow description (e.g., 'Magnetic Flux Coupling', 'Hydraulic Fluid Pressure')"
    }
  ],
  "explanation": "Comprehensive technical summary (2-4 sentences) explaining the fundamental operating principles, physics/mechanics, and how all components work together.",
  "animation_steps": [
    {
      "step": 1,
      "description": "Clear step-by-step description of this operational phase.",
      "affected_components": ["component_id_1", "component_id_2"],
      "action": "pulse|highlight|rotate|move"
    }
  ]
}

CRITICAL ENGINEERING DESIGN & FIDELITY RULES:
1. STRICT FIDELITY TO USER INSTRUCTION:
   - You MUST generate the EXACT concept, system, mechanism, or subject requested by the user.
   - Do NOT substitute a generic or predefined model. Every component explicitly or implicitly requested by the user must be represented.
   - For example, if the user asks for a 'hydraulic braking system with master cylinder and vented caliper', you must model the pedal arm, pushrod, master cylinder reservoir, hydraulic steel brake lines, caliper bracket, and vented brake disc at their correct relative positions.

2. LOGICAL PROPORTIONS & SPATIAL HIERARCHY:
   - Base & Mount: All mechanical/physical systems must rest on or emerge from an appropriately sized mounting chassis, base plate, or support frame.
   - Proportions: Components must have realistic relative aspect ratios (e.g. shafts length >> radius; disks radius >> thickness; pipes/tubes radius << length; coils wrapped around magnetic cores).
   - Alignment: Parts that connect must physically touch or align at logical 3D node coordinates.

3. SPATIAL ACCURACY & JOINING:
   - For structural beams, diagonal struts, connecting rods, pipes, and shafts, specify "endpoints": [[x1, y1, z1], [x2, y2, z2]] so members meet precisely at structural node joints.
   - For cylinders along specific axes, specify "axis": "x", "y", or "z".
   - Keep coordinate boundaries clean and proportional (typical span -3.5 to +3.5).

4. QUANTITY & DETAIL: Create 8 to 16 distinct components so the model looks realistic, professional, and educational. Include all essential structural, moving, transmission, and fluid/electrical parts.

5. ENGINEERING MATERIALS PALETTE:
   - Structural Steel / Chassis: #2d3748, #334155, #475569
   - Polished Chrome / Shafts / Pistons: #94a3b8, #cbd5e1, #d8f8ff
   - Copper / Brass / Coils: #f59e0b, #d97706, #ff8c00
   - Active Power / Flame / High Energy: #00e5ff, #00d4ff, #ff3355, #ffcc00
   - Hydraulic Fluid / Coolant Lines: #0ea5e9, #00ff88, #22d3ee

6. COMPLETE DESCRIPTIONS: Every component MUST have a rich, informative technical description so users can inspect and learn every part.
"""

    def __init__(self):
        import os
        keys = _get_api_keys()
        self.gemini_key = os.getenv("GEMINI_API_KEY") or keys.get("gemini_api_key", "").strip()
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY") or keys.get("openrouter_api_key", "").strip()

    def generate_model(self, user_instruction: str, force_catalog: bool = False) -> ModelSpec | None:
        """
        Generate a 3D model specification from user instruction.

        AURA behaves as an AI 3D Generation Agent:
        1. Dynamic AI generation via Google Gemini (primary pipeline)
        2. Dynamic AI generation via OpenRouter (fallback)
        3. Built-in Catalog Match (for specific test fixtures / when offline)
        4. Dynamic Procedural Geometry Generator
        """
        instruction_clean = user_instruction.strip()
        if not instruction_clean:
            instruction_clean = "Generic Science & Engineering Model"

        # If forced to catalog (e.g. from preset example selector)
        if force_catalog:
            catalog_match = self._match_catalog(instruction_clean)
            if catalog_match:
                print(f"[AIModelGenerator] Loaded from catalog (forced): {catalog_match.topic}")
                return catalog_match

        # 1. Primary AI Pipeline: Google Gemini
        if self.gemini_key and len(self.gemini_key) > 8:
            spec = self._try_gemini(instruction_clean)
            if spec:
                return spec

        # 2. Secondary AI Pipeline: OpenRouter
        if self.openrouter_key and len(self.openrouter_key) > 8 and not self.openrouter_key.startswith("AQ."):
            spec = self._try_openrouter(instruction_clean)
            if spec:
                return spec

        # 3. Catalog fallback when offline or specific query matches
        catalog_match = self._match_catalog(instruction_clean)
        if catalog_match:
            print(f"[AIModelGenerator] Loaded from built-in model catalog fallback: {catalog_match.topic}")
            return catalog_match

        # 4. Procedural parametric generation fallback
        print(f"[AIModelGenerator] [PROCEDURAL] Generating procedural model for: {instruction_clean}")
        return self._generate_procedural_fallback(instruction_clean)

    def _try_gemini(self, instruction: str) -> ModelSpec | None:
        """Attempt generation using Google Gemini API (SDK or direct REST)."""
        models_to_try = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
        ]

        # 1. Direct REST request (most reliable across environments)
        import requests
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_key}"
                payload = {
                    "system_instruction": {"parts": [{"text": self.SYSTEM_PROMPT}]},
                    "contents": [{"role": "user", "parts": [{"text": instruction}]}],
                    "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
                }
                res = requests.post(url, json=payload, timeout=45)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts if "text" in p)
                        spec = self._parse_json_to_spec(text)
                        if spec and spec.components:
                            print(f"[AIModelGenerator] [OK] Dynamically generated via Gemini REST ({model_name}): {spec.topic}")
                            return spec
            except Exception as e:
                logger.warning(f"Gemini REST {model_name} error: {e}")

        # 2. SDK attempt as secondary
        if genai:
            for model_name in models_to_try:
                try:
                    client = genai.Client(api_key=self.gemini_key)
                    response = client.models.generate_content(
                        model=model_name,
                        contents=instruction,
                        config=types.GenerateContentConfig(
                            system_instruction=self.SYSTEM_PROMPT,
                            temperature=0.2,
                        ),
                    )
                    text = response.text.strip() if response.text else ""
                    spec = self._parse_json_to_spec(text)
                    if spec:
                        print(f"[AIModelGenerator] [OK] Generated via Gemini SDK ({model_name}): {spec.topic}")
                        return spec
                except Exception as e:
                    logger.warning(f"Gemini SDK {model_name} error: {e}")

        return None

    def _try_openrouter(self, instruction: str) -> ModelSpec | None:
        """Attempt generation using OpenRouter API."""
        try:
            from or_client import OpenRouterClient
            client = OpenRouterClient()
            data = client.chat_json(
                prompt=instruction,
                system=self.SYSTEM_PROMPT + "\nRespond with ONLY valid JSON.",
            )
            if isinstance(data, dict):
                spec = ModelSpec.from_json(data)
                if spec.components:
                    print(f"[AIModelGenerator] [OK] Generated via OpenRouter: {spec.topic}")
                    return spec
        except Exception as e:
            logger.warning(f"OpenRouter generation failed: {e}")
        return None

    def modify_model(self, current_spec_dict: dict, modification_instruction: str) -> ModelSpec | None:
        """
        Dynamically modifies an existing 3D model according to user instructions.
        Applies AI generation with guaranteed local parametric fallback.
        """
        prompt = (
            f"You are modifying an existing 3D educational model.\n"
            f"CURRENT MODEL JSON:\n{json.dumps(current_spec_dict)}\n\n"
            f"USER MODIFICATION INSTRUCTION: {modification_instruction}\n\n"
            f"Apply the requested changes while preserving unchanged components and structural base. "
            f"Respond with the complete updated model in valid JSON conforming to the schema."
        )
        ai_spec = self._try_gemini(prompt) or self._try_openrouter(prompt)
        if ai_spec and len(ai_spec.components) > 0:
            return ai_spec

        # Guaranteed Local Parametric Fallback
        spec_copy = json.loads(json.dumps(current_spec_dict))
        comps = spec_copy.get("components", [])
        connections = spec_copy.get("connections", [])
        low = modification_instruction.lower().strip()

        named_colors = {
            "blue": "#0284c7", "cyan": "#00d4ff", "orange": "#ff8c00", "green": "#10b981",
            "red": "#ef4444", "yellow": "#eab308", "gold": "#f59e0b", "purple": "#a855f7",
            "white": "#f8fafc", "black": "#1e293b", "gray": "#64748b",
        }

        # 1. Recolor command
        if "recolor" in low or "color" in low:
            target_color = "#00d4ff"
            for cname, chex in named_colors.items():
                if cname in low:
                    target_color = chex
                    break
            # Find matching component
            modified = False
            for c in comps:
                cname = c.get("name", "").lower()
                cid = c.get("id", "").lower()
                if cid in low or cname in low or any(word in low for word in cname.split()):
                    c["color"] = target_color
                    modified = True
            if not modified and comps:
                comps[0]["color"] = target_color

        # 2. Remove command
        elif "remove" in low or "delete" in low:
            to_remove_ids = set()
            for c in comps:
                cname = c.get("name", "").lower()
                cid = c.get("id", "").lower()
                if cid in low or any(word in low for word in cname.split() if len(word) > 3):
                    to_remove_ids.add(c["id"])
            if to_remove_ids:
                comps = [c for c in comps if c["id"] not in to_remove_ids]
                connections = [cn for cn in connections if cn.get("from_id") not in to_remove_ids and cn.get("to_id") not in to_remove_ids]
                spec_copy["components"] = comps
                spec_copy["connections"] = connections

        # 3. Add component command
        elif "add" in low:
            new_type = "cylinder" if "cylinder" in low or "coil" in low else ("sphere" if "sphere" in low or "sensor" in low else "box")
            new_id = f"added_comp_{int(time.time()) % 10000}"
            new_color = "#ff8c00"
            for cname, chex in named_colors.items():
                if cname in low: new_color = chex; break
            
            comps.append({
                "id": new_id,
                "name": modification_instruction.replace("add", "").replace("a", "").strip().title() or "Added Auxiliary Module",
                "type": new_type,
                "position": [0.0, 0.0, 1.8],
                "size": [0.8, 0.8, 0.8] if new_type == "box" else 0.5,
                "color": new_color,
                "alpha": 0.9,
                "description": f"Component added via user modification: {modification_instruction}.",
                "role": "Auxiliary Addition",
            })
            if len(comps) > 1:
                connections.append({
                    "from_id": comps[0]["id"],
                    "to_id": new_id,
                    "type": "link",
                    "color": new_color,
                    "thickness": 2.5,
                    "label": "Mechanical Interface",
                })
            spec_copy["components"] = comps
            spec_copy["connections"] = connections

        # 4. Resize / Scale command
        elif "resize" in low or "scale" in low or "bigger" in low or "smaller" in low:
            scale_factor = 0.6 if "smaller" in low else 1.4
            for c in comps:
                cname = c.get("name", "").lower()
                cid = c.get("id", "").lower()
                if cid in low or any(word in low for word in cname.split() if len(word) > 3):
                    s = c.get("size")
                    if isinstance(s, list):
                        c["size"] = [round(x * scale_factor, 2) for x in s]
                    elif isinstance(s, (int, float)):
                        c["size"] = round(s * scale_factor, 2)

        return ModelSpec.from_json(spec_copy)

    def generate_from_image(self, image_bytes: bytes, mime_type: str = "image/jpeg", instruction: str = "") -> ModelSpec | None:
        """
        Visual Understanding: converts an uploaded diagram, blueprint, or photo into a 3D ModelSpec.
        """
        import base64
        import requests
        b64_data = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            "Analyze this technical diagram or engineering reference image carefully. "
            "Identify the key components, their geometric shapes (cylinder, box, sphere, torus), "
            "their spatial arrangement, colors, and functional connections. "
            f"Build a complete 3D interactive educational ModelSpec representing this system. {instruction}"
        )

        models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        for model_name in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_key}"
                payload = {
                    "system_instruction": {"parts": [{"text": self.SYSTEM_PROMPT}]},
                    "contents": [{
                        "role": "user",
                        "parts": [
                            {"inlineData": {"mimeType": mime_type, "data": b64_data}},
                            {"text": prompt}
                        ]
                    }],
                    "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
                }
                res = requests.post(url, json=payload, timeout=60)
                if res.status_code == 200:
                    data = res.json()
                    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts if "text" in p)
                    spec = self._parse_json_to_spec(text)
                    if spec and spec.components:
                        print(f"[AIModelGenerator] [OK] Visual Understanding generated 3D Model from Image: {spec.topic}")
                        return spec
            except Exception as e:
                logger.warning(f"Image-to-3D error on {model_name}: {e}")

        # Fallback to procedural generation if vision inference fails
        topic_hint = instruction or "Technical Schematic Assembly"
        return self._generate_procedural_fallback(topic_hint)

    def generate_animation(self, current_spec_dict: dict, animation_instruction: str) -> list[dict]:
        """Dynamically generates operational animation steps for a model based on user instructions."""
        prompt = (
            f"You are designing operational animation sequences for a 3D physical system.\n"
            f"SYSTEM: {current_spec_dict.get('topic')}\n"
            f"COMPONENTS AVAILABLE: {[c.get('id') for c in current_spec_dict.get('components', [])]}\n"
            f"ANIMATION GOAL: {animation_instruction}\n\n"
            f"Generate a sequence of 3-6 logical animation steps. "
            f"Respond with JSON format: {{\"animation_steps\": [ {{\"step\": 1, \"description\": \"...\", \"affected_components\": [\"...\"], \"action\": \"pulse|rotate|highlight|move|flow\"}} ] }}"
        )
        spec = self._try_gemini(prompt)
        if spec and spec.animation_steps:
            return spec.animation_steps
        return current_spec_dict.get("animation_steps", [])

    def _parse_json_to_spec(self, text: str) -> ModelSpec | None:
        """Clean and parse JSON into a ModelSpec."""
        if not text:
            return None
        try:
            json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
            if json_match:
                text = json_match.group(1).strip()
            data = json.loads(text)
            spec = ModelSpec.from_json(data)
            if spec.components:
                return spec
        except Exception as e:
            logger.warning(f"JSON parsing error: {e}")
        return None

    def _match_catalog(self, query: str) -> ModelSpec | None:
        """Match query against built-in rich procedural engineering models with word-boundary precision."""
        low = query.lower()

        def _has_phrase(patterns: list[str]) -> bool:
            return any(bool(re.search(p, low)) for p in patterns)

        # 1. Atom Structure & Quantum Orbitals (Matching reference image aura_app.png)
        if _has_phrase([r"\batom\b", r"\batomic\b", r"\belectron orbital\b", r"\bnucleus\b", r"\bbohr model\b", r"\brutherford\b"]) and not _has_phrase([r"\bbomb\b", r"\breactor\b"]):
            return ModelSpec(
                topic="Rutherford-Bohr Atomic Structure",
                components=[
                    {"id": "nucleus_proton_1", "type": "sphere", "name": "Proton (+)", "position": [-0.18, 0.15, 0.1], "size": 0.28, "color": "#ff3355", "alpha": 0.95, "description": "Positively charged nucleon defining atomic number and nuclear mass."},
                    {"id": "nucleus_proton_2", "type": "sphere", "name": "Proton (+)", "position": [0.18, -0.15, 0.1], "size": 0.28, "color": "#ff3355", "alpha": 0.95, "description": "Positive nuclear charge providing electromagnetic attraction for orbital electrons."},
                    {"id": "nucleus_neutron_1", "type": "sphere", "name": "Neutron (0)", "position": [0.15, 0.2, -0.1], "size": 0.28, "color": "#8ffcff", "alpha": 0.9, "description": "Electrically neutral nucleon providing nuclear binding stability via strong nuclear force."},
                    {"id": "nucleus_neutron_2", "type": "sphere", "name": "Neutron (0)", "position": [-0.15, -0.2, -0.1], "size": 0.28, "color": "#8ffcff", "alpha": 0.9, "description": "Neutral nucleon preventing electrostatic proton repulsion within the core."},
                    {"id": "nucleus_force_field", "type": "sphere", "name": "Strong Nuclear Force Well", "position": [0, 0, 0], "size": 0.85, "color": "#ff8c00", "alpha": 0.28, "description": "Ultra-short-range strong fundamental force holding protons and neutrons together."},
                    {"id": "orbital_ring_1", "type": "torus", "name": "Principal Quantum Shell 1s", "position": [0, 0, 0], "size": [2.4, 0.035], "normal": [0.3, 0.4, 1.0], "color": "#00e5ff", "alpha": 0.85, "description": "Lowest energy spherical electron orbital level with high probability density."},
                    {"id": "orbital_ring_2", "type": "torus", "name": "Subshell Orbital 2p-x", "position": [0, 0, 0], "size": [2.4, 0.035], "normal": [-0.5, 0.6, 1.0], "color": "#22d3ee", "alpha": 0.85, "description": "Quantized orbital path tilted relative to nuclear axis."},
                    {"id": "orbital_ring_3", "type": "torus", "name": "Subshell Orbital 2p-y", "position": [0, 0, 0], "size": [2.4, 0.035], "normal": [0.8, -0.2, 0.6], "color": "#00ff88", "alpha": 0.85, "description": "Transverse probability shell completing electron valence cloud."},
                    {"id": "electron_1", "type": "sphere", "name": "Valence Electron 1 (-)", "position": [1.8, 0.7, -0.8], "size": 0.18, "color": "#ffcc00", "alpha": 1.0, "description": "Elementary lepton carrying negative unit charge orbiting at relativistic velocity."},
                    {"id": "electron_2", "type": "sphere", "name": "Valence Electron 2 (-)", "position": [-1.6, 1.3, 0.6], "size": 0.18, "color": "#ffcc00", "alpha": 1.0, "description": "Paired electron occupying opposite quantum spin state."},
                    {"id": "electron_3", "type": "sphere", "name": "Valence Electron 3 (-)", "position": [0.4, -1.9, 1.2], "size": 0.18, "color": "#ffcc00", "alpha": 1.0, "description": "Outer shell electron determining chemical bonding properties."},
                ],
                connections=[
                    {"from": "nucleus_proton_1", "to": "electron_1", "color": "#00e5ff", "thickness": 2, "label": "Coulomb Attraction"},
                    {"from": "nucleus_proton_2", "to": "electron_2", "color": "#22d3ee", "thickness": 2, "label": "Coulomb Attraction"},
                    {"from": "nucleus_proton_1", "to": "nucleus_neutron_1", "color": "#ff3355", "thickness": 3, "label": "Strong Nuclear Force"},
                ],
                explanation="An atom comprises a compact, extremely dense nucleus composed of positive protons and neutral neutrons bound by the strong nuclear force, surrounded by electrons in discrete quantized probability shells as visualized in the Rutherford-Bohr model.",
                animation_steps=[
                    {"step": 1, "description": "Strong nuclear force binds nucleons tightly into dense nucleus", "affected_components": ["nucleus_proton_1", "nucleus_proton_2", "nucleus_neutron_1", "nucleus_neutron_2", "nucleus_force_field"], "action": "pulse"},
                    {"step": 2, "description": "Electrons orbit along quantized wave shells at distinct phase angles", "affected_components": ["orbital_ring_1", "orbital_ring_2", "orbital_ring_3", "electron_1", "electron_2", "electron_3"], "action": "rotate"},
                    {"step": 3, "description": "Coulomb electrostatic attraction establishes quantum equilibrium", "affected_components": ["electron_1", "electron_2", "electron_3", "nucleus_proton_1"], "action": "highlight"},
                ],
            )

        # 2. Electrical Transformer
        if _has_phrase([r"\btransformer\b", r"\bprimary winding\b", r"\bsecondary winding\b", r"\bstep[- ]down\b", r"\bstep[- ]up\b"]) and not _has_phrase([r"\btransformer model\b", r"\bneural\b", r"\boptimus\b"]):
            return ModelSpec(
                topic="Electrical Transformer",
                components=[
                    {"id": "base_plate", "type": "box", "name": "Heavy Steel Bed Foundation", "position": [0, 0, -1.7], "size": [4.4, 2.2, 0.35], "color": "#2d3748", "alpha": 0.95, "description": "Rigid structural foundation supporting heavy silicon-steel core laminations and dampening 100/120 Hz magnetostrictive vibration."},
                    {"id": "core_left", "type": "cylinder", "name": "Laminated Iron Core (Primary Limb)", "position": [-1.6, 0, 0], "size": [0.45, 2.6], "color": "#ff8c00", "alpha": 0.9, "axis": "z", "description": "Grain-oriented silicon steel laminations conducting alternating magnetic flux."},
                    {"id": "core_right", "type": "cylinder", "name": "Laminated Iron Core (Secondary Limb)", "position": [1.6, 0, 0], "size": [0.45, 2.6], "color": "#ff8c00", "alpha": 0.9, "axis": "z", "description": "Secondary limb channeling flux through the step-down or step-up secondary coil."},
                    {"id": "core_top_yoke", "type": "box", "name": "Upper Magnetic Yoke Beam", "position": [0, 0, 1.3], "size": [3.6, 0.7, 0.5], "color": "#ff8c00", "alpha": 0.9, "description": "Horizontal ferromagnetic yoke closing the magnetic loop across primary and secondary limbs."},
                    {"id": "core_bot_yoke", "type": "box", "name": "Lower Magnetic Yoke Beam", "position": [0, 0, -1.3], "size": [3.6, 0.7, 0.5], "color": "#ff8c00", "alpha": 0.9, "description": "Bottom ferromagnetic return path completing the low-reluctance closed magnetic circuit."},
                    {"id": "primary_coil", "type": "cylinder", "name": "Primary Winding Coil (High Voltage)", "position": [-1.6, 0, 0], "size": [0.85, 1.6], "color": "#00d4ff", "alpha": 0.88, "axis": "z", "description": "Heavy multi-turn insulated copper winding generating magnetic flux from AC power source."},
                    {"id": "secondary_coil", "type": "cylinder", "name": "Secondary Winding Coil (Low Voltage)", "position": [1.6, 0, 0], "size": [0.75, 1.6], "color": "#ffcc00", "alpha": 0.88, "axis": "z", "description": "Insulated copper output winding in which transformed EMF is induced via Faraday's law."},
                    {"id": "cooling_fins_left", "type": "box", "name": "Radiator Cooling Fins Left", "position": [-2.5, 0, 0], "size": [0.35, 1.4, 2.0], "color": "#475569", "alpha": 0.85, "description": "Transformer oil cooling radiator dissipating I^2*R copper and core eddy current heat."},
                    {"id": "cooling_fins_right", "type": "box", "name": "Radiator Cooling Fins Right", "position": [2.5, 0, 0], "size": [0.35, 1.4, 2.0], "color": "#475569", "alpha": 0.85, "description": "Transformer oil heat dissipation radiator."},
                    {"id": "primary_bushing", "type": "cone", "name": "Primary High-Voltage Bushing", "position": [-1.6, 0, 1.8], "size": [0.28, 0.75], "color": "#8ffcff", "alpha": 0.95, "axis": "z", "description": "Shedded porcelain insulator insulating high-voltage conductor passing through grounded tank."},
                    {"id": "secondary_bushing", "type": "cone", "name": "Secondary Output Bushing", "position": [1.6, 0, 1.8], "size": [0.25, 0.65], "color": "#ff3355", "alpha": 0.95, "axis": "z", "description": "Low-voltage high-current output bushing terminal."},
                ],
                connections=[
                    {"from": "base_plate", "to": "core_bot_yoke", "color": "#2d3748", "thickness": 3, "label": "Chassis Mount"},
                    {"from": "core_bot_yoke", "to": "core_left", "color": "#ff8c00", "thickness": 4, "label": "Magnetic Circuit"},
                    {"from": "core_left", "to": "core_top_yoke", "color": "#ff8c00", "thickness": 4, "label": "Magnetic Circuit"},
                    {"from": "core_top_yoke", "to": "core_right", "color": "#ff8c00", "thickness": 4, "label": "Magnetic Circuit"},
                    {"from": "core_right", "to": "core_bot_yoke", "color": "#ff8c00", "thickness": 4, "label": "Magnetic Circuit"},
                    {"from": "primary_bushing", "to": "primary_coil", "color": "#00d4ff", "thickness": 3, "label": "Primary AC Feed"},
                    {"from": "secondary_coil", "to": "secondary_bushing", "color": "#ffcc00", "thickness": 3, "label": "Induced Output"},
                ],
                explanation="An electrical transformer transfers electrical energy between circuits via mutual electromagnetic induction. AC voltage in the primary coil creates an alternating magnetic flux in the laminated iron core loop, which links with and induces voltage in the secondary winding proportional to the turns ratio.",
                animation_steps=[
                    {"step": 1, "description": "Primary AC voltage enters through ceramic bushing and energizes primary winding", "affected_components": ["primary_bushing", "primary_coil"], "action": "pulse"},
                    {"step": 2, "description": "Alternating magnetic flux circulates continuously through the closed laminated core loop", "affected_components": ["core_left", "core_top_yoke", "core_right", "core_bot_yoke"], "action": "pulse"},
                    {"step": 3, "description": "Electromagnetic induction delivers transformed voltage to secondary bushings", "affected_components": ["secondary_coil", "secondary_bushing"], "action": "highlight"},
                ],
            )

        # 3. Electric Motor & Generator
        if _has_phrase([r"\belectric motor\b", r"\bmotor generator\b", r"\bstator\b", r"\barmature\b", r"\brotor coil\b", r"\bcommutator\b"]) or (_has_phrase([r"\bmotor\b", r"\bgenerator\b"]) and not _has_phrase([r"\bcar\b", r"\bengine\b", r"\bsearch\b", r"\bgame\b"])):
            return ModelSpec(
                topic="Industrial Electric Motor & Generator",
                components=[
                    {"id": "motor_base", "type": "box", "name": "Cast-Iron Base Pedestal", "position": [0, 0, -1.7], "size": [3.6, 2.6, 0.4], "color": "#1e293b", "alpha": 0.95, "description": "Heavy cast-iron bed plate absorbing mechanical vibration and anchoring stator housing."},
                    {"id": "stator_housing", "type": "cylinder", "name": "Cylindrical Stator Frame", "position": [0, 0, 0], "size": [1.6, 2.4], "color": "#0c3245", "alpha": 0.45, "axis": "y", "description": "Outer steel enclosure providing magnetic flux return path and holding pole shoes."},
                    {"id": "stator_n", "type": "box", "name": "North Magnetic Pole Shoe", "position": [-1.1, 0, 0], "size": [0.5, 2.0, 1.2], "color": "#ff3355", "alpha": 0.9, "description": "Electromagnet pole establishing horizontal inward B-field across the air gap."},
                    {"id": "stator_s", "type": "box", "name": "South Magnetic Pole Shoe", "position": [1.1, 0, 0], "size": [0.5, 2.0, 1.2], "color": "#00d4ff", "alpha": 0.9, "description": "Opposing pole completing the horizontal stator magnetic field."},
                    {"id": "rotor_shaft", "type": "cylinder", "name": "Precision Drive Rotor Shaft", "position": [0, 0, 0], "size": [0.22, 4.4], "color": "#cbd5e1", "alpha": 0.95, "axis": "y", "description": "Precision-ground alloy steel shaft transferring mechanical output torque."},
                    {"id": "armature_core", "type": "cylinder", "name": "Slotted Armature Core", "position": [0, 0, 0], "size": [0.85, 1.8], "color": "#ff8c00", "alpha": 0.9, "axis": "y", "description": "Laminated silicon steel rotor core containing slots for copper armature windings."},
                    {"id": "bearing_front", "type": "box", "name": "Deep-Groove Ball Bearing Front", "position": [0, -1.3, 0], "size": [0.7, 0.35, 0.7], "color": "#475569", "alpha": 0.9, "description": "Low-friction bearing supporting high radial loads on the drive end."},
                    {"id": "bearing_rear", "type": "box", "name": "Deep-Groove Ball Bearing Rear", "position": [0, 1.3, 0], "size": [0.7, 0.35, 0.7], "color": "#475569", "alpha": 0.9, "description": "Radial ball bearing on the commutator end."},
                    {"id": "commutator", "type": "cylinder", "name": "Segmented Copper Commutator", "position": [0, 1.5, 0], "size": [0.42, 0.5], "color": "#ffcc00", "alpha": 0.95, "axis": "y", "description": "Hard-drawn copper wedge segments insulated with mica, reversing current every half turn."},
                    {"id": "brush_pos", "type": "box", "name": "Positive Carbon Brush & Holder", "position": [-0.55, 1.5, 0], "size": [0.22, 0.25, 0.35], "color": "#00ff88", "alpha": 0.95, "description": "Graphite block maintaining sliding electrical contact under spring pressure."},
                    {"id": "brush_neg", "type": "box", "name": "Negative Carbon Brush & Holder", "position": [0.55, 1.5, 0], "size": [0.22, 0.25, 0.35], "color": "#00ff88", "alpha": 0.95, "description": "Return current carbon brush assembly."},
                ],
                connections=[
                    {"from": "motor_base", "to": "stator_housing", "color": "#1e293b", "thickness": 3, "label": "Chassis Mount"},
                    {"from": "stator_housing", "to": "bearing_front", "color": "#475569", "thickness": 3, "label": "End Bell"},
                    {"from": "stator_housing", "to": "bearing_rear", "color": "#475569", "thickness": 3, "label": "End Bell"},
                    {"from": "brush_pos", "to": "commutator", "color": "#00ff88", "thickness": 2, "label": "Sliding Contact"},
                    {"from": "commutator", "to": "armature_core", "color": "#ffcc00", "thickness": 3, "label": "Winding Current"},
                    {"from": "armature_core", "to": "rotor_shaft", "color": "#ff8c00", "thickness": 4, "label": "Torque Transmission"},
                ],
                explanation="An electric motor converts electrical energy into rotational kinetic energy. Current supplied through carbon brushes and the segmented commutator flows through rotor windings inside the stator magnetic field, experiencing Lorentz forces (F = I x B) that generate continuous output torque.",
                animation_steps=[
                    {"step": 1, "description": "Electric current enters via carbon brushes and commutator segments", "affected_components": ["brush_pos", "brush_neg", "commutator"], "action": "highlight"},
                    {"step": 2, "description": "Armature windings experience Lorentz force in the stator magnetic field", "affected_components": ["armature_core", "stator_n", "stator_s"], "action": "pulse"},
                    {"step": 3, "description": "Rotor shaft delivers continuous high-speed mechanical output", "affected_components": ["rotor_shaft", "bearing_front", "bearing_rear"], "action": "rotate"},
                ],
            )

        # 4. Hydraulic Brake System
        if _has_phrase([r"\bhydraulic brake\b", r"\bbrake caliper\b", r"\bmaster cylinder\b", r"\bdisc rotor\b", r"\bbrake system\b"]):
            return ModelSpec(
                topic="Automotive Hydraulic Disc Brake System",
                components=[
                    {"id": "mounting_chassis", "type": "box", "name": "Chassis Mounting Bulkhead", "position": [-2.6, 0, 0.4], "size": [0.6, 1.4, 2.4], "color": "#2d3748", "alpha": 0.95, "description": "Firewall and suspension knuckle mounting structures anchoring the brake components."},
                    {"id": "brake_pedal", "type": "box", "name": "Forged Brake Pedal & Pivot", "position": [-2.8, 0, 1.3], "size": [0.35, 0.25, 1.5], "color": "#cbd5e1", "alpha": 0.95, "description": "Driver interface applying mechanical leverage to amplify pedal effort."},
                    {"id": "push_rod", "type": "cylinder", "name": "Master Cylinder Push Rod", "position": [-2.1, 0, 0.6], "size": [0.08, 0.9], "color": "#d8f8ff", "alpha": 0.95, "axis": "x", "description": "Hardened push rod transferring amplified pedal force into the master cylinder piston."},
                    {"id": "master_cylinder", "type": "cylinder", "name": "Tandem Master Cylinder Body", "position": [-1.4, 0, 0.6], "size": [0.32, 1.2], "color": "#ff8c00", "alpha": 0.9, "axis": "x", "description": "Dual-circuit aluminum hydraulic cylinder generating fluid pressure via Pascal's law."},
                    {"id": "fluid_reservoir", "type": "box", "name": "DOT-4 Fluid Reservoir Tank", "position": [-1.4, 0, 1.3], "size": [0.9, 0.7, 0.6], "color": "#8ffcff", "alpha": 0.75, "description": "Translucent reservoir holding reserve hydraulic fluid for thermal expansion."},
                    {"id": "brake_line", "type": "cylinder", "name": "Braided Steel Hydraulic Line", "position": [0.2, 0, 0.6], "size": [0.05, 2.0], "color": "#00d4ff", "alpha": 0.9, "axis": "x", "description": "Flexible PTFE high-pressure braided stainless steel conduit transmitting fluid pressure."},
                    {"id": "caliper_body", "type": "box", "name": "Floating Brake Caliper Housing", "position": [1.8, 0, 0.6], "size": [1.1, 1.4, 1.0], "color": "#ff3355", "alpha": 0.9, "description": "Rigid ductile iron caliper straddling the disc rotor and housing opposed pistons."},
                    {"id": "caliper_piston", "type": "cylinder", "name": "Hydraulic Caliper Piston", "position": [1.6, 0.3, 0.6], "size": [0.35, 0.4], "color": "#cbd5e1", "alpha": 0.95, "axis": "y", "description": "Chromed steel piston extending under hydraulic pressure to clamp brake pads."},
                    {"id": "brake_pad_inner", "type": "box", "name": "Ceramic Brake Pad (Inner)", "position": [1.8, -0.2, 0.6], "size": [0.75, 0.15, 0.6], "color": "#ffcc00", "alpha": 0.95, "description": "High-friction composite friction lining contacting the rotating brake disc surface."},
                    {"id": "brake_pad_outer", "type": "box", "name": "Ceramic Brake Pad (Outer)", "position": [1.8, 0.2, 0.6], "size": [0.75, 0.15, 0.6], "color": "#ffcc00", "alpha": 0.95, "description": "Opposing ceramic composite pad squeezing the opposite disc rotor face."},
                    {"id": "disc_rotor", "type": "cylinder", "name": "Ventilated Cast-Iron Disc Rotor", "position": [1.8, 0, 0.1], "size": [1.5, 0.22], "color": "#cbd5e1", "alpha": 0.95, "axis": "y", "description": "Internally vented cast-iron rotor spinning with wheel, converting kinetic energy into heat."},
                    {"id": "wheel_hub", "type": "cylinder", "name": "Wheel Hub & Bearing Assembly", "position": [1.8, 0, 0.1], "size": [0.55, 0.5], "color": "#475569", "alpha": 0.95, "axis": "y", "description": "Central wheel flange carrying five hardened wheel lug studs."},
                ],
                connections=[
                    {"from": "brake_pedal", "to": "push_rod", "color": "#cbd5e1", "thickness": 3, "label": "Mechanical Force"},
                    {"from": "push_rod", "to": "master_cylinder", "color": "#ff8c00", "thickness": 3, "label": "Piston Thrust"},
                    {"from": "fluid_reservoir", "to": "master_cylinder", "color": "#8ffcff", "thickness": 2, "label": "Fluid Gravity Feed"},
                    {"from": "master_cylinder", "to": "brake_line", "color": "#00d4ff", "thickness": 4, "label": "Hydraulic Pressure (1500 PSI)"},
                    {"from": "brake_line", "to": "caliper_body", "color": "#00d4ff", "thickness": 4, "label": "Pascal Pressure"},
                    {"from": "caliper_piston", "to": "brake_pad_inner", "color": "#ff3355", "thickness": 4, "label": "Clamping Force"},
                    {"from": "brake_pad_inner", "to": "disc_rotor", "color": "#ffcc00", "thickness": 4, "label": "Friction Torque"},
                ],
                explanation="Hydraulic brakes exploit Pascal's principle: pedal force is mechanically magnified into hydraulic fluid pressure in the master cylinder. Incompressible fluid carries pressure instantly through lines to caliper pistons, squeezing friction pads against the spinning vented rotor to halt the vehicle.",
                animation_steps=[
                    {"step": 1, "description": "Driver applies foot pressure to brake pedal lever", "affected_components": ["brake_pedal", "push_rod"], "action": "move"},
                    {"step": 2, "description": "Master cylinder generates high hydraulic fluid pressure transmitted through brake line", "affected_components": ["master_cylinder", "brake_line"], "action": "pulse"},
                    {"step": 3, "description": "Caliper pistons clamp ceramic pads tightly against spinning disc rotor", "affected_components": ["caliper_piston", "brake_pad_inner", "brake_pad_outer", "disc_rotor"], "action": "highlight"},
                ],
            )

        # 5. Four-Stroke Internal Combustion Engine
        if _has_phrase([r"\bfour[- ]stroke\b", r"\binternal combustion\b", r"\b4[- ]stroke engine\b", r"\bcombustion chamber\b", r"\bcrankshaft\b", r"\bpiston engine\b"]) and not _has_phrase([r"\bjet\b", r"\bturbofan\b", r"\brocket\b", r"\bsearch\b"]):
            return ModelSpec(
                topic="Four-Stroke Internal Combustion Engine",
                components=[
                    {"id": "crankcase_block", "type": "box", "name": "Cast Engine Crankcase Block", "position": [0, 0, -1.2], "size": [2.4, 1.8, 1.4], "color": "#1e293b", "alpha": 0.92, "description": "Rigid cast iron engine block housing oil sump, main bearings, and rotating crankshaft."},
                    {"id": "cylinder_bore", "type": "cylinder", "name": "Honed Cylinder Sleeve", "position": [0, 0, 0.4], "size": [1.1, 2.2], "color": "#0c2d48", "alpha": 0.45, "axis": "z", "description": "Precision-honed cylinder bore containing combustion gas expansion."},
                    {"id": "piston_crown", "type": "cylinder", "name": "Forged Aluminum Piston Crown", "position": [0, 0, 0.9], "size": [0.95, 0.6], "color": "#ff8c00", "alpha": 0.95, "axis": "z", "description": "Lightweight forged piston transferring gas pressure from combustion into mechanical motion."},
                    {"id": "wrist_pin", "type": "cylinder", "name": "Hardened Steel Wrist Pin", "position": [0, 0, 0.9], "size": [0.18, 1.5], "color": "#cbd5e1", "alpha": 0.95, "axis": "y", "description": "Precision gudgeon pin connecting piston crown to small end of connecting rod."},
                    {"id": "connecting_rod", "type": "cylinder", "name": "Forged H-Beam Connecting Rod", "endpoints": [[0, 0, 0.9], [0.55, 0, -1.0]], "size": [0.14, 2.0], "color": "#d8f8ff", "alpha": 0.95, "description": "Forged chrome-moly H-beam rod transmitting reciprocating thrust to the crank throw."},
                    {"id": "crank_journal", "type": "sphere", "name": "Crankshaft Rod Journal Pin", "position": [0.55, 0, -1.0], "size": 0.42, "color": "#00d4ff", "alpha": 0.95, "description": "Offset crankpin rotating about crankshaft centerline."},
                    {"id": "crank_counterweight", "type": "box", "name": "Crankshaft Counterweight Cheek", "position": [-0.4, 0, -1.0], "size": [0.8, 0.35, 1.1], "color": "#475569", "alpha": 0.92, "description": "Precision counterweight balancing reciprocating piston and rod mass."},
                    {"id": "crank_main_shaft", "type": "cylinder", "name": "Crankshaft Main Drive Shaft", "position": [0, 0, -1.0], "size": [0.25, 2.6], "color": "#00d4ff", "alpha": 0.95, "axis": "y", "description": "Central rotating axle delivering shaft flywheel horsepower to transmission."},
                    {"id": "cylinder_head", "type": "box", "name": "Cylinder Head Assembly", "position": [0, 0, 2.2], "size": [2.2, 1.6, 0.6], "color": "#334155", "alpha": 0.92, "description": "Cast cylinder head enclosing combustion chamber and housing valves and spark plug."},
                    {"id": "intake_valve", "type": "cone", "name": "Intake Poppet Valve", "position": [-0.55, 0, 1.8], "size": [0.35, 0.55], "color": "#00ff88", "alpha": 0.9, "axis": "z", "description": "Cam-actuated valve opening to draw stoichiometric air-fuel charge into cylinder."},
                    {"id": "exhaust_valve", "type": "cone", "name": "Exhaust Poppet Valve", "position": [0.55, 0, 1.8], "size": [0.35, 0.55], "color": "#ff3355", "alpha": 0.9, "axis": "z", "description": "Sodium-cooled exhaust valve discharging burnt combustion gases to manifold."},
                    {"id": "spark_plug", "type": "cylinder", "name": "Iridium Spark Plug / Injector", "position": [0, 0, 2.4], "size": [0.15, 0.75], "color": "#ffcc00", "alpha": 0.98, "axis": "z", "description": "Ignites compressed charge with high-voltage spark at Top Dead Center."},
                ],
                connections=[
                    {"from": "cylinder_bore", "to": "cylinder_head", "color": "#334155", "thickness": 3, "label": "Head Gasket Seal"},
                    {"from": "spark_plug", "to": "piston_crown", "color": "#ffcc00", "thickness": 4, "label": "Combustion Flame Expansion"},
                    {"from": "piston_crown", "to": "connecting_rod", "color": "#ff8c00", "thickness": 4, "label": "Wrist Pin Thrust"},
                    {"from": "connecting_rod", "to": "crank_journal", "color": "#00d4ff", "thickness": 4, "label": "Rotational Torque"},
                    {"from": "crank_journal", "to": "crank_main_shaft", "color": "#00d4ff", "thickness": 4, "label": "Crank Throw"},
                ],
                explanation="The four-stroke Otto cycle comprises: (1) Intake: intake valve opens as piston descends, drawing in fuel-air charge; (2) Compression: both valves close as piston compresses mixture; (3) Power: spark plug fires, pushing piston downward with immense force; (4) Exhaust: exhaust valve opens as piston expels burnt gases.",
                animation_steps=[
                    {"step": 1, "description": "Intake Stroke: intake valve opens and descending piston draws in fresh charge", "affected_components": ["intake_valve", "cylinder_bore", "piston_crown"], "action": "move"},
                    {"step": 2, "description": "Power Stroke: spark plug ignites mixture driving piston down with high force", "affected_components": ["spark_plug", "piston_crown"], "action": "pulse"},
                    {"step": 3, "description": "Connecting rod and crankshaft convert linear stroke into continuous flywheel torque", "affected_components": ["connecting_rod", "crank_journal", "crank_main_shaft"], "action": "rotate"},
                ],
            )

        # 6. Warren Truss Bridge Structure
        if _has_phrase([r"\btruss bridge\b", r"\bwarren truss\b", r"\bbridge structure\b", r"\bsteel truss\b", r"\btruss\b"]):
            return ModelSpec(
                topic="Warren Steel Truss Bridge Structure",
                components=[
                    {"id": "pier_left", "type": "box", "name": "Reinforced Concrete Abutment (West)", "position": [-3.2, 0, -1.0], "size": [0.9, 2.2, 1.6], "color": "#2d3748", "alpha": 0.95, "description": "Massive concrete foundation abutment transferring vertical bridge and traffic dead/live loads into bedrock."},
                    {"id": "pier_right", "type": "box", "name": "Reinforced Concrete Abutment (East)", "position": [3.2, 0, -1.0], "size": [0.9, 2.2, 1.6], "color": "#2d3748", "alpha": 0.95, "description": "East foundation pier with expansion roller bearing assembly accommodating thermal expansion."},
                    {"id": "bottom_chord_south", "type": "cylinder", "name": "Bottom Tension Chord (South)", "endpoints": [[-3.0, -0.7, 0.0], [3.0, -0.7, 0.0]], "size": [0.1, 6.0], "color": "#00d4ff", "alpha": 0.95, "description": "Primary lower structural box girder carrying peak tension forces along bottom flange."},
                    {"id": "bottom_chord_north", "type": "cylinder", "name": "Bottom Tension Chord (North)", "endpoints": [[-3.0, 0.7, 0.0], [3.0, 0.7, 0.0]], "size": [0.1, 6.0], "color": "#00d4ff", "alpha": 0.95, "description": "Parallel lower chord carrying tensile dead and live loads."},
                    {"id": "top_chord_south", "type": "cylinder", "name": "Top Compression Chord (South)", "endpoints": [[-2.0, -0.7, 1.6], [2.0, -0.7, 1.6]], "size": [0.1, 4.0], "color": "#ff8c00", "alpha": 0.95, "description": "Upper horizontal chord subjected to heavy compressive bending forces."},
                    {"id": "top_chord_north", "type": "cylinder", "name": "Top Compression Chord (North)", "endpoints": [[-2.0, 0.7, 1.6], [2.0, 0.7, 1.6]], "size": [0.1, 4.0], "color": "#ff8c00", "alpha": 0.95, "description": "North upper compression chord preventing mid-span deflection."},
                    {"id": "roadway_deck", "type": "box", "name": "Reinforced Concrete Roadway Deck", "position": [0, 0, -0.1], "size": [6.2, 1.5, 0.2], "color": "#64748b", "alpha": 0.95, "description": "Vehicular roadway slab distributing live dynamic wheel loads to floor beams."},
                    {"id": "diagonal_web_1", "type": "cylinder", "name": "Warren Diagonal Strut 1", "endpoints": [[-3.0, -0.7, 0.0], [-2.0, -0.7, 1.6]], "size": [0.08, 2.0], "color": "#ff3355", "alpha": 0.9, "description": "Diagonal web member transferring end-shear forces directly into pier bearing."},
                    {"id": "diagonal_web_2", "type": "cylinder", "name": "Warren Diagonal Strut 2", "endpoints": [[-2.0, -0.7, 1.6], [-1.0, -0.7, 0.0]], "size": [0.07, 2.0], "color": "#00ff88", "alpha": 0.9, "description": "Tensile web strut in classic equilateral Warren truss configuration."},
                    {"id": "diagonal_web_3", "type": "cylinder", "name": "Warren Diagonal Strut 3", "endpoints": [[-1.0, -0.7, 0.0], [0.0, -0.7, 1.6]], "size": [0.07, 2.0], "color": "#ffcc00", "alpha": 0.9, "description": "Compressive web strut conveying center span shear load."},
                    {"id": "diagonal_web_4", "type": "cylinder", "name": "Warren Diagonal Strut 4", "endpoints": [[0.0, -0.7, 1.6], [1.0, -0.7, 0.0]], "size": [0.07, 2.0], "color": "#00ff88", "alpha": 0.9, "description": "Tensile diagonal load transfer member."},
                    {"id": "diagonal_web_5", "type": "cylinder", "name": "Warren Diagonal Strut 5", "endpoints": [[1.0, -0.7, 0.0], [2.0, -0.7, 1.6]], "size": [0.07, 2.0], "color": "#ffcc00", "alpha": 0.9, "description": "Compressive diagonal web strut."},
                    {"id": "diagonal_web_6", "type": "cylinder", "name": "Warren Diagonal Strut 6", "endpoints": [[2.0, -0.7, 1.6], [3.0, -0.7, 0.0]], "size": [0.08, 2.0], "color": "#ff3355", "alpha": 0.9, "description": "End diagonal strut transferring shear into east abutment."},
                    {"id": "portal_cross_strut_1", "type": "cylinder", "name": "Top Sway Portal Cross-Brace 1", "endpoints": [[-2.0, -0.7, 1.6], [-2.0, 0.7, 1.6]], "size": [0.06, 1.4], "color": "#8ffcff", "alpha": 0.9, "description": "Overhead cross girder preventing lateral torsional buckling of top chords under wind loads."},
                    {"id": "portal_cross_strut_2", "type": "cylinder", "name": "Top Sway Portal Cross-Brace 2", "endpoints": [[0.0, -0.7, 1.6], [0.0, 0.7, 1.6]], "size": [0.06, 1.4], "color": "#8ffcff", "alpha": 0.9, "description": "Midspan lateral stability tie."},
                    {"id": "portal_cross_strut_3", "type": "cylinder", "name": "Top Sway Portal Cross-Brace 3", "endpoints": [[2.0, -0.7, 1.6], [2.0, 0.7, 1.6]], "size": [0.06, 1.4], "color": "#8ffcff", "alpha": 0.9, "description": "East portal sway cross girder."},
                ],
                connections=[
                    {"from": "pier_left", "to": "bottom_chord_south", "color": "#2d3748", "thickness": 4, "label": "Fixed Abutment Bearing"},
                    {"from": "pier_right", "to": "bottom_chord_south", "color": "#2d3748", "thickness": 4, "label": "Roller Expansion Bearing"},
                    {"from": "bottom_chord_south", "to": "roadway_deck", "color": "#64748b", "thickness": 3, "label": "Floor Beam Link"},
                    {"from": "bottom_chord_south", "to": "diagonal_web_1", "color": "#ff3355", "thickness": 3, "label": "Pin Gusset Node"},
                    {"from": "diagonal_web_1", "to": "top_chord_south", "color": "#ff8c00", "thickness": 3, "label": "Apex Pin Joint"},
                    {"from": "top_chord_south", "to": "portal_cross_strut_1", "color": "#8ffcff", "thickness": 2, "label": "Wind Sway Bracing"},
                ],
                explanation="A Warren truss uses an arrangement of equilateral or isosceles triangles to distribute bending loads. Vertical gravity and live traffic loads induce compression along the top chords and tension along the bottom chords, while diagonal web members alternate between tension and compression.",
                animation_steps=[
                    {"step": 1, "description": "Vehicular live loads act downward upon the concrete deck and floor beams", "affected_components": ["roadway_deck"], "action": "pulse"},
                    {"step": 2, "description": "Top chord compresses while bottom chord tensions in pure bending equilibrium", "affected_components": ["top_chord_south", "top_chord_north", "bottom_chord_south", "bottom_chord_north"], "action": "highlight"},
                    {"step": 3, "description": "Triangular web struts convey axial shear down into bedrock abutments", "affected_components": ["diagonal_web_1", "diagonal_web_2", "diagonal_web_3", "pier_left", "pier_right"], "action": "pulse"},
                ],
            )

        # 7. Turbofan Jet Engine
        if _has_phrase([r"\bjet engine\b", r"\bturbofan\b", r"\bgas turbine\b", r"\baircraft engine\b"]):
            return ModelSpec(
                topic="High-Bypass Turbofan Jet Engine",
                components=[
                    {"id": "nacelle_cowl", "type": "cylinder", "name": "Inlet Nacelle & Bypass Cowl", "position": [0, 0, 0], "size": [1.8, 3.8], "color": "#0c2d48", "alpha": 0.35, "axis": "x", "description": "Aerodynamic outer engine casing directing incoming airflow smoothly into fan and core."},
                    {"id": "fan_hub_spinner", "type": "cone", "name": "Aerodynamic Fan Nose Spinner", "position": [1.8, 0, 0], "size": [0.45, 0.7], "color": "#cbd5e1", "alpha": 0.95, "axis": "x", "description": "Conical aerodynamic nose cone shedding ice and directing mass airflow into fan blades."},
                    {"id": "fan_blades", "type": "cylinder", "name": "Wide-Chord Titanium Fan", "position": [1.4, 0, 0], "size": [1.6, 0.35], "color": "#00d4ff", "alpha": 0.92, "axis": "x", "description": "Titanium alloy fan generating 80% of total thrust through the cold outer bypass duct."},
                    {"id": "lp_compressor", "type": "cone", "name": "Low-Pressure Compressor (Booster)", "position": [0.8, 0, 0], "size": [1.1, 0.7], "color": "#8ffcff", "alpha": 0.9, "axis": "x", "description": "First core stage compressing ambient air prior to high-pressure stages."},
                    {"id": "hp_compressor", "type": "cone", "name": "High-Pressure Compressor Drum", "position": [0.1, 0, 0], "size": [0.85, 0.7], "color": "#cbd5e1", "alpha": 0.9, "axis": "x", "description": "Multi-stage axial compressor raising pressure ratio to 40:1 entering combustor."},
                    {"id": "combustion_chamber", "type": "torus", "name": "Annular Combustion Chamber", "position": [-0.6, 0, 0], "size": [0.8, 0.25], "color": "#ff5722", "alpha": 0.92, "normal": [1, 0, 0], "description": "Continuous high-temperature combustion zone injecting and burning atomized Jet-A kerosene."},
                    {"id": "hp_turbine", "type": "cylinder", "name": "High-Pressure Turbine Stage", "position": [-1.1, 0, 0], "size": [0.85, 0.25], "color": "#ff3355", "alpha": 0.95, "axis": "x", "description": "Single-crystal nickel superalloy blades extracting energy from expanding gas to spin HP compressor."},
                    {"id": "lp_turbine", "type": "cylinder", "name": "Low-Pressure Turbine Multi-Stage", "position": [-1.5, 0, 0], "size": [1.1, 0.45], "color": "#ffcc00", "alpha": 0.95, "axis": "x", "description": "Multi-stage turbine driving the front intake fan through the central concentric spool."},
                    {"id": "central_drive_shaft", "type": "cylinder", "name": "Concentric Dual Spool Drive Shaft", "position": [0, 0, 0], "size": [0.16, 4.4], "color": "#00ff88", "alpha": 0.95, "axis": "x", "description": "Concentric inner drive shaft connecting LP turbine to the front titanium fan."},
                    {"id": "exhaust_nozzle", "type": "cone", "name": "Convergent Core Exhaust Nozzle", "position": [-2.0, 0, 0], "size": [0.95, 0.9], "color": "#d8f8ff", "alpha": 0.85, "axis": "x", "description": "Expands core exhaust gases to atmospheric pressure at supersonic velocity for thrust."},
                ],
                connections=[
                    {"from": "fan_hub_spinner", "to": "fan_blades", "color": "#cbd5e1", "thickness": 3, "label": "Hub Mount"},
                    {"from": "fan_blades", "to": "lp_compressor", "color": "#00d4ff", "thickness": 4, "label": "Air Inflow"},
                    {"from": "lp_compressor", "to": "hp_compressor", "color": "#8ffcff", "thickness": 4, "label": "Core Compression (40:1)"},
                    {"from": "hp_compressor", "to": "combustion_chamber", "color": "#ff8c00", "thickness": 4, "label": "High-P Air Feed"},
                    {"from": "combustion_chamber", "to": "hp_turbine", "color": "#ff5722", "thickness": 5, "label": "1700°C Expanding Gas"},
                    {"from": "hp_turbine", "to": "lp_turbine", "color": "#ffcc00", "thickness": 5, "label": "Thermal Gas Expansion"},
                    {"from": "lp_turbine", "to": "central_drive_shaft", "color": "#00ff88", "thickness": 4, "label": "Shaft Spool Drive"},
                    {"from": "central_drive_shaft", "to": "fan_blades", "color": "#00ff88", "thickness": 4, "label": "Direct Fan Drive"},
                    {"from": "lp_turbine", "to": "exhaust_nozzle", "color": "#d8f8ff", "thickness": 4, "label": "Jet Velocity Output"},
                ],
                explanation="In a modern high-bypass turbofan, the front titanium fan accelerates a huge mass of air through the outer bypass duct to generate the majority of thrust. Core air is compressed, ignited in the annular combustor, and expanded through turbines that power the compressors and fan.",
                animation_steps=[
                    {"step": 1, "description": "Front titanium fan ingests mass airflow, splitting into cold bypass and hot core", "affected_components": ["fan_hub_spinner", "fan_blades", "nacelle_cowl"], "action": "rotate"},
                    {"step": 2, "description": "Axial compressors raise core pressure and atomized fuel burns in annular combustor", "affected_components": ["lp_compressor", "hp_compressor", "combustion_chamber"], "action": "pulse"},
                    {"step": 3, "description": "Turbines extract thermal expansion to spin drive shafts and exit supersonic nozzle", "affected_components": ["hp_turbine", "lp_turbine", "central_drive_shaft", "exhaust_nozzle"], "action": "highlight"},
                ],
            )

        # 8. Industrial Robotic Arm / Articulated Manipulator
        if _has_phrase([r"\brobot arm\b", r"\brobotic arm\b", r"\barticulated robot\b", r"\bindustrial robot\b", r"\bmanipulator\b", r"\bgripper\b"]):
            return ModelSpec(
                topic="6-Axis Industrial Articulated Robot Arm",
                components=[
                    {"id": "pedestal_base", "type": "box", "name": "Heavy Steel Foundation Pedestal", "position": [0, 0, -1.7], "size": [2.6, 2.6, 0.4], "color": "#1e293b", "alpha": 0.95, "description": "Rigid machine foundation bolted to concrete floor absorbing dynamic moment loads."},
                    {"id": "waist_turret", "type": "cylinder", "name": "Axis 1: Azimuth Rotating Turntable", "position": [0, 0, -1.2], "size": [0.8, 0.6], "color": "#ff8c00", "alpha": 0.95, "axis": "z", "description": "Precision cycloidal drive rotating the entire manipulator 360 degrees in azimuth."},
                    {"id": "shoulder_joint", "type": "box", "name": "Axis 2: Shoulder Pitch Joint", "position": [0, 0, -0.6], "size": [1.0, 1.0, 0.8], "color": "#334155", "alpha": 0.95, "description": "High-torque servo actuator executing shoulder pitch articulation."},
                    {"id": "lower_boom", "type": "cylinder", "name": "Primary Upper Boom Arm", "endpoints": [[0, 0, -0.6], [0.8, 0, 0.8]], "size": [0.22, 2.0], "color": "#cbd5e1", "alpha": 0.95, "description": "Cast aluminum structural boom carrying electric servo harnesses."},
                    {"id": "elbow_joint", "type": "box", "name": "Axis 3: Elbow Articulation Joint", "position": [0.8, 0, 0.8], "size": [0.75, 0.75, 0.7], "color": "#ff8c00", "alpha": 0.95, "description": "Compact harmonic drive motor executing forearm elevation."},
                    {"id": "forearm_link", "type": "cylinder", "name": "Structural Forearm Link", "endpoints": [[0.8, 0, 0.8], [2.2, 0, 0.6]], "size": [0.18, 1.8], "color": "#00d4ff", "alpha": 0.92, "description": "Torsion-resistant tubular link carrying wrist servomotors."},
                    {"id": "wrist_assembly", "type": "sphere", "name": "Axes 4-5-6: 3-Axis Spherical Wrist", "position": [2.2, 0, 0.6], "size": 0.38, "color": "#ffcc00", "alpha": 0.95, "description": "Triple-roll wrist executing pitch, yaw, and tool flange roll motions."},
                    {"id": "gripper_body", "type": "box", "name": "Pneumatic End-Effector Tool Flange", "position": [2.6, 0, 0.6], "size": [0.45, 0.6, 0.4], "color": "#475569", "alpha": 0.95, "description": "ISO mounting flange holding double-acting pneumatic clamp cylinder."},
                    {"id": "finger_left", "type": "box", "name": "Parallel Gripper Jaw (Left)", "position": [2.9, -0.22, 0.6], "size": [0.35, 0.1, 0.25], "color": "#00ff88", "alpha": 0.95, "description": "Hardened urethane-coated parallel gripping finger."},
                    {"id": "finger_right", "type": "box", "name": "Parallel Gripper Jaw (Right)", "position": [2.9, 0.22, 0.6], "size": [0.35, 0.1, 0.25], "color": "#00ff88", "alpha": 0.95, "description": "Opposing synchronous clamping jaw."},
                ],
                connections=[
                    {"from": "pedestal_base", "to": "waist_turret", "color": "#1e293b", "thickness": 4, "label": "Thrust Bearing"},
                    {"from": "waist_turret", "to": "shoulder_joint", "color": "#ff8c00", "thickness": 4, "label": "Axis 1 Drive"},
                    {"from": "shoulder_joint", "to": "lower_boom", "color": "#334155", "thickness": 4, "label": "Axis 2 Shoulder Pitch"},
                    {"from": "lower_boom", "to": "elbow_joint", "color": "#cbd5e1", "thickness": 4, "label": "Boom Link"},
                    {"from": "elbow_joint", "to": "forearm_link", "color": "#ff8c00", "thickness": 3, "label": "Axis 3 Elbow Pitch"},
                    {"from": "forearm_link", "to": "wrist_assembly", "color": "#00d4ff", "thickness": 3, "label": "Forearm Conduit"},
                    {"from": "wrist_assembly", "to": "gripper_body", "color": "#ffcc00", "thickness": 3, "label": "Tool Flange ISO 9409"},
                    {"from": "gripper_body", "to": "finger_left", "color": "#00ff88", "thickness": 2, "label": "Pneumatic Clamping"},
                    {"from": "gripper_body", "to": "finger_right", "color": "#00ff88", "thickness": 2, "label": "Pneumatic Clamping"},
                ],
                explanation="A 6-DOF articulated robotic arm mirrors human kinematics: the waist, shoulder, and elbow position the wrist in 3D cartesian coordinates (X, Y, Z), while the 3-axis spherical wrist precisely orients the end-effector gripper tool in Roll, Pitch, and Yaw angles.",
                animation_steps=[
                    {"step": 1, "description": "Waist turret rotates azimuth while shoulder and elbow position the manipulator", "affected_components": ["waist_turret", "shoulder_joint", "lower_boom", "elbow_joint"], "action": "rotate"},
                    {"step": 2, "description": "Wrist executes precision angular orientation", "affected_components": ["forearm_link", "wrist_assembly"], "action": "move"},
                    {"step": 3, "description": "Pneumatic gripper jaws clamp payload securely", "affected_components": ["gripper_body", "finger_left", "finger_right"], "action": "highlight"},
                ],
            )

        # 9. Wind Turbine Renewable Energy System
        if _has_phrase([r"\bwind turbine\b", r"\bwind power\b", r"\bwind generator\b", r"\bwind blade\b"]):
            return ModelSpec(
                topic="Utility-Scale Horizontal-Axis Wind Turbine",
                components=[
                    {"id": "foundation_pad", "type": "box", "name": "Reinforced Concrete Gravity Base", "position": [0, 0, -1.8], "size": [3.6, 3.6, 0.4], "color": "#2d3748", "alpha": 0.95, "description": "Sub-surface concrete slab counteracting massive wind overturning moments."},
                    {"id": "tower_base", "type": "cylinder", "name": "Tubular Steel Tower (Lower)", "position": [0, 0, -1.6], "size": [0.55, 1.4], "color": "#cbd5e1", "alpha": 0.95, "axis": "z", "description": "High-strength rolled steel shell anchored with prestressed foundation bolts."},
                    {"id": "tower_upper", "type": "cylinder", "name": "Tapered Structural Tower (Upper)", "position": [0, 0, -0.2], "size": [0.42, 1.6], "color": "#cbd5e1", "alpha": 0.95, "axis": "z", "description": "Tapered column elevating the rotor into high-velocity boundary layer wind streams."},
                    {"id": "yaw_bearing", "type": "torus", "name": "Active Yaw Drive Slewing Ring", "position": [0, 0, 1.35], "size": [0.45, 0.08], "color": "#ff8c00", "alpha": 0.95, "description": "Gear drive steering the nacelle into the wind direction to eliminate yaw error."},
                    {"id": "nacelle_housing", "type": "box", "name": "Machine Nacelle Enclosure", "position": [-0.3, 0, 1.55], "size": [1.8, 0.8, 0.7], "color": "#334155", "alpha": 0.92, "description": "Aerodynamic nacelle enclosing main shaft, planetary step-up gearbox, and generator."},
                    {"id": "rotor_hub", "type": "cone", "name": "Aerodynamic Rotor Hub Spinner", "position": [0.75, 0, 1.55], "size": [0.45, 0.6], "color": "#00d4ff", "alpha": 0.95, "axis": "x", "description": "Cast steel rotor hub with internal hydraulic pitch bearings for each blade."},
                    {"id": "blade_1", "type": "box", "name": "Composite Airfoil Blade 1 (0°)", "position": [0.75, 0, 2.6], "size": [0.22, 0.08, 2.1], "color": "#d8f8ff", "alpha": 0.95, "description": "Fiberglass/carbon aerodynamic lifting surface producing rotational aerodynamic torque."},
                    {"id": "blade_2", "type": "box", "name": "Composite Airfoil Blade 2 (120°)", "position": [0.75, -0.9, 1.0], "size": [0.22, 0.08, 2.1], "color": "#d8f8ff", "alpha": 0.95, "description": "Balanced aerodynamic lifting blade."},
                    {"id": "blade_3", "type": "box", "name": "Composite Airfoil Blade 3 (240°)", "position": [0.75, 0.9, 1.0], "size": [0.22, 0.08, 2.1], "color": "#d8f8ff", "alpha": 0.95, "description": "Balanced aerodynamic lifting blade."},
                    {"id": "low_speed_shaft", "type": "cylinder", "name": "Forged Low-Speed Main Shaft", "position": [0.3, 0, 1.55], "size": [0.15, 0.8], "color": "#00d4ff", "alpha": 0.95, "axis": "x", "description": "Rigid forged main drive shaft rotating at 10-18 RPM."},
                    {"id": "stepup_gearbox", "type": "box", "name": "Planetary Step-Up Gearbox (1:100)", "position": [-0.3, 0, 1.55], "size": [0.65, 0.6, 0.55], "color": "#ff8c00", "alpha": 0.95, "description": "Multi-stage planetary transmission multiplying shaft speed up to 1800 RPM."},
                    {"id": "ac_generator", "type": "cylinder", "name": "Doubly-Fed Induction Generator", "position": [-0.85, 0, 1.55], "size": [0.32, 0.6], "color": "#00ff88", "alpha": 0.95, "axis": "x", "description": "3-phase 690V generator converting mechanical shaft work into grid electricity."},
                ],
                connections=[
                    {"from": "foundation_pad", "to": "tower_base", "color": "#2d3748", "thickness": 4, "label": "Anchor Bolts"},
                    {"from": "tower_base", "to": "tower_upper", "color": "#cbd5e1", "thickness": 4, "label": "Tower Flange"},
                    {"from": "tower_upper", "to": "yaw_bearing", "color": "#ff8c00", "thickness": 3, "label": "Yaw Axis"},
                    {"from": "yaw_bearing", "to": "nacelle_housing", "color": "#334155", "thickness": 3, "label": "Bedplate"},
                    {"from": "rotor_hub", "to": "blade_1", "color": "#00d4ff", "thickness": 3, "label": "Pitch Bearing"},
                    {"from": "rotor_hub", "to": "low_speed_shaft", "color": "#00d4ff", "thickness": 4, "label": "Rotor Torque"},
                    {"from": "low_speed_shaft", "to": "stepup_gearbox", "color": "#ff8c00", "thickness": 4, "label": "Input Speed (15 RPM)"},
                    {"from": "stepup_gearbox", "to": "ac_generator", "color": "#00ff88", "thickness": 3, "label": "Output Speed (1800 RPM)"},
                ],
                explanation="A wind turbine extracts kinetic energy from the wind via aerodynamic lift on three composite airfoil blades. The slowly spinning rotor hub drives a low-speed main shaft, which is multiplied roughly 100-fold by a planetary gearbox to spin a generator that feeds synchronized AC electricity to the grid.",
                animation_steps=[
                    {"step": 1, "description": "Wind flow induces aerodynamic lift on the three pitch-regulated blades", "affected_components": ["blade_1", "blade_2", "blade_3", "rotor_hub"], "action": "rotate"},
                    {"step": 2, "description": "Low-speed shaft transfers torque through the planetary step-up gearbox", "affected_components": ["low_speed_shaft", "stepup_gearbox"], "action": "pulse"},
                    {"step": 3, "description": "Generator outputs synchronized 3-phase AC power down tower busbars to grid", "affected_components": ["ac_generator", "tower_upper", "tower_base"], "action": "highlight"},
                ],
            )

        # 10. Gantry Crane / Overhead Hoist System
        if _has_phrase([r"\bgantry crane\b", r"\boverhead crane\b", r"\bhoist\b", r"\bcrane\b"]):
            return ModelSpec(
                topic="Industrial Heavy Gantry Crane System",
                components=[
                    {"id": "runway_rail_west", "type": "cylinder", "name": "Ground Runway Rail (West)", "endpoints": [[-2.4, -2.2, -1.7], [-2.4, 2.2, -1.7]], "size": [0.12, 4.4], "color": "#2d3748", "alpha": 0.95, "description": "Heavy steel crane rail anchored to concrete runway slab."},
                    {"id": "runway_rail_east", "type": "cylinder", "name": "Ground Runway Rail (East)", "endpoints": [[2.4, -2.2, -1.7], [2.4, 2.2, -1.7]], "size": [0.12, 4.4], "color": "#2d3748", "alpha": 0.95, "description": "Parallel ground travel track rail."},
                    {"id": "leg_a_west_1", "type": "cylinder", "name": "West A-Frame Structural Leg 1", "endpoints": [[-2.4, -1.4, -1.7], [-2.4, 0.0, 1.6]], "size": [0.14, 3.4], "color": "#ff8c00", "alpha": 0.95, "description": "Tubular steel A-frame vertical support leg."},
                    {"id": "leg_a_west_2", "type": "cylinder", "name": "West A-Frame Structural Leg 2", "endpoints": [[-2.4, 1.4, -1.7], [-2.4, 0.0, 1.6]], "size": [0.14, 3.4], "color": "#ff8c00", "alpha": 0.95, "description": "Opposing A-frame leg forming rigid vertical bipod."},
                    {"id": "leg_a_east_1", "type": "cylinder", "name": "East A-Frame Structural Leg 1", "endpoints": [[2.4, -1.4, -1.7], [2.4, 0.0, 1.6]], "size": [0.14, 3.4], "color": "#ff8c00", "alpha": 0.95, "description": "East A-frame vertical support leg."},
                    {"id": "leg_a_east_2", "type": "cylinder", "name": "East A-Frame Structural Leg 2", "endpoints": [[2.4, 1.4, -1.7], [2.4, 0.0, 1.6]], "size": [0.14, 3.4], "color": "#ff8c00", "alpha": 0.95, "description": "East bipod leg transmitting overhead crane loads."},
                    {"id": "leg_cross_brace_west", "type": "cylinder", "name": "West Leg Horizontal Tie Strut", "endpoints": [[-2.4, -0.8, -0.2], [-2.4, 0.8, -0.2]], "size": [0.08, 1.6], "color": "#cbd5e1", "alpha": 0.9, "description": "Horizontal tie preventing leg spread under heavy hoist loads."},
                    {"id": "leg_cross_brace_east", "type": "cylinder", "name": "East Leg Horizontal Tie Strut", "endpoints": [[2.4, -0.8, -0.2], [2.4, 0.8, -0.2]], "size": [0.08, 1.6], "color": "#cbd5e1", "alpha": 0.9, "description": "Horizontal tie beam."},
                    {"id": "main_box_girder", "type": "box", "name": "Main Overhead Box Girder Beam", "position": [0, 0, 1.6], "size": [5.2, 0.7, 0.45], "color": "#00d4ff", "alpha": 0.95, "description": "High-rigidity welded steel box girder spanning between west and east A-frames."},
                    {"id": "traveling_trolley", "type": "box", "name": "Motorized Hoist Trolley", "position": [0.3, 0, 1.9], "size": [0.9, 0.8, 0.4], "color": "#ffcc00", "alpha": 0.95, "description": "Electric trolley traversing horizontally along top flange of main bridge girder."},
                    {"id": "hoist_drum", "type": "cylinder", "name": "Grooved Wire Rope Hoist Drum", "position": [0.3, 0, 1.9], "size": [0.28, 0.6], "color": "#ff3355", "alpha": 0.95, "axis": "x", "description": "Motorized grooved drum spooling high-tensile wire rope."},
                    {"id": "hoist_wire_rope", "type": "cylinder", "name": "Multi-Part Wire Rope Fall", "endpoints": [[0.3, 0, 1.9], [0.3, 0, 0.2]], "size": [0.045, 1.7], "color": "#d8f8ff", "alpha": 0.95, "description": "High-tensile galvanized steel wire rope reeved through sheave pulleys."},
                    {"id": "hook_block", "type": "cone", "name": "Heavy Forged Swivel Crane Hook", "position": [0.3, 0, 0.0], "size": [0.32, 0.4], "color": "#ff3355", "alpha": 0.98, "axis": "z", "description": "Heavy-duty forged alloy steel lifting hook with thrust bearing swivel."},
                ],
                connections=[
                    {"from": "runway_rail_west", "to": "leg_a_west_1", "color": "#2d3748", "thickness": 4, "label": "Travel Bogie"},
                    {"from": "leg_a_west_1", "to": "main_box_girder", "color": "#ff8c00", "thickness": 4, "label": "Apex Moment Joint"},
                    {"from": "leg_a_east_1", "to": "main_box_girder", "color": "#ff8c00", "thickness": 4, "label": "Apex Moment Joint"},
                    {"from": "main_box_girder", "to": "traveling_trolley", "color": "#00d4ff", "thickness": 3, "label": "Trolley Rail Track"},
                    {"from": "traveling_trolley", "to": "hoist_wire_rope", "color": "#ffcc00", "thickness": 3, "label": "Cable Reevings"},
                    {"from": "hoist_wire_rope", "to": "hook_block", "color": "#ff3355", "thickness": 3, "label": "Lifting Attachment"},
                ],
                explanation="A gantry crane uses rigid A-frame legs supported on ground travel rails to elevate an overhead box girder. A motorized trolley traverses the girder span while an electric wire rope hoist drum raises or lowers multi-ton industrial loads via a heavy hook block.",
                animation_steps=[
                    {"step": 1, "description": "Entire gantry frame travels longitudinally along ground runway tracks", "affected_components": ["runway_rail_west", "runway_rail_east", "leg_a_west_1", "leg_a_east_1"], "action": "move"},
                    {"step": 2, "description": "Motorized trolley traverses horizontally along main bridge girder", "affected_components": ["traveling_trolley", "main_box_girder"], "action": "move"},
                    {"step": 3, "description": "Electric hoist drum spools wire rope to elevate the heavy forged hook block", "affected_components": ["hoist_drum", "hoist_wire_rope", "hook_block"], "action": "pulse"},
                ],
            )

        # 11. Human Heart Anatomy & Circulatory Dynamics
        if _has_phrase([r"\bhuman heart\b", r"\bheart anatomy\b", r"\bcardiac\b", r"\bventricle\b", r"\batrium\b", r"\baorta\b"]) or (_has_phrase([r"\bheart\b"]) and not _has_phrase([r"\battack\b", r"\brate\b"])):
            return ModelSpec(
                topic="Human Heart Anatomy & Circulatory Dynamics",
                components=[
                    {"id": "left_ventricle", "type": "sphere", "name": "Left Ventricle (Systemic Pump)", "position": [0.55, 0, -0.6], "size": 1.1, "color": "#dc2626", "alpha": 0.95, "description": "Thick-walled muscular chamber pumping oxygenated blood to the entire body at high arterial pressure."},
                    {"id": "right_ventricle", "type": "sphere", "name": "Right Ventricle (Pulmonary Pump)", "position": [-0.55, 0, -0.6], "size": 0.95, "color": "#2563eb", "alpha": 0.95, "description": "Muscular chamber pumping deoxygenated blood through the pulmonary valve into the lungs."},
                    {"id": "left_atrium", "type": "sphere", "name": "Left Atrium", "position": [0.5, 0, 0.6], "size": 0.8, "color": "#ef4444", "alpha": 0.92, "description": "Receives freshly oxygenated blood returning from the pulmonary veins."},
                    {"id": "right_atrium", "type": "sphere", "name": "Right Atrium", "position": [-0.5, 0, 0.6], "size": 0.8, "color": "#3b82f6", "alpha": 0.92, "description": "Receives deoxygenated venous return from superior and inferior vena cavae."},
                    {"id": "aorta_arch", "type": "torus", "name": "Aortic Arch & Ascending Aorta", "position": [0.1, 0, 1.4], "size": [0.85, 0.22], "normal": [0, 1, 0], "color": "#f87171", "alpha": 0.96, "description": "Primary high-pressure systemic artery distributing oxygenated blood throughout the body."},
                    {"id": "pulmonary_trunk", "type": "cylinder", "name": "Pulmonary Artery Trunk", "endpoints": [[-0.2, 0, 0.4], [-0.5, 0, 1.3]], "size": [0.22, 1.1], "color": "#60a5fa", "alpha": 0.95, "description": "Arterial vessel branching left and right to transport blood to the alveolar capillary beds."},
                    {"id": "superior_vena_cava", "type": "cylinder", "name": "Superior Vena Cava", "position": [-0.85, 0, 1.1], "size": [0.22, 1.2], "color": "#1d4ed8", "alpha": 0.95, "axis": "z", "description": "Large vein returning deoxygenated blood from head, neck, and upper limbs into right atrium."},
                    {"id": "mitral_valve", "type": "cylinder", "name": "Bicuspid Mitral Valve", "position": [0.55, 0, 0.0], "size": [0.35, 0.12], "color": "#fef08a", "alpha": 0.95, "axis": "z", "description": "Dual-cusp atrioventricular valve preventing backflow into left atrium during ventricular systole."},
                    {"id": "tricuspid_valve", "type": "cylinder", "name": "Tricuspid Valve", "position": [-0.55, 0, 0.0], "size": [0.35, 0.12], "color": "#fef08a", "alpha": 0.95, "axis": "z", "description": "Three-cusp valve preventing ventricular regurgitation into the right atrium."},
                    {"id": "septum_wall", "type": "box", "name": "Interventricular Muscular Septum", "position": [0, 0, -0.6], "size": [0.2, 1.2, 1.6], "color": "#b91c1c", "alpha": 0.95, "description": "Dense muscular dividing wall separating systemic oxygenated blood from pulmonary deoxygenated blood."},
                ],
                connections=[
                    {"from": "superior_vena_cava", "to": "right_atrium", "color": "#1d4ed8", "thickness": 4, "label": "Venous Return"},
                    {"from": "right_atrium", "to": "tricuspid_valve", "color": "#3b82f6", "thickness": 3, "label": "Atrial Inflow"},
                    {"from": "tricuspid_valve", "to": "right_ventricle", "color": "#2563eb", "thickness": 4, "label": "Diastolic Filling"},
                    {"from": "right_ventricle", "to": "pulmonary_trunk", "color": "#60a5fa", "thickness": 4, "label": "Pulmonary Ejection"},
                    {"from": "left_atrium", "to": "mitral_valve", "color": "#ef4444", "thickness": 3, "label": "Oxygenated Feed"},
                    {"from": "mitral_valve", "to": "left_ventricle", "color": "#dc2626", "thickness": 4, "label": "Ventricular Filling"},
                    {"from": "left_ventricle", "to": "aorta_arch", "color": "#f87171", "thickness": 5, "label": "Aortic Systolic Ejection (120 mmHg)"},
                ],
                explanation="The human heart operates as a synchronized dual-pump. The right side receives oxygen-depleted venous blood and pumps it into the lungs for re-oxygenation. The left side receives oxygen-rich pulmonary blood and propels it through the aortic arch under high pressure into systemic circulation.",
                animation_steps=[
                    {"step": 1, "description": "Atrial Systole: Atria contract, filling both ventricles across mitral and tricuspid valves", "affected_components": ["right_atrium", "left_atrium", "mitral_valve", "tricuspid_valve"], "action": "pulse"},
                    {"step": 2, "description": "Ventricular Systole: Thick ventricular muscles contract, closing AV valves", "affected_components": ["left_ventricle", "right_ventricle", "septum_wall"], "action": "highlight"},
                    {"step": 3, "description": "High-pressure blood surges simultaneously into the aorta and pulmonary artery", "affected_components": ["aorta_arch", "pulmonary_trunk"], "action": "pulse"},
                ],
            )

        # 12. Plant Cell Anatomy & Photosynthesis Organelles
        if _has_phrase([r"\bplant cell\b", r"\bplant anatomy\b", r"\bchloroplast\b", r"\bvacuole\b", r"\bcell wall\b"]):
            return ModelSpec(
                topic="Plant Cell Anatomy & Photosynthetic Machinery",
                components=[
                    {"id": "cell_wall", "type": "box", "name": "Rigid Cellulose Cell Wall", "position": [0, 0, 0], "size": [3.6, 2.8, 1.8], "color": "#15803d", "alpha": 0.35, "description": "Rigid outer layer composed of cellulose microfibrils providing structural turgor support."},
                    {"id": "cell_membrane", "type": "box", "name": "Semi-Permeable Cell Membrane", "position": [0, 0, 0], "size": [3.3, 2.5, 1.6], "color": "#4ade80", "alpha": 0.25, "description": "Phospholipid bilayer regulating molecular transport in and out of cytoplasm."},
                    {"id": "central_vacuole", "type": "sphere", "name": "Central Turgor Vacuole", "position": [0.4, -0.2, 0.0], "size": 1.1, "color": "#38bdf8", "alpha": 0.65, "description": "Large single fluid reservoir storing cell sap, maintaining internal hydrostatic turgor pressure."},
                    {"id": "cell_nucleus", "type": "sphere", "name": "Cell Nucleus & Nucleolus", "position": [-0.9, 0.6, 0.2], "size": 0.55, "color": "#8b5cf6", "alpha": 0.95, "description": "Membrane-bound control center housing genomic DNA and coordinating cellular transcription."},
                    {"id": "chloroplast_1", "type": "sphere", "name": "Photosynthetic Chloroplast Alpha", "position": [-1.1, -0.6, 0.3], "size": 0.38, "color": "#22c55e", "alpha": 0.95, "description": "Chlorophyll-rich double-membrane organelle converting light, water, and CO2 into glucose."},
                    {"id": "chloroplast_2", "type": "sphere", "name": "Photosynthetic Chloroplast Beta", "position": [1.1, 0.6, -0.2], "size": 0.38, "color": "#22c55e", "alpha": 0.95, "description": "Photosynthetic thylakoid site executing light-dependent reactions."},
                    {"id": "chloroplast_3", "type": "sphere", "name": "Photosynthetic Chloroplast Gamma", "position": [0.8, -0.8, 0.3], "size": 0.38, "color": "#22c55e", "alpha": 0.95, "description": "Synthesizes ATP and NADPH during Calvin cycle carbon fixation."},
                    {"id": "mitochondria_1", "type": "cylinder", "name": "Cellular Mitochondrion", "position": [-0.4, 0.8, -0.3], "size": [0.18, 0.5], "color": "#f97316", "alpha": 0.95, "axis": "x", "description": "Powerhouse organelle generating ATP through oxidative phosphorylation."},
                    {"id": "golgi_apparatus", "type": "box", "name": "Golgi Vesicle Complex", "position": [-0.2, -0.7, -0.3], "size": [0.6, 0.3, 0.25], "color": "#fbbf24", "alpha": 0.92, "description": "Membranous cisternae packaging and secreting polysaccharides for cell wall expansion."},
                ],
                connections=[
                    {"from": "cell_wall", "to": "cell_membrane", "color": "#15803d", "thickness": 3, "label": "Turgor Interface"},
                    {"from": "central_vacuole", "to": "cell_wall", "color": "#38bdf8", "thickness": 3, "label": "Hydrostatic Pressure"},
                    {"from": "chloroplast_1", "to": "central_vacuole", "color": "#22c55e", "thickness": 2, "label": "Sugar Storage"},
                    {"from": "cell_nucleus", "to": "chloroplast_1", "color": "#8b5cf6", "thickness": 2, "label": "Genetic Regulation"},
                ],
                explanation="A plant cell possesses unique structural adaptations compared to animal cells: a rigid cellulose cell wall preventing osmotic lysis, a large central vacuole sustaining mechanical turgor pressure, and multiple green chloroplasts carrying out oxygenic photosynthesis.",
                animation_steps=[
                    {"step": 1, "description": "Central vacuole absorbs water, establishing outward turgor pressure against cell wall", "affected_components": ["central_vacuole", "cell_wall"], "action": "pulse"},
                    {"step": 2, "description": "Chloroplasts harvest photon energy to fix carbon into starch within thylakoid disks", "affected_components": ["chloroplast_1", "chloroplast_2", "chloroplast_3"], "action": "highlight"},
                    {"step": 3, "description": "Mitochondria convert carbohydrate stores into high-energy ATP across inner cristae", "affected_components": ["mitochondria_1", "cell_nucleus"], "action": "pulse"},
                ],
            )

        # 13. Solar System Planetary Orbits
        if _has_phrase([r"\bsolar system\b", r"\bplanet\b", r"\bplanets\b", r"\borbit\b", r"\bsun\b"]) and not _has_phrase([r"\bsolar panel\b", r"\bsunflower\b"]):
            return ModelSpec(
                topic="Solar System Heliocentric Orbital Mechanics",
                components=[
                    {"id": "sun_core", "type": "sphere", "name": "The Sun (Sol G2V Star)", "position": [0, 0, 0], "size": 0.9, "color": "#facc15", "alpha": 0.98, "description": "G-type main-sequence star containing 99.86% of the solar system's mass and driving orbits via gravity."},
                    {"id": "orbit_mercury", "type": "torus", "name": "Mercury Orbital Path", "position": [0, 0, 0], "size": [1.4, 0.02], "color": "#94a3b8", "alpha": 0.7, "description": "Elliptical orbit closest to the Sun with high orbital velocity of 47.4 km/s."},
                    {"id": "planet_mercury", "type": "sphere", "name": "Mercury", "position": [1.4, 0, 0], "size": 0.14, "color": "#9ca3af", "alpha": 1.0, "description": "Smallest terrestrial planet with cratered silicate surface and no atmosphere."},
                    {"id": "orbit_venus", "type": "torus", "name": "Venus Orbital Path", "position": [0, 0, 0], "size": [2.1, 0.02], "color": "#fde047", "alpha": 0.7, "description": "Nearly circular retrograde rotation orbit inside habitable zone."},
                    {"id": "planet_venus", "type": "sphere", "name": "Venus", "position": [0, 2.1, 0], "size": 0.24, "color": "#eab308", "alpha": 1.0, "description": "Terrestrial planet with runaway CO2 greenhouse effect and sulfuric acid clouds."},
                    {"id": "orbit_earth", "type": "torus", "name": "Earth Orbital Path (1.0 AU)", "position": [0, 0, 0], "size": [2.8, 0.025], "color": "#38bdf8", "alpha": 0.8, "description": "Habitable zone orbit defining one astronomical unit (149.6 million km)."},
                    {"id": "planet_earth", "type": "sphere", "name": "Earth (Terra)", "position": [-2.8, 0, 0], "size": 0.26, "color": "#0284c7", "alpha": 1.0, "description": "Liquid water ocean world supporting biosphere with nitrogen-oxygen atmosphere."},
                    {"id": "earth_moon", "type": "sphere", "name": "The Moon (Luna)", "position": [-2.45, 0, 0.25], "size": 0.08, "color": "#e2e8f0", "alpha": 1.0, "description": "Tidally locked satellite causing ocean tides and stabilizing Earth's axial tilt."},
                    {"id": "orbit_mars", "type": "torus", "name": "Mars Orbital Path", "position": [0, 0, 0], "size": [3.6, 0.02], "color": "#ef4444", "alpha": 0.7, "description": "Eccentric orbit outside Earth possessing thin carbon dioxide atmosphere."},
                    {"id": "planet_mars", "type": "sphere", "name": "Mars", "position": [0, -3.6, 0], "size": 0.18, "color": "#dc2626", "alpha": 1.0, "description": "Red planet characterized by iron oxide regolith, Olympus Mons volcano, and polar ice caps."},
                    {"id": "orbit_jupiter", "type": "torus", "name": "Jupiter Orbital Path", "position": [0, 0, 0], "size": [4.6, 0.03], "color": "#fb923c", "alpha": 0.75, "description": "Outer gas giant orbital boundary separating asteroid belt from Jovian system."},
                    {"id": "planet_jupiter", "type": "sphere", "name": "Jupiter (Gas Giant)", "position": [3.2, 3.2, 0], "size": 0.52, "color": "#f97316", "alpha": 1.0, "description": "Massive hydrogen-helium gas giant harboring Great Red Spot and protecting inner solar system from cometary impacts."},
                ],
                connections=[
                    {"from": "sun_core", "to": "planet_mercury", "color": "#facc15", "thickness": 2, "label": "Gravitational Attraction"},
                    {"from": "sun_core", "to": "planet_earth", "color": "#facc15", "thickness": 2, "label": "Gravitational Attraction"},
                    {"from": "planet_earth", "to": "earth_moon", "color": "#38bdf8", "thickness": 2, "label": "Lunar Orbit"},
                    {"from": "sun_core", "to": "planet_jupiter", "color": "#facc15", "thickness": 2, "label": "Gravitational Attraction"},
                ],
                explanation="The solar system is governed by Newton's law of universal gravitation and Kepler's laws of planetary motion. Planets travel along elliptical heliocentric orbits with velocities inversely proportional to their distance from the central mass of the Sun.",
                animation_steps=[
                    {"step": 1, "description": "Inner terrestrial planets complete high-speed orbits in the solar gravitational well", "affected_components": ["planet_mercury", "planet_venus", "planet_earth", "earth_moon"], "action": "rotate"},
                    {"step": 2, "description": "Outer planets maintain stable low-velocity harmonic orbits", "affected_components": ["planet_mars", "planet_jupiter"], "action": "rotate"},
                    {"step": 3, "description": "Solar radiation and gravitational equilibrium define the solar system architecture", "affected_components": ["sun_core"], "action": "pulse"},
                ],
            )

        return None


    # =========================================================================
    # INTELLIGENT PROCEDURAL STRUCTURAL ASSEMBLY GENERATOR
    # Assembles realistic, structurally complete engineering 3D models for ANY prompt
    # =========================================================================

    def _generate_procedural_fallback(self, instruction: str) -> ModelSpec:
        """
        Dynamically synthesize a complete, realistic, structurally connected engineering 3D model
        for ANY custom user instruction, automatically determining required parts and assembling them.
        """
        clean_title = instruction.strip().title()
        if len(clean_title) > 42:
            clean_title = clean_title[:39] + "..."
        low = instruction.lower()

        # Domain classification:
        is_civil = any(w in low for w in ["bridge", "tower", "truss", "crane", "building", "beam", "frame", "scaffold", "pylon", "pier", "roof", "arch", "column", "structure", "stadium"])
        is_aero = any(w in low for w in ["aircraft", "airplane", "plane", "jet", "rocket", "satellite", "drone", "space", "shuttle", "flight", "glider", "orbiter", "capsule", "missile", "aerodynamic"])
        is_electric = any(w in low for w in ["circuit", "sensor", "radar", "antenna", "telescope", "radio", "wave", "laser", "solar panel", "battery", "coil", "magnet", "transistor", "detector", "optics"])
        is_science = any(w in low for w in ["atom", "molecule", "cell", "dna", "quantum", "particle", "crystal", "chemical", "nucleus", "organelle", "protein", "virus", "bacteria", "microscopic"])

        if is_civil:
            return self._build_civil_structural_assembly(clean_title)
        elif is_aero:
            return self._build_aerospace_assembly(clean_title)
        elif is_electric:
            return self._build_electronics_sensor_assembly(clean_title)
        elif is_science:
            return self._build_scientific_molecular_assembly(clean_title)
        else:
            return self._build_mechanical_mechanism_assembly(clean_title)

    def _build_civil_structural_assembly(self, title: str) -> ModelSpec:
        """Procedural generator for civil and structural engineering assemblies."""
        return ModelSpec(
            topic=f"{title} (Structural Engineering Model)",
            components=[
                {"id": "foundation_slab", "type": "box", "name": f"{title} Reinforced Concrete Foundation Base", "position": [0, 0, -1.8], "size": [5.6, 2.4, 0.4], "color": "#2d3748", "alpha": 0.95, "description": f"Massive reinforced concrete foundation slab providing ground anchoring and stability for {title}."},
                {"id": "column_left", "type": "cylinder", "name": "Primary Structural Column (West)", "endpoints": [[-2.2, 0, -1.6], [-2.2, 0, 1.8]], "size": [0.18, 3.4], "color": "#475569", "alpha": 0.95, "description": "Heavy-section vertical structural steel column carrying dead and live axial compressive loads."},
                {"id": "column_right", "type": "cylinder", "name": "Primary Structural Column (East)", "endpoints": [[2.2, 0, -1.6], [2.2, 0, 1.8]], "size": [0.18, 3.4], "color": "#475569", "alpha": 0.95, "description": "Opposing vertical load-bearing structural steel column."},
                {"id": "main_cross_girder", "type": "box", "name": "Upper Load-Bearing Box Girder", "position": [0, 0, 1.8], "size": [4.8, 0.6, 0.35], "color": "#00d4ff", "alpha": 0.95, "description": "Horizontal steel girder spanning columns and supporting upper subsystem loads."},
                {"id": "mid_level_tie", "type": "box", "name": "Intermediate Structural Tie Beam", "position": [0, 0, 0.0], "size": [4.6, 0.45, 0.25], "color": "#0ea5e9", "alpha": 0.92, "description": "Mid-elevation horizontal tie preventing column buckling and lateral drift."},
                {"id": "deck_platform", "type": "box", "name": f"{title} Operational Deck Platform", "position": [0, 0, -0.1], "size": [5.0, 1.6, 0.2], "color": "#64748b", "alpha": 0.95, "description": f"Stiffened working platform and roadway deck distributing operational loads across the frame."},
                {"id": "diagonal_brace_1", "type": "cylinder", "name": "Lower Diagonal Warren Truss Brace 1", "endpoints": [[-2.2, 0, -1.6], [-0.7, 0, 0.0]], "size": [0.09, 2.2], "color": "#ff8c00", "alpha": 0.9, "description": "Diagonal web brace resisting horizontal wind shear and seismic forces."},
                {"id": "diagonal_brace_2", "type": "cylinder", "name": "Lower Diagonal Warren Truss Brace 2", "endpoints": [[-0.7, 0, 0.0], [0.8, 0, -1.6]], "size": [0.09, 2.2], "color": "#ff8c00", "alpha": 0.9, "description": "Alternating diagonal member in triangular truss lattice."},
                {"id": "diagonal_brace_3", "type": "cylinder", "name": "Lower Diagonal Warren Truss Brace 3", "endpoints": [[0.8, 0, -1.6], [2.2, 0, 0.0]], "size": [0.09, 2.2], "color": "#ff8c00", "alpha": 0.9, "description": "Tension diagonal transferring loads into eastern foundation footing."},
                {"id": "diagonal_brace_top_1", "type": "cylinder", "name": "Upper Diagonal Web Strut 1", "endpoints": [[-2.2, 0, 0.0], [-0.7, 0, 1.8]], "size": [0.09, 2.2], "color": "#00ff88", "alpha": 0.9, "description": "Upper triangular bracing establishing rigid portal stability."},
                {"id": "diagonal_brace_top_2", "type": "cylinder", "name": "Upper Diagonal Web Strut 2", "endpoints": [[0.8, 0, 1.8], [2.2, 0, 0.0]], "size": [0.09, 2.2], "color": "#00ff88", "alpha": 0.9, "description": "Upper structural lattice bracing member."},
                {"id": "apex_actuator", "type": "box", "name": f"{title} Apex Core Mechanism / Actuator", "position": [0, 0, 2.1], "size": [1.0, 0.8, 0.45], "color": "#ffcc00", "alpha": 0.95, "description": "Primary functional mechanism, hoist, or power unit mounted atop the structural frame."},
                {"id": "load_conduit", "type": "cylinder", "name": "High-Tensile Load Cable / Conduit", "endpoints": [[0, 0, 2.1], [0, 0, 0.4]], "size": [0.05, 1.7], "color": "#d8f8ff", "alpha": 0.95, "description": "High-tensile steel cable or hydraulic conduit transferring active loads to the deck."},
                {"id": "end_terminal", "type": "cone", "name": "Working Load Hook / Anchor Node", "position": [0, 0, 0.2], "size": [0.35, 0.4], "color": "#ff3355", "alpha": 0.98, "axis": "z", "description": "Working terminal, hook block, or load connection node."},
            ],
            connections=[
                {"from": "foundation_slab", "to": "column_left", "color": "#2d3748", "thickness": 4, "label": "Column Anchor Base"},
                {"from": "foundation_slab", "to": "column_right", "color": "#2d3748", "thickness": 4, "label": "Column Anchor Base"},
                {"from": "column_left", "to": "main_cross_girder", "color": "#00d4ff", "thickness": 4, "label": "Moment Connection"},
                {"from": "column_right", "to": "main_cross_girder", "color": "#00d4ff", "thickness": 4, "label": "Moment Connection"},
                {"from": "column_left", "to": "mid_level_tie", "color": "#0ea5e9", "thickness": 3, "label": "Tie Joint"},
                {"from": "mid_level_tie", "to": "deck_platform", "color": "#64748b", "thickness": 3, "label": "Floor Beam Support"},
                {"from": "main_cross_girder", "to": "apex_actuator", "color": "#ffcc00", "thickness": 3, "label": "Actuator Mount"},
                {"from": "apex_actuator", "to": "load_conduit", "color": "#d8f8ff", "thickness": 3, "label": "Tension Cable"},
                {"from": "load_conduit", "to": "end_terminal", "color": "#ff3355", "thickness": 3, "label": "Terminal Joint"},
            ],
            explanation=f"This realistic 3D engineering model illustrates the structural mechanics of {title}. A reinforced concrete foundation anchors two heavy vertical columns linked by cross-girders and diagonal Warren truss bracing to form a rigid, triangulated frame resisting both vertical gravity loads and lateral shear moments.",
            animation_steps=[
                {"step": 1, "description": f"Operational loads act upon the platform deck and structural columns of {title}", "affected_components": ["deck_platform", "column_left", "column_right"], "action": "pulse"},
                {"step": 2, "description": "Diagonal Warren truss members resolve bending stresses into pure tension and compression", "affected_components": ["diagonal_brace_1", "diagonal_brace_2", "diagonal_brace_3", "diagonal_brace_top_1", "diagonal_brace_top_2"], "action": "highlight"},
                {"step": 3, "description": "Apex mechanism operates and conveys work through central tension conduit", "affected_components": ["apex_actuator", "load_conduit", "end_terminal"], "action": "pulse"},
            ],
        )

    def _build_mechanical_mechanism_assembly(self, title: str) -> ModelSpec:
        """Procedural generator for mechanical mechanisms, machines, engines, pumps, and tools."""
        return ModelSpec(
            topic=f"{title} (Mechanical System Model)",
            components=[
                {"id": "machine_bed", "type": "box", "name": f"{title} Rigid Cast Bed Chassis", "position": [0, 0, -1.6], "size": [4.4, 2.2, 0.4], "color": "#1e293b", "alpha": 0.95, "description": f"Heavy-duty cast bed frame providing rigid alignment for all rotating and moving {title} components."},
                {"id": "drive_motor", "type": "cylinder", "name": "Primary Drive Motor / Power Unit", "position": [-1.6, 0, -0.6], "size": [0.65, 1.2], "color": "#0c3245", "alpha": 0.9, "axis": "x", "description": "High-torque prime mover delivering rotational power into the drive train."},
                {"id": "input_shaft", "type": "cylinder", "name": "Hardened Alloy Input Shaft", "endpoints": [[-1.6, 0, -0.6], [-0.4, 0, -0.6]], "size": [0.15, 1.2], "color": "#cbd5e1", "alpha": 0.95, "description": "Precision-ground alloy steel input shaft transmitting motor torque."},
                {"id": "bearing_block_1", "type": "box", "name": "Input Pillow Block Bearing", "position": [-0.9, 0, -0.6], "size": [0.45, 0.7, 0.8], "color": "#475569", "alpha": 0.95, "description": "Heavy-duty pillow block housing radial roller bearings."},
                {"id": "driving_gear", "type": "cylinder", "name": "Precision Driving Gear / Rotor", "position": [-0.35, 0, -0.6], "size": [0.75, 0.35], "color": "#00d4ff", "alpha": 0.95, "axis": "x", "description": "Drive gear with precision-machined involute profile transferring torque across mesh line."},
                {"id": "driven_gear", "type": "cylinder", "name": "Meshing Driven Gear / Impeller", "position": [0.4, 0, -0.6], "size": [1.05, 0.35], "color": "#ff8c00", "alpha": 0.95, "axis": "x", "description": "Torque-multiplying driven gear or impeller member in the mechanical chain."},
                {"id": "output_shaft", "type": "cylinder", "name": "Heavy-Duty Output Shaft", "endpoints": [[0.4, 0, -0.6], [1.8, 0, -0.6]], "size": [0.18, 1.4], "color": "#cbd5e1", "alpha": 0.95, "description": "High-torque output shaft driving secondary linkages."},
                {"id": "bearing_block_2", "type": "box", "name": "Output Pillow Block Bearing", "position": [1.4, 0, -0.6], "size": [0.45, 0.7, 0.8], "color": "#475569", "alpha": 0.95, "description": "Output support bearing resisting high radial and thrust loads."},
                {"id": "hydraulic_cylinder", "type": "cylinder", "name": "Actuating Power Cylinder / Bore", "position": [0, 0, 0.8], "size": [0.42, 1.4], "color": "#ffcc00", "alpha": 0.92, "axis": "z", "description": "Linear actuator cylinder executing reciprocating stroke work."},
                {"id": "connecting_piston_rod", "type": "cylinder", "name": "Articulated Piston Connecting Rod", "endpoints": [[0, 0, 0.8], [0.8, 0, 0.2]], "size": [0.12, 1.4], "color": "#d8f8ff", "alpha": 0.95, "description": "Forged connecting rod translating rotational motion to reciprocating linear motion."},
                {"id": "lever_linkage", "type": "box", "name": f"{title} Articulated Working Link / Arm", "position": [1.1, 0, 0.4], "size": [1.6, 0.3, 0.25], "color": "#00ff88", "alpha": 0.95, "description": f"Articulated mechanical arm or lever arm delivering useful work to {title} interfaces."},
                {"id": "fluid_manifold", "type": "box", "name": "Pressurized Fluid Valve Manifold", "position": [-1.2, 0.7, 0.2], "size": [0.6, 0.5, 0.6], "color": "#ff3355", "alpha": 0.95, "description": "Hydraulic or pneumatic control valve manifold regulating fluid flow rates."},
                {"id": "pressure_supply_line", "type": "cylinder", "name": "High-Pressure Braided Feed Line", "endpoints": [[-1.2, 0.7, 0.2], [0, 0, 0.8]], "size": [0.045, 1.8], "color": "#00e5ff", "alpha": 0.9, "description": "Flexible steel braided pressure line delivering working fluid into actuator."},
                {"id": "control_governor", "type": "box", "name": "Governor Feedback Interface", "position": [1.4, 0.7, -0.8], "size": [0.5, 0.5, 0.5], "color": "#2dd4bf", "alpha": 0.95, "description": "Closed-loop feedback controller monitoring rotational velocity and position."},
            ],
            connections=[
                {"from": "machine_bed", "to": "drive_motor", "color": "#1e293b", "thickness": 3, "label": "Motor Bed Mount"},
                {"from": "drive_motor", "to": "input_shaft", "color": "#cbd5e1", "thickness": 4, "label": "Shaft Coupling"},
                {"from": "input_shaft", "to": "driving_gear", "color": "#00d4ff", "thickness": 4, "label": "Drive Torque"},
                {"from": "driving_gear", "to": "driven_gear", "color": "#ff8c00", "thickness": 4, "label": "Pitch Mesh Line"},
                {"from": "driven_gear", "to": "output_shaft", "color": "#cbd5e1", "thickness": 4, "label": "Amplified Torque"},
                {"from": "output_shaft", "to": "connecting_piston_rod", "color": "#d8f8ff", "thickness": 3, "label": "Crank Link"},
                {"from": "connecting_piston_rod", "to": "hydraulic_cylinder", "color": "#ffcc00", "thickness": 3, "label": "Linear Stroke"},
                {"from": "fluid_manifold", "to": "pressure_supply_line", "color": "#00e5ff", "thickness": 2, "label": "Hydraulic Power"},
                {"from": "output_shaft", "to": "lever_linkage", "color": "#00ff88", "thickness": 3, "label": "Mechanical Output"},
            ],
            explanation=f"This interactive 3D model visualizes the mechanical operating principles of {title}. Rotational power from the primary motor drives an alloy shaft mounted in pillow-block bearings, which meshes through precision gears to multiply torque and actuate the working linkages and pistons.",
            animation_steps=[
                {"step": 1, "description": f"Drive motor energizes input shaft and turns the primary driving gear of {title}", "affected_components": ["drive_motor", "input_shaft", "driving_gear"], "action": "rotate"},
                {"step": 2, "description": "Meshing gear teeth transfer amplified torque to output shaft and crank linkages", "affected_components": ["driving_gear", "driven_gear", "output_shaft"], "action": "pulse"},
                {"step": 3, "description": "Connecting rod and power cylinder drive working mechanical arm through complete cycle", "affected_components": ["connecting_piston_rod", "hydraulic_cylinder", "lever_linkage"], "action": "highlight"},
            ],
        )

    def _build_aerospace_assembly(self, title: str) -> ModelSpec:
        """Procedural generator for aircraft, spacecraft, rockets, and satellites."""
        return ModelSpec(
            topic=f"{title} (Aerospace System Model)",
            components=[
                {"id": "fuselage_core", "type": "cylinder", "name": f"{title} Central Aerodynamic Fuselage", "position": [0, 0, 0], "size": [0.75, 3.8], "color": "#1e293b", "alpha": 0.95, "axis": "x", "description": f"Aerodynamic pressurized semi-monocoque fuselage providing the structural backbone of {title}."},
                {"id": "cockpit_canopy", "type": "sphere", "name": "Pressurized Flight Deck Canopy", "position": [1.4, 0, 0.4], "size": 0.55, "color": "#00e5ff", "alpha": 0.85, "description": "Multi-layer polycarbonate pressurized cockpit canopy offering pilot visibility and avionics protection."},
                {"id": "wing_spar_transverse", "type": "cylinder", "name": "Primary Structural Wing Spar", "endpoints": [[0, -2.6, 0], [0, 2.6, 0]], "size": [0.14, 5.2], "color": "#64748b", "alpha": 0.95, "description": "Continuous forged spar carrying wing bending moments through the center fuselage."},
                {"id": "wing_port", "type": "box", "name": "Port Aerodynamic Wing / Airfoil", "position": [0, -1.8, 0], "size": [1.4, 2.2, 0.12], "color": "#0ea5e9", "alpha": 0.92, "description": "Cambered composite lifting wing generating aerodynamic lift forces."},
                {"id": "wing_starboard", "type": "box", "name": "Starboard Aerodynamic Wing / Airfoil", "position": [0, 1.8, 0], "size": [1.4, 2.2, 0.12], "color": "#0ea5e9", "alpha": 0.92, "description": "Symmetrical starboard lifting wing surface."},
                {"id": "winglet_port", "type": "box", "name": "Port Winglet / Stabilizer", "position": [-0.4, -2.8, 0.4], "size": [0.6, 0.1, 0.8], "color": "#ff8c00", "alpha": 0.95, "description": "Vertical aerodynamic winglet diffusing induced tip vortex drag."},
                {"id": "winglet_starboard", "type": "box", "name": "Starboard Winglet / Stabilizer", "position": [-0.4, 2.8, 0.4], "size": [0.6, 0.1, 0.8], "color": "#ff8c00", "alpha": 0.95, "description": "Starboard induced drag reduction winglet."},
                {"id": "propulsion_port", "type": "cylinder", "name": "Port Propulsion Thruster / Engine", "position": [-0.6, -1.1, -0.35], "size": [0.35, 1.6], "color": "#334155", "alpha": 0.95, "axis": "x", "description": "High-thrust propulsion engine nacelle providing forward forward velocity vector."},
                {"id": "propulsion_starboard", "type": "cylinder", "name": "Starboard Propulsion Thruster / Engine", "position": [-0.6, 1.1, -0.35], "size": [0.35, 1.6], "color": "#334155", "alpha": 0.95, "axis": "x", "description": "Starboard propulsion unit balancing thrust line."},
                {"id": "nozzle_port", "type": "cone", "name": "Port Supersonic Expansion Nozzle", "position": [-1.6, -1.1, -0.35], "size": [0.38, 0.6], "color": "#ff5722", "alpha": 0.95, "axis": "x", "description": "Convergent-divergent nozzle expanding hot exhaust gases into reactive thrust."},
                {"id": "nozzle_starboard", "type": "cone", "name": "Starboard Supersonic Expansion Nozzle", "position": [-1.6, 1.1, -0.35], "size": [0.38, 0.6], "color": "#ff5722", "alpha": 0.95, "axis": "x", "description": "Starboard expansion thrust nozzle."},
                {"id": "vertical_tailfin", "type": "box", "name": "Empennage Vertical Stabilizer & Rudder", "position": [-1.4, 0, 0.85], "size": [1.1, 0.12, 1.3], "color": "#ff3355", "alpha": 0.95, "description": "Vertical tail surface providing directional yaw stability and rudder control."},
                {"id": "avionics_sensor_suite", "type": "box", "name": "Flight Guidance & Avionics Suite", "position": [1.8, 0, 0], "size": [0.5, 0.5, 0.4], "color": "#00ff88", "alpha": 0.95, "description": "Autonomous flight control computer, inertial measurement units (IMU), and radar telemetry."},
            ],
            connections=[
                {"from": "fuselage_core", "to": "wing_spar_transverse", "color": "#64748b", "thickness": 4, "label": "Spar Carrythrough"},
                {"from": "wing_spar_transverse", "to": "wing_port", "color": "#0ea5e9", "thickness": 3, "label": "Lift Force"},
                {"from": "wing_spar_transverse", "to": "wing_starboard", "color": "#0ea5e9", "thickness": 3, "label": "Lift Force"},
                {"from": "fuselage_core", "to": "propulsion_port", "color": "#334155", "thickness": 3, "label": "Engine Pylon"},
                {"from": "fuselage_core", "to": "propulsion_starboard", "color": "#334155", "thickness": 3, "label": "Engine Pylon"},
                {"from": "propulsion_port", "to": "nozzle_port", "color": "#ff5722", "thickness": 4, "label": "Exhaust Thrust"},
                {"from": "propulsion_starboard", "to": "nozzle_starboard", "color": "#ff5722", "thickness": 4, "label": "Exhaust Thrust"},
                {"from": "fuselage_core", "to": "vertical_tailfin", "color": "#ff3355", "thickness": 3, "label": "Empennage Root"},
            ],
            explanation=f"This 3D aerospace engineering model demonstrates the structural and flight mechanics of {title}. The semi-monocoque fuselage carries the aerodynamic wing spars and propulsion units, balancing lift, thrust, weight, and drag across six degrees of freedom.",
            animation_steps=[
                {"step": 1, "description": f"Propulsion thrusters ignite and generate forward thrust vectors for {title}", "affected_components": ["propulsion_port", "propulsion_starboard", "nozzle_port", "nozzle_starboard"], "action": "pulse"},
                {"step": 2, "description": "Airfoil wing surfaces generate aerodynamic lift forces balancing craft weight", "affected_components": ["wing_port", "wing_starboard", "winglet_port", "winglet_starboard"], "action": "highlight"},
                {"step": 3, "description": "Flight avionics command control surfaces for active 3-axis trajectory stabilization", "affected_components": ["avionics_sensor_suite", "vertical_tailfin"], "action": "move"},
            ],
        )

    def _build_electronics_sensor_assembly(self, title: str) -> ModelSpec:
        """Procedural generator for electronics, sensors, antennas, radars, and optical systems."""
        return ModelSpec(
            topic=f"{title} (Electronic & Sensor Platform)",
            components=[
                {"id": "tripod_foundation", "type": "box", "name": f"{title} Heavy Support Platform", "position": [0, 0, -1.8], "size": [3.2, 3.2, 0.35], "color": "#1e293b", "alpha": 0.95, "description": f"Precision anti-vibration ground base anchoring {title}."},
                {"id": "azimuth_column", "type": "cylinder", "name": "Precision Azimuth Drive Column", "endpoints": [[0, 0, -1.6], [0, 0, 0.0]], "size": [0.25, 1.6], "color": "#475569", "alpha": 0.95, "description": "360-degree rotary azimuth tracking column with internal optical encoders."},
                {"id": "gimbal_yoke", "type": "box", "name": "Dual-Axis Elevation Gimbal Fork", "position": [0, 0, 0.1], "size": [1.8, 0.8, 0.4], "color": "#ff8c00", "alpha": 0.95, "description": "Cast aluminum gimbal yoke providing dual-axis motorized pointing articulation."},
                {"id": "collector_aperture", "type": "cone", "name": "Parabolic Reflector / Optical Aperture", "position": [0, 0, 0.7], "size": [1.6, 1.1], "color": "#0c3245", "alpha": 0.75, "axis": "z", "description": "Parabolic collector dish or optical barrel concentrating incoming electromagnetic signals onto the focal receiver."},
                {"id": "focal_sensor_pod", "type": "sphere", "name": "Primary Sensor Receiver Node", "position": [0, 0, 2.1], "size": 0.32, "color": "#00ff88", "alpha": 0.95, "description": "Cryogenically cooled focal plane detector converting electromagnetic energy into digital signals."},
                {"id": "support_strut_1", "type": "cylinder", "name": "Focal Support Strut 1", "endpoints": [[-1.1, 0, 1.1], [0, 0, 2.1]], "size": [0.04, 1.5], "color": "#cbd5e1", "alpha": 0.9, "description": "Carbon fiber quadripod strut maintaining sub-millimeter focal alignment."},
                {"id": "support_strut_2", "type": "cylinder", "name": "Focal Support Strut 2", "endpoints": [[1.1, 0, 1.1], [0, 0, 2.1]], "size": [0.04, 1.5], "color": "#cbd5e1", "alpha": 0.9, "description": "Carbon fiber quadripod support strut."},
                {"id": "support_strut_3", "type": "cylinder", "name": "Focal Support Strut 3", "endpoints": [[0, -1.1, 1.1], [0, 0, 2.1]], "size": [0.04, 1.5], "color": "#cbd5e1", "alpha": 0.9, "description": "Carbon fiber quadripod support strut."},
                {"id": "waveguide_feed", "type": "cylinder", "name": "Coaxial Waveguide Signal Feed", "endpoints": [[0, 0, 2.1], [0, 0, 0.2]], "size": [0.05, 1.9], "color": "#ffcc00", "alpha": 0.95, "description": "Low-loss coaxial waveguide transmitting microwave or optical signals from sensor to processing unit."},
                {"id": "signal_processor", "type": "box", "name": "Digital Signal Processing (DSP) Inverter", "position": [-1.0, 0.8, -1.4], "size": [0.8, 0.7, 0.6], "color": "#00d4ff", "alpha": 0.95, "description": "Ultra-fast FPGA/DSP signal processor filtering and amplifying telemetry data."},
                {"id": "power_supply", "type": "box", "name": "Regulated Power Distribution Unit", "position": [1.0, 0.8, -1.4], "size": [0.8, 0.7, 0.6], "color": "#ff3355", "alpha": 0.95, "description": "Clean regulated DC power supply with surge protection and battery backup."},
            ],
            connections=[
                {"from": "tripod_foundation", "to": "azimuth_column", "color": "#1e293b", "thickness": 4, "label": "Rotary Bearing"},
                {"from": "azimuth_column", "to": "gimbal_yoke", "color": "#ff8c00", "thickness": 4, "label": "Azimuth Drive"},
                {"from": "gimbal_yoke", "to": "collector_aperture", "color": "#0c3245", "thickness": 3, "label": "Elevation Trunnion"},
                {"from": "collector_aperture", "to": "focal_sensor_pod", "color": "#cbd5e1", "thickness": 2, "label": "Optical Axis Focus"},
                {"from": "focal_sensor_pod", "to": "waveguide_feed", "color": "#ffcc00", "thickness": 3, "label": "RF Signal Channel"},
                {"from": "waveguide_feed", "to": "signal_processor", "color": "#00d4ff", "thickness": 3, "label": "Coaxial Inflow"},
                {"from": "power_supply", "to": "signal_processor", "color": "#ff3355", "thickness": 2, "label": "Regulated DC Power"},
            ],
            explanation=f"This high-precision engineering model details the electromagnetic and sensor systems of {title}. The aperture focuses incoming signals onto a focal receiver node supported by carbon struts, which conduits data into an FPGA signal processor for telemetry analysis.",
            animation_steps=[
                {"step": 1, "description": f"Azimuth and elevation gimbals steer {title} to track target trajectory", "affected_components": ["azimuth_column", "gimbal_yoke", "collector_aperture"], "action": "rotate"},
                {"step": 2, "description": "Collector aperture concentrates incoming wave front onto focal sensor receiver", "affected_components": ["collector_aperture", "focal_sensor_pod"], "action": "pulse"},
                {"step": 3, "description": "Waveguide channels raw signal into FPGA processor for high-speed demodulation", "affected_components": ["waveguide_feed", "signal_processor"], "action": "highlight"},
            ],
        )

    def _build_scientific_molecular_assembly(self, title: str) -> ModelSpec:
        """Procedural generator for atomic, molecular, quantum, and biological science systems."""
        return ModelSpec(
            topic=f"{title} (Scientific & Molecular Structure)",
            components=[
                {"id": "core_nucleus", "type": "sphere", "name": f"{title} Central Dense Core / Nucleus", "position": [0, 0, 0], "size": 0.8, "color": "#ff3355", "alpha": 0.95, "description": f"Central dense physical core orchestrating fundamental atomic or molecular bonds of {title}."},
                {"id": "orbital_manifold_1", "type": "torus", "name": "Principal Quantum Orbital Ring 1", "position": [0, 0, 0], "size": [2.4, 0.035], "normal": [0.3, 0.4, 1.0], "color": "#00e5ff", "alpha": 0.85, "description": "Tilted quantum orbital probability shell containing bound valence particles."},
                {"id": "orbital_manifold_2", "type": "torus", "name": "Principal Quantum Orbital Ring 2", "position": [0, 0, 0], "size": [2.4, 0.035], "normal": [-0.5, 0.6, 1.0], "color": "#22d3ee", "alpha": 0.85, "description": "Complementary tilted subshell completing the spatial equilibrium cloud."},
                {"id": "orbital_manifold_3", "type": "torus", "name": "Transverse Conjugate Ring 3", "position": [0, 0, 0], "size": [2.4, 0.035], "normal": [0.8, -0.2, 0.6], "color": "#00ff88", "alpha": 0.85, "description": "Transverse orbital pathway matching the reference AURA 3D atom standard."},
                {"id": "valence_particle_1", "type": "sphere", "name": "Valence Lepton Particle 1 (-)", "position": [1.8, 0.6, -0.8], "size": 0.18, "color": "#ffcc00", "alpha": 1.0, "description": "Elementary particle executing relativistic orbital revolution."},
                {"id": "valence_particle_2", "type": "sphere", "name": "Valence Lepton Particle 2 (-)", "position": [-1.6, 1.2, 0.7], "size": 0.18, "color": "#ffcc00", "alpha": 1.0, "description": "Quantum particle establishing valence electron shell bonding."},
                {"id": "valence_particle_3", "type": "sphere", "name": "Valence Lepton Particle 3 (-)", "position": [0.4, -1.9, 1.2], "size": 0.18, "color": "#ffcc00", "alpha": 1.0, "description": "Paired opposite-spin electron particle."},
                {"id": "bonding_ligand_alpha", "type": "cylinder", "name": "Molecular Coordination Covalent Bond Alpha", "endpoints": [[0, 0, 0], [-2.2, 0, -1.4]], "size": [0.08, 2.6], "color": "#8ffcff", "alpha": 0.9, "description": "Strong covalent sigma bond sharing electron density between molecular centers."},
                {"id": "bonding_ligand_beta", "type": "cylinder", "name": "Molecular Coordination Covalent Bond Beta", "endpoints": [[0, 0, 0], [2.2, 0, -1.4]], "size": [0.08, 2.6], "color": "#8ffcff", "alpha": 0.9, "description": "Covalent bond link anchoring terminal functional group."},
                {"id": "terminal_group_alpha", "type": "sphere", "name": "Terminal Molecular Functional Group Alpha", "position": [-2.2, 0, -1.4], "size": 0.5, "color": "#ff8c00", "alpha": 0.95, "description": "Peripheral chemical group defining intermolecular reactivity and charge distribution."},
                {"id": "terminal_group_beta", "type": "sphere", "name": "Terminal Molecular Functional Group Beta", "position": [2.2, 0, -1.4], "size": 0.5, "color": "#00ff88", "alpha": 0.95, "description": "Opposing chemical functional group."},
            ],
            connections=[
                {"from": "core_nucleus", "to": "valence_particle_1", "color": "#00e5ff", "thickness": 2, "label": "Coulomb Attraction"},
                {"from": "core_nucleus", "to": "valence_particle_2", "color": "#22d3ee", "thickness": 2, "label": "Coulomb Attraction"},
                {"from": "core_nucleus", "to": "terminal_group_alpha", "color": "#8ffcff", "thickness": 3, "label": "Covalent Bond Alpha"},
                {"from": "core_nucleus", "to": "terminal_group_beta", "color": "#8ffcff", "thickness": 3, "label": "Covalent Bond Beta"},
            ],
            explanation=f"This scientific 3D model presents the physical and chemical properties of {title}. A dense central core binds peripheral atoms through covalent coordinate bonds, while quantum probability shells constrain orbiting valence particles in dynamic equilibrium.",
            animation_steps=[
                {"step": 1, "description": "Central core exerts strong and electrostatic binding potentials", "affected_components": ["core_nucleus"], "action": "pulse"},
                {"step": 2, "description": "Valence particles orbit along multiple tilted quantum shells", "affected_components": ["orbital_manifold_1", "orbital_manifold_2", "orbital_manifold_3", "valence_particle_1", "valence_particle_2", "valence_particle_3"], "action": "rotate"},
                {"step": 3, "description": "Covalent bonding ligands transmit vibrational and rotational energy to functional groups", "affected_components": ["bonding_ligand_alpha", "bonding_ligand_beta", "terminal_group_alpha", "terminal_group_beta"], "action": "highlight"},
            ],
        )


# Convenience alias
ModelGenerator = AIModelGenerator

