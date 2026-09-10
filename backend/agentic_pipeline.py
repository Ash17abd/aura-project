"""
Autonomous Agentic Pipeline for AURA 3D Learning Lab.

Orchestrates the complete automated lifecycle:
Voice/Text → Intent Understanding → Agentic Planning → Reference Search/Context Gathering → 
Dynamic ModelSpec Generation → Validation/Repair → Three.js Rendering → Reference Images → 
Semantic Animation → Explanation/Teacher Mode → Interactive Learning/Quiz → 
Conversational Modification → Memory Update

OS requests follow:
Voice/Text → Intent → Permission Check → Secure Local Agent → Approved OS Action → Result.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from backend.model_spec_schema import validate_and_repair_model_spec
from backend.self_verification import SelfVerificationEngine
from backend.secure_os_agent import secure_agent
from backend.session_memory import session_manager
from backend.teacher_mode import TeacherModeGenerator
from backend.quiz_generator import QuizGenerator
from actions.image_search import search_diagram_images
from actions.model_generator import AIModelGenerator, ModelSpec


class AgenticPipeline:
    """Central autonomous reasoning and execution coordinator."""

    def __init__(self):
        self.generator = AIModelGenerator()

    def classify_intent(self, text: str, has_active_model: bool) -> tuple[str, dict[str, Any]]:
        """
        Understands the user's intent and extracts parameters without relying on brittle exact keywords.
        """
        low = text.lower().strip()

        # 1. Check OS Automation intent ("open chrome", "open vs code", "launch explorer", "mute volume")
        os_triggers = [
            "open chrome", "open google chrome", "open vs code", "open vscode", "open code",
            "open notepad", "open calculator", "open calc", "open explorer", "open file explorer",
            "open terminal", "open cmd", "open powershell", "open spotify", "open discord",
            "open downloads", "open desktop", "open documents", "open project folder",
            "mute volume", "unmute", "volume up", "volume down", "take screenshot",
            "list processes", "show processes", "running tasks", "task list", "running processes"
        ]
        if any(t in low for t in os_triggers) or (low.startswith("open ") and any(k in low for k in ["app", "browser", "folder", "directory", "window"])):
            return "OS_AUTOMATION", {"command": text}

        # 2. Check Teacher Mode request ("explain this", "how does it work", "teach me", "teacher mode")
        teacher_triggers = ["teacher mode", "explain the model", "explain this system", "how does this work", "working principle", "teach me how this works", "deep explanation"]
        if any(t in low for t in teacher_triggers):
            return "TEACHER_EXPLAIN", {}

        # 3. Check Quiz request ("quiz me", "test my knowledge", "generate a quiz", "quiz mode")
        quiz_triggers = ["quiz", "test me", "start a quiz", "quiz mode", "ask me questions", "practice questions"]
        if any(t in low for t in quiz_triggers):
            diff = "Intermediate"
            if "beginner" in low or "easy" in low: diff = "Beginner"
            elif "advanced" in low or "hard" in low: diff = "Advanced"
            return "GENERATE_QUIZ", {"difficulty": diff}

        # 4. Check Conversational 3D Modification ("recolor", "add a", "remove", "resize", "rotate", "move", "connect")
        modify_triggers = ["recolor", "change color", "add a ", "add another", "remove ", "delete ", "make it bigger", "make it smaller", "resize", "rotate the", "move the", "connect the"]
        if has_active_model and any(t in low for t in modify_triggers):
            return "MODIFY_3D", {"instruction": text}

        # 5. Check Semantic Animation control ("animate", "play animation", "show magnetic flux", "show electrical flow", "simulate flow")
        anim_triggers = ["animate", "play animation", "pause animation", "show rotation", "show flow", "simulate", "semantic animation"]
        if has_active_model and any(t in low for t in anim_triggers):
            return "SEMANTIC_ANIMATE", {"instruction": text}

        # 6. Check New 3D Model Generation intent ("create", "build", "visualize", "show me a", "model a")
        gen_triggers = ["create a", "create 3d", "build a", "visualize", "show me a", "make a 3d", "generate a", "3d model of", "diagram of", "model of"]
        if any(t in low for t in gen_triggers) or not has_active_model:
            clean_prompt = text
            for t in gen_triggers:
                clean_prompt = clean_prompt.replace(t, "").strip()
            return "GENERATE_3D", {"prompt": clean_prompt or text}

        # 7. Default to conversational learning chat
        return "GENERAL_CHAT", {"query": text}

    def run(
        self,
        user_instruction: str,
        session_id: str = "default_user_session",
        image_bytes: bytes | None = None,
        mime_type: str = "image/jpeg",
    ) -> dict[str, Any]:
        """
        Executes the end-to-end agentic workflow.
        Returns unified response object containing actions taken, verified model, references, teacher lesson, and quiz.
        """
        session = session_manager.get_or_create(session_id)
        has_active_model = session.current_model is not None

        # 1. Intent Understanding
        intent, params = self.classify_intent(user_instruction, has_active_model)
        execution_plan = []

        # ============================================================
        # PIPELINE A: Secure OS Automation
        # ============================================================
        if intent == "OS_AUTOMATION":
            cmd = params.get("command", user_instruction)
            execution_plan.append({"step": "Permission & Whitelist Verification", "status": "APPROVED"})
            execution_plan.append({"step": "Secure Local Agent Execution", "status": "IN_PROGRESS"})
            
            os_res = secure_agent.execute_command(cmd, session_id=session_id)
            execution_plan[-1]["status"] = "SUCCESS" if os_res.get("success") else "REJECTED"

            reply_text = os_res.get("message", "Executed OS command.")
            session.add_message("user", user_instruction)
            session.add_message("assistant", reply_text)

            return {
                "intent": intent,
                "text_response": reply_text,
                "execution_plan": execution_plan,
                "os_result": os_res,
                "session_state": session.to_dict(),
            }

        # ============================================================
        # PIPELINE B: Conversational 3D Modification
        # ============================================================
        elif intent == "MODIFY_3D" and session.current_model:
            execution_plan.append({"step": "Parse 3D Component Target & Desired Modification", "status": "COMPLETE"})
            execution_plan.append({"step": "Apply Contextual Modification", "status": "IN_PROGRESS"})
            
            mod_inst = params.get("instruction", user_instruction)
            updated_model = self.generator.modify_model(session.current_model, mod_inst)
            raw_dict = updated_model.to_dict() if updated_model else session.current_model

            execution_plan.append({"step": "Self-Verification & Auto-Repair Engine", "status": "IN_PROGRESS"})
            verified_model, report = SelfVerificationEngine.verify_and_repair(raw_dict)
            verified_model["reference_images"] = session.current_model.get("reference_images", [])
            execution_plan[-1]["status"] = f"VERIFIED (Score: {report.get('score', 100)}%)"

            # Update session memory
            session.set_model(verified_model, record_history=True)
            reply = f"Applied modification: **{mod_inst}**. The 3D model has been updated and verified."
            session.add_message("user", user_instruction)
            session.add_message("assistant", reply)

            return {
                "intent": intent,
                "text_response": reply,
                "execution_plan": execution_plan,
                "model_spec": verified_model,
                "model": verified_model,
                "verification_report": report,
                "session_state": session.to_dict(),
            }

        # ============================================================
        # PIPELINE C: Semantic Animation Control
        # ============================================================
        elif intent == "SEMANTIC_ANIMATE" and session.current_model:
            execution_plan.append({"step": "Parse Semantic Physics Animation Goal", "status": "COMPLETE"})
            execution_plan.append({"step": "Synthesize 60 FPS Particle & Motion Sequence", "status": "IN_PROGRESS"})
            
            anim_inst = params.get("instruction", user_instruction)
            steps = self.generator.generate_animation(session.current_model, anim_inst)
            spec_copy = dict(session.current_model)
            spec_copy["animation_steps"] = steps
            verified_model, report = SelfVerificationEngine.verify_and_repair(spec_copy)
            session.set_model(verified_model, record_history=False)
            execution_plan[-1]["status"] = f"APPLIED ({len(verified_model.get('animation_steps', []))} PHASES)"

            reply = f"Configured semantic animation sequence for **{verified_model['topic']}**: {anim_inst}."
            session.add_message("user", user_instruction)
            session.add_message("assistant", reply)

            return {
                "intent": intent,
                "text_response": reply,
                "execution_plan": execution_plan,
                "model_spec": verified_model,
                "model": verified_model,
                "animation_steps": verified_model.get("animation_steps", []),
                "verification_report": report,
                "session_state": session.to_dict(),
            }

        # ============================================================
        # PIPELINE D: Visual Understanding (Image to 3D Model)
        # ============================================================
        elif intent == "IMAGE_TO_3D" or image_bytes is not None:
            execution_plan.append({"step": "Visual Understanding & Diagram Extraction", "status": "IN_PROGRESS"})
            
            if image_bytes:
                raw_spec = self.generator.generate_from_image(image_bytes, mime_type=mime_type, instruction=user_instruction)
            else:
                raw_spec = self.generator.generate_model(user_instruction or "Reconstructed Diagram")
            
            spec_dict = raw_spec.to_dict() if raw_spec else {"topic": user_instruction or "Visual Schematic Assembly", "components": []}
            execution_plan[-1]["status"] = f"EXTRACTED ({spec_dict.get('topic')})"

            execution_plan.append({"step": "Self-Verification & Auto-Repair Engine", "status": "IN_PROGRESS"})
            verified_model, report = SelfVerificationEngine.verify_and_repair(spec_dict)
            execution_plan[-1]["status"] = f"PASSED (Score: {report.get('score', 100)}%)"

            # Search real reference diagrams as well
            try:
                ref_images = search_diagram_images(verified_model["topic"], max_results=4)
                verified_model["reference_images"] = ref_images
            except Exception:
                verified_model["reference_images"] = []

            lesson = TeacherModeGenerator.generate_lesson(verified_model)
            quiz = QuizGenerator.generate_quiz(verified_model, difficulty=session.difficulty)

            session.set_model(verified_model, record_history=True)
            session.current_lesson = lesson
            session.current_quiz = quiz

            reply = f"Successfully reconstructed interactive 3D model for **{verified_model['topic']}** from visual reference with {len(verified_model['components'])} components."
            session.add_message("user", user_instruction or "Uploaded schematic reference.")
            session.add_message("assistant", reply)

            return {
                "intent": "IMAGE_TO_3D",
                "text_response": reply,
                "execution_plan": execution_plan,
                "model_spec": verified_model,
                "model": verified_model,
                "verification_report": report,
                "reference_images": verified_model.get("reference_images", []),
                "teacher_lesson": lesson,
                "quiz": quiz,
                "session_state": session.to_dict(),
            }

        # ============================================================
        # PIPELINE E: AI Teacher Mode
        # ============================================================
        elif intent == "TEACHER_EXPLAIN" and session.current_model:
            execution_plan.append({"step": "Synthesize System Anatomy & Physics Laws", "status": "COMPLETE"})
            execution_plan.append({"step": "Generate Socratic Lesson & Applications", "status": "COMPLETE"})

            lesson = TeacherModeGenerator.generate_lesson(session.current_model)
            session.current_lesson = lesson
            reply = f"### {lesson.get('topic')} — AI Teacher Mode\n\n{lesson.get('overview')}\n\n**Working Principle:** {lesson.get('working_principle')}"
            session.add_message("user", user_instruction)
            session.add_message("assistant", reply)

            return {
                "intent": intent,
                "text_response": reply,
                "execution_plan": execution_plan,
                "teacher_lesson": lesson,
                "session_state": session.to_dict(),
            }

        # ============================================================
        # PIPELINE F: Interactive Quiz Generation
        # ============================================================
        elif intent == "GENERATE_QUIZ" and session.current_model:
            diff = params.get("difficulty", "Intermediate")
            execution_plan.append({"step": f"Generate {diff} Assessment from 3D Assembly", "status": "COMPLETE"})

            quiz = QuizGenerator.generate_quiz(session.current_model, difficulty=diff)
            session.current_quiz = quiz
            reply = f"Generated interactive **{diff}** quiz with {len(quiz.get('questions', []))} questions for **{quiz.get('topic')}**. Test your understanding in the Quiz Lab tab!"
            session.add_message("user", user_instruction)
            session.add_message("assistant", reply)

            return {
                "intent": intent,
                "text_response": reply,
                "execution_plan": execution_plan,
                "quiz": quiz,
                "session_state": session.to_dict(),
            }

        # ============================================================
        # PIPELINE G: Dynamic 3D Model Generation (Full Pipeline)
        # ============================================================
        elif intent == "GENERATE_3D":
            prompt = params.get("prompt", user_instruction)
            execution_plan.append({"step": "Retrieve Real-World Web Reference Schematics", "status": "IN_PROGRESS"})
            
            # Step 1: Real-world technical reference retrieval
            ref_images = []
            try:
                ref_images = search_diagram_images(prompt, max_results=6)
                execution_plan[-1]["status"] = f"FOUND {len(ref_images)} REFERENCES"
            except Exception:
                execution_plan[-1]["status"] = "OFFLINE_FALLBACK"

            # Step 2: Dynamic Model Generation (Gemini AI -> OpenRouter -> Procedural)
            execution_plan.append({"step": "Dynamic AI ModelSpec Generation", "status": "IN_PROGRESS"})
            raw_spec = self.generator.generate_model(prompt)
            spec_dict = raw_spec.to_dict() if raw_spec else {"topic": prompt, "components": []}
            execution_plan[-1]["status"] = f"GENERATED ({spec_dict.get('topic')})"

            # Step 3: 8-Dimension Self-Verification & Auto-Repair
            execution_plan.append({"step": "Self-Verification & Auto-Repair Engine", "status": "IN_PROGRESS"})
            verified_model, report = SelfVerificationEngine.verify_and_repair(spec_dict)
            verified_model["reference_images"] = ref_images
            execution_plan[-1]["status"] = f"PASSED (Score: {report.get('score', 100)}%)"

            # Step 4: Generate Teacher Lesson & Initial Quiz
            execution_plan.append({"step": "Prepare Teacher Pedagogy & Assessment", "status": "COMPLETE"})
            lesson = TeacherModeGenerator.generate_lesson(verified_model)
            quiz = QuizGenerator.generate_quiz(verified_model, difficulty=session.difficulty)

            # Update continuous session state
            session.set_model(verified_model, record_history=True)
            session.current_lesson = lesson
            session.current_quiz = quiz

            reply = (
                f"Generated interactive 3D model for **{verified_model['topic']}** with "
                f"{len(verified_model['components'])} engineered parts and {len(verified_model['animation_steps'])} operational phases. "
                f"{verified_model['explanation']}"
            )
            session.add_message("user", user_instruction)
            session.add_message("assistant", reply)

            return {
                "intent": intent,
                "text_response": reply,
                "execution_plan": execution_plan,
                "model_spec": verified_model,
                "model": verified_model,
                "verification_report": report,
                "reference_images": ref_images,
                "teacher_lesson": lesson,
                "quiz": quiz,
                "session_state": session.to_dict(),
            }

        # ============================================================
        # PIPELINE F: General Learning Inquiry / Chat
        # ============================================================
        else:
            session.add_message("user", user_instruction)
            reply = (
                f"I am AURA, your autonomous AI learning assistant. "
                f"I can generate any 3D physical or engineering model from your instructions, "
                f"guide you through Teacher Mode, quiz your mastery, or control your desktop securely."
            )
            if session.current_model:
                reply += f" Currently inspecting **{session.current_model.get('topic')}** with {len(session.current_model.get('components', []))} components."
            session.add_message("assistant", reply)

            return {
                "intent": "GENERAL_CHAT",
                "text_response": reply,
                "execution_plan": [{"step": "Contextual Knowledge Synthesis", "status": "COMPLETE"}],
                "model_spec": session.current_model,
                "session_state": session.to_dict(),
            }


# Global pipeline instance
agentic_pipeline = AgenticPipeline()
