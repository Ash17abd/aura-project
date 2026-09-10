"""
AI Teacher Mode Lesson & Component Explainer for AURA 3D Learning Lab.

Provides multi-tier pedagogical explanations (Beginner, Intermediate, Advanced, Socratic)
and contextual component-level instruction directly tied to active 3D ModelSpecs.
"""

from __future__ import annotations

import json
import os
import requests
from typing import Any


class TeacherModeGenerator:
    """Generates structured educational lessons and component explanations."""

    SYSTEM_PROMPT = """You are an elite master engineering professor and science educator.
Given a 3D ModelSpec representing a mechanical, electrical, physical, biological, or chemical system, 
create an engaging, pedagogically rigorous lesson in JSON format conforming strictly to this schema:

{
  "topic": "Precise Topic Title",
  "pedagogical_level": "Beginner | Intermediate | Advanced | Socratic",
  "overview": "Comprehensive explanation of the system, its primary purpose, and significance.",
  "components_breakdown": [
    {
      "name": "Part Name",
      "role": "Mechanical / Electrical / Structural Role",
      "explanation": "Detailed explanation of how this specific component interacts with others in the assembly."
    }
  ],
  "working_principle": "Step-by-step physical explanation: fundamental governing laws, energy transfer stages, and chain of operation.",
  "animation_analysis": "Explanation of the dynamic motion or operational phases visualized in the 3D animation sequence.",
  "real_world_applications": [
    "Application 1 with industrial or scientific context",
    "Application 2",
    "Application 3"
  ],
  "socratic_questions": [
    {
      "question": "Thought-provoking inquiry",
      "hint": "Guiding clue for the student",
      "answer": "Master answer"
    }
  ]
}
Respond with ONLY valid JSON."""

    @classmethod
    def generate_lesson(
        cls,
        model_spec: dict[str, Any],
        level: str = "intermediate",
        api_key: str | None = None
    ) -> dict[str, Any]:
        """Generate structured lesson with pedagogical level tailoring."""
        topic = model_spec.get("topic", "Engineering System")
        components = model_spec.get("components", [])
        explanation = model_spec.get("explanation", "")
        anim_steps = model_spec.get("animation_steps", [])

        norm_level = (level or "intermediate").lower()

        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            from config import get_config
            key = get_config().get("gemini_api_key", "")

        # 1. Attempt AI Generation
        if key and len(key) > 8:
            parts_list = [f"{c.get('name')} ({c.get('type')}): {c.get('description')}" for c in components[:14]]
            anim_phase_list = [s.get('description') for s in anim_steps[:6]]
            
            level_instructions = {
                "beginner": "Use intuitive analogies, plain everyday language, and simple conceptual examples. Avoid intimidating equations.",
                "intermediate": "Use standard technical terminology, component interactions, and fundamental physical laws.",
                "advanced": "Use rigorous scientific equations, thermodynamics, electromagnetic principles, material stresses, and engineering tolerances.",
                "socratic": "Structure explanations around questions, guided discoveries, and inquiry puzzles that invite student deduction."
            }.get(norm_level, "Provide standard technical pedagogy.")

            prompt = (
                f"SYSTEM TOPIC: {topic}\n"
                f"PEDAGOGICAL LEVEL: {norm_level.upper()}\n"
                f"LEVEL INSTRUCTION: {level_instructions}\n"
                f"SUMMARY: {explanation}\n"
                f"PARTS LIST: {parts_list}\n"
                f"ANIMATION PHASES: {anim_phase_list}\n"
            )
            models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash-lite"]
            for model_name in models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
                    payload = {
                        "system_instruction": {"parts": [{"text": cls.SYSTEM_PROMPT}]},
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
                    }
                    res = requests.post(url, json=payload, timeout=25)
                    if res.status_code == 200:
                        data = res.json()
                        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                        clean = text.replace("```json", "").replace("```", "").strip()
                        parsed = json.loads(clean)
                        if isinstance(parsed, dict) and ("overview" in parsed or "working_principle" in parsed):
                            if not parsed.get("topic"):
                                parsed["topic"] = topic
                            parsed["pedagogical_level"] = norm_level.capitalize()
                            comps = parsed.get("components_breakdown") or parsed.get("components") or []
                            if not comps and components:
                                comps = [
                                    {
                                        "name": c.get("name", "Component"),
                                        "role": c.get("role", "Functional Element"),
                                        "explanation": c.get("description", f"Operational part of {topic}."),
                                    }
                                    for c in components[:8]
                                ]
                            parsed["components_breakdown"] = comps
                            parsed["components"] = comps
                            parsed["level"] = norm_level.capitalize()
                            parsed["title"] = parsed.get("title", f"{topic} Educational Lesson")
                            if "sections" not in parsed:
                                parsed["sections"] = [
                                    {"title": "Overview", "content": parsed.get("overview", "")},
                                    {"title": "Working Principles", "content": parsed.get("working_principle", "")},
                                ]
                            if not parsed.get("working_principle"):
                                parsed["working_principle"] = f"Governed by physical conservation principles. {explanation}"
                            return parsed
                except Exception:
                    continue

        # 2. High-Quality Fallback Synthesis
        comp_breakdown = []
        for c in components[:8]:
            comp_breakdown.append({
                "name": c.get("name", "Component"),
                "role": c.get("role", "Functional Element"),
                "explanation": c.get("description", f"Integral part of the {topic} assembly."),
            })

        anim_desc = "; ".join([s.get("description", "") for s in anim_steps]) if anim_steps else "Demonstrates continuous functional operation."

        level_text = {
            "beginner": f"Imagine the {topic} like a team working together to accomplish a common physical goal.",
            "intermediate": f"The {topic} coordinates mechanical and energetic actions across interconnected components.",
            "advanced": f"The {topic} implements energy transfer under governing thermodynamic and dynamical equations.",
            "socratic": f"Consider how each component in {topic} must interact before motion or work can occur."
        }.get(norm_level, f"Operating principles of {topic}.")

        overview_text = (
            f"{level_text} It is an essential system designed to perform structured energy conversion, "
            f"physical transformation, or mechanical work. In this interactive 3D model, each element is arranged "
            f"according to real-world spatial constraints, enabling deep visual inspection."
        )
        working_principle_text = (
            f"Operating principles of {topic} are governed by fundamental physical conservation laws. "
            f"Input energy travels through interconnected components, transforming velocity, pressure, or electromagnetic potential into target output work. "
            f"{explanation}"
        )

        return {
            "topic": topic,
            "title": f"{topic} Comprehensive Lesson",
            "level": norm_level.capitalize(),
            "pedagogical_level": norm_level.capitalize(),
            "overview": overview_text,
            "components_breakdown": comp_breakdown,
            "components": comp_breakdown,
            "working_principle": working_principle_text,
            "sections": [
                {"title": "System Overview", "content": overview_text},
                {"title": "Operating Principles", "content": working_principle_text},
                {"title": "Component Mechanics", "content": "; ".join([f"{c['name']}: {c['explanation']}" for c in comp_breakdown[:4]])},
            ],
            "animation_analysis": f"The dynamic sequence demonstrates operational progression: {anim_desc}",
            "real_world_applications": [
                f"Industrial manufacturing and automation utilizing {topic}",
                f"Commercial energy, robotics, and mechanical power transmission",
                f"Advanced research and aerospace implementations",
            ],
            "socratic_questions": [
                {
                    "question": f"What happens to the {topic} if the primary active component is removed or restricted?",
                    "hint": "Trace the path of energy or force through the system.",
                    "answer": "Without the primary driver, force transmission stops and downstream components experience zero torque or current.",
                },
                {
                    "question": f"Which component in this {topic} is subjected to peak mechanical or thermal stress during high load?",
                    "hint": "Look for the junction node where energy density is highest.",
                    "answer": "The central bearing, winding, or piston node absorbs peak friction, electrical resistance, or pressure gradients.",
                },
            ],
        }

    @classmethod
    def explain_component(
        cls,
        model_spec: dict[str, Any],
        component_id: str,
        component_name: str | None = None,
        level: str = "intermediate",
        api_key: str | None = None
    ) -> dict[str, Any]:
        """
        Deep-dive contextual explanation for THAT specific selected 3D component.
        Explains: anatomy, exact role, physical interaction with adjacent parts, and failure modes.
        """
        topic = model_spec.get("topic", "System")
        components = model_spec.get("components", [])
        
        # Locate component by id or name
        target_comp = None
        for c in components:
            if c.get("id") == component_id or (component_name and c.get("name", "").lower() == component_name.lower()):
                target_comp = c
                break
        
        if not target_comp and components:
            target_comp = components[0]
            
        c_name = target_comp.get("name", component_name or "Selected Component")
        c_role = target_comp.get("role", "Active Element")
        c_desc = target_comp.get("description", "Core part of assembly.")
        c_type = target_comp.get("type", "solid")

        adjacent_names = [c.get("name") for c in components if c.get("id") != target_comp.get("id")][:3]
        adjacent_str = ", ".join(adjacent_names) if adjacent_names else "surrounding assembly"

        norm_level = (level or "intermediate").lower()

        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            from config import get_config
            key = get_config().get("gemini_api_key", "")

        # 1. Direct AI Generation if API available
        if key and len(key) > 8:
            prompt = (
                f"You are AURA's expert 3D engineering instructor.\n"
                f"TOPIC: {topic}\n"
                f"COMPONENT: {c_name} (Type: {c_type}, Role: {c_role})\n"
                f"DESCRIPTION: {c_desc}\n"
                f"NEIGHBORING PARTS: {adjacent_str}\n"
                f"PEDAGOGICAL LEVEL: {norm_level.upper()}\n\n"
                f"Explain THIS specific component's engineering purpose, how it interacts with {adjacent_str}, "
                f"what happens if it fails, and ask one intriguing socratic follow-up question. "
                f"Respond in JSON with keys: 'component_name', 'role', 'explanation', 'interactions', 'failure_impact', 'socratic_question'."
            )
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
                }
                res = requests.post(url, json=payload, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    txt = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                    parsed = json.loads(txt.replace("```json", "").replace("```", "").strip())
                    if isinstance(parsed, dict) and "explanation" in parsed:
                        parsed["status"] = "success"
                        parsed["component_id"] = target_comp.get("id", component_id)
                        parsed["component_name"] = parsed.get("component_name", c_name)
                        parsed["component"] = parsed.get("component_name", c_name)
                        parsed["role"] = parsed.get("role", c_role)
                        parsed["interactions"] = parsed.get("interactions", f"Interacts with {adjacent_str}")
                        parsed["failure_mode"] = parsed.get("failure_impact", parsed.get("failure_mode", f"Failure of {c_name} causes systemic instability."))
                        parsed["failure_impact"] = parsed["failure_mode"]
                        parsed["level"] = norm_level.capitalize()
                        return parsed
            except Exception:
                pass

        # 2. Reliable Heuristic Fallback
        return {
            "status": "success",
            "component_id": target_comp.get("id", component_id),
            "component_name": c_name,
            "component": c_name,
            "role": c_role,
            "level": norm_level.capitalize(),
            "explanation": (
                f"In the {topic}, the {c_name} acts as a vital {c_role}. "
                f"{c_desc} It maintains spatial alignment, transmits physical forces, or conducts electrical/fluid flux "
                f"necessary for systemic equilibrium."
            ),
            "interactions": f"Operates in direct mechanical, thermal, or electromagnetic conjunction with {adjacent_str}.",
            "failure_mode": (
                f"If the {c_name} fails or undergoes excessive wear, the {topic} will experience localized imbalance, "
                f"reduced efficiency, or complete mechanical seizure."
            ),
            "failure_impact": (
                f"If the {c_name} fails or undergoes excessive wear, the {topic} will experience localized imbalance, "
                f"reduced efficiency, or complete mechanical seizure."
            ),
            "socratic_question": (
                f"How would modifying the material properties or geometry of the {c_name} alter the overall performance of the {topic}?"
            )
        }


# Convenience alias
TeacherMode = TeacherModeGenerator
