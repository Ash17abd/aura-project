"""
Interactive 3D Quiz Generator for AURA 3D Learning Lab.

Constructs comprehensive, model-tailored quizzes:
1. Multiple Choice Questions (MCQ)
2. True / False Concepts
3. 3D Component Identification (links directly to 3D model component picking)
4. Application & Scenario-based Engineering Problems
5. Configurable difficulty tiers (Beginner, Intermediate, Advanced)
"""

from __future__ import annotations

import json
import os
import random
import requests
from typing import Any


class QuizGenerator:
    """Generates educational quizzes tailored to the active 3D ModelSpec."""

    SYSTEM_PROMPT = """You are an expert STEM quiz and assessment designer.
Given a 3D model representing an engineering or science system, generate 4 to 5 rigorous, engaging questions in valid JSON.
Include a variety of question types:
- 'mcq' (Multiple Choice with 4 options)
- 'true_false' (True or False with 2 options)
- 'identification' (Which component performs X role? options contain component names, target_component_id contains matching ID)
- 'application' (What happens if parameter Y changes in this system? with 4 options)

Follow this EXACT schema:
{
  "topic": "System Topic Name",
  "difficulty": "Beginner|Intermediate|Advanced",
  "questions": [
    {
      "id": "q1",
      "type": "mcq|true_false|identification|application",
      "question": "Clear, concise question statement",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "target_component_id": "optional_component_id_for_3d_highlight",
      "explanation": "Detailed explanation of why this is the correct answer and the physical/engineering rationale."
    }
  ]
}
Respond with ONLY valid JSON."""

    @classmethod
    def generate_quiz(cls, model_spec: dict[str, Any], difficulty: str = "Intermediate", api_key: str | None = None) -> dict[str, Any]:
        topic = model_spec.get("topic", "System")
        components = model_spec.get("components", [])
        explanation = model_spec.get("explanation", "")

        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            from config import get_config
            key = get_config().get("gemini_api_key", "")

        # 1. Attempt AI Generation via Gemini
        if key and len(key) > 8:
            comp_summaries = [f"{c.get('id')}: {c.get('name')} - {c.get('description')}" for c in components[:10]]
            prompt = (
                f"SYSTEM TOPIC: {topic}\n"
                f"DIFFICULTY LEVEL: {difficulty}\n"
                f"SUMMARY: {explanation}\n"
                f"COMPONENTS: {comp_summaries}\n"
            )
            models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash-lite"]
            for model_name in models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
                    payload = {
                        "system_instruction": {"parts": [{"text": cls.SYSTEM_PROMPT}]},
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
                    }
                    res = requests.post(url, json=payload, timeout=25)
                    if res.status_code == 200:
                        data = res.json()
                        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                        clean = text.replace("```json", "").replace("```", "").strip()
                        parsed = json.loads(clean)
                        if isinstance(parsed, dict) and "questions" in parsed and len(parsed["questions"]) > 0:
                            return parsed
                except Exception:
                    continue

        # 2. Heuristic Procedural Fallback Generation
        questions = []
        c1 = components[0] if len(components) > 0 else {"name": "Primary Component", "id": "comp_1", "description": "Core unit"}
        c2 = components[1] if len(components) > 1 else {"name": "Secondary Component", "id": "comp_2", "description": "Auxiliary unit"}
        c3 = components[2] if len(components) > 2 else {"name": "Mounting Base", "id": "comp_3", "description": "Foundation"}

        # Q1: Component Identification
        questions.append({
            "id": "q1",
            "type": "identification",
            "question": f"In the 3D model of {topic}, which component is described as: \"{c1.get('description')}\"?",
            "options": [c1.get("name"), c2.get("name"), c3.get("name"), "None of the above"],
            "correct_index": 0,
            "target_component_id": c1.get("id"),
            "explanation": f"{c1.get('name')} is responsible for this functional role in the {topic} assembly.",
        })

        # Q2: MCQ on Working Principle
        questions.append({
            "id": "q2",
            "type": "mcq",
            "question": f"What is the primary function or energy conversion performed by the {topic}?",
            "options": [
                f"Controlled physical operation transforming input energy through {c1.get('name')}",
                "Arbitrary static support with no mechanical or physical interaction",
                "Complete dissipation of energy without mechanical or electrical output",
                "Reversing the laws of thermodynamics without external input",
            ],
            "correct_index": 0,
            "target_component_id": c1.get("id"),
            "explanation": f"{topic} works by channeling energy or force between components such as {c1.get('name')} and {c2.get('name')}.",
        })

        # Q3: True/False Question
        questions.append({
            "id": "q3",
            "type": "true_false",
            "question": f"True or False: The {c2.get('name')} operates independently without any physical or energetic connection to {c1.get('name')}.",
            "options": ["True", "False"],
            "correct_index": 1,
            "target_component_id": c2.get("id"),
            "explanation": f"False. In {topic}, {c1.get('name')} and {c2.get('name')} are functionally interdependent.",
        })

        # Q4: Application Scenario
        questions.append({
            "id": "q4",
            "type": "application",
            "question": f"If mechanical or electrical load on {c1.get('name')} increases significantly, what engineering effect is observed?",
            "options": [
                "Increased internal stress, temperature, or electromagnetic flux across the assembly",
                "The system instantaneously stops obeying physical conservation laws",
                "Total energy requirement drops to absolute zero",
                "No physical parameter in the system changes under load",
            ],
            "correct_index": 0,
            "target_component_id": c1.get("id"),
            "explanation": "Increasing operating load elevates kinetic stress, current, or thermal dissipation in the primary active components.",
        })

        return {
            "topic": topic,
            "difficulty": difficulty,
            "questions": questions,
        }
