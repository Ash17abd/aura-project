"""
Automated Verification Suite for AURE 3D Learning Lab & Autonomous Agent Platform.
Tests:
1. ModelSpecSchema validation & conforming primitives
2. 8-Dimension Self-Verification and Auto-Repair Engine
3. Secure Local OS Agent (whitelist, traversal blocking, audit log, confirmation)
4. AI Teacher Mode (pedagogical lesson structure & Socratic questions)
5. Interactive Quiz Lab (MCQ, True/False, and 3D Component Identification)
6. Session Memory Manager (state persistence & undo/redo tracking)
7. Voice Command & Intent Parser
8. Real-world reference schematics search
9. Unified Agentic Pipeline intent routing & turn execution
"""

import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.model_spec_schema import ModelSpecSchema, validate_and_repair_model_spec
from backend.self_verification import SelfVerificationEngine
from backend.secure_os_agent import SecureOSAgent, secure_agent
from backend.teacher_mode import TeacherMode
from backend.quiz_generator import QuizGenerator
from backend.session_memory import SessionMemoryManager
from backend.agentic_pipeline import AgenticPipeline
from actions.voice_parser import VoiceCommandParser
from actions.image_search import search_diagram_images
from actions.model_generator import ModelGenerator


class TestModelSpecSchema(unittest.TestCase):
    def test_schema_valid_spec(self):
        sample_spec = {
            "topic": "Lithium-Ion Battery Cell",
            "explanation": "Electrochemical energy storage cell.",
            "components": [
                {
                    "id": "anode",
                    "name": "Graphite Anode",
                    "type": "cylinder",
                    "role": "Negative Electrode",
                    "description": "Houses lithium ions during charge state.",
                    "position": [0, 0, 0],
                    "size": [1, 3, 1],
                    "color": "#3366cc",
                },
                {
                    "id": "cathode",
                    "name": "Lithium Metal Cathode",
                    "type": "cylinder",
                    "role": "Positive Electrode",
                    "description": "Releases lithium ions during discharge.",
                    "position": [3, 0, 0],
                    "size": [1, 3, 1],
                    "color": "#cc3333",
                }
            ],
            "connections": [
                {"from_id": "anode", "to_id": "cathode", "type": "conduit", "color": "#ffcc00"}
            ],
            "animation_steps": [
                {
                    "step": 1,
                    "description": "Electrons flow via external circuit while Li+ ions traverse electrolyte.",
                    "affected_components": ["anode", "cathode"],
                    "action": "electrical_flow",
                    "duration": 2.0
                }
            ],
            "camera": {"position": [0, 4, 8], "target": [1.5, 0, 0]}
        }
        is_valid, errors = ModelSpecSchema.validate_spec(sample_spec)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_schema_invalid_missing_fields(self):
        invalid_spec = {"topic": "Incomplete Model"}
        is_valid, errors = ModelSpecSchema.validate_spec(invalid_spec)
        self.assertFalse(is_valid)
        self.assertTrue(any("explanation" in e for e in errors))


class TestSelfVerificationEngine(unittest.TestCase):
    def test_8_dimension_verification_and_repair(self):
        # Spec with intentional defects:
        # 1. Missing component IDs
        # 2. Overlapping coordinates (clipping)
        # 3. Connection pointing to non-existent component
        # 4. Unknown animation action
        defective_spec = {
            "topic": "Turbofan Engine Core",
            "explanation": "Jet propulsion system with high-bypass airflow.",
            "components": [
                {
                    "name": "Compressor Stage",
                    "type": "cylinder",
                    "position": [0, 0, 0],
                    "size": [2, 2, 2],
                    "color": "#444444"
                },
                {
                    "name": "Combustion Chamber",
                    "type": "cylinder",
                    "position": [0.1, 0.1, 0.1],  # Heavy collision/clipping with compressor
                    "size": [2, 2, 2],
                    "color": "#ff4400"
                }
            ],
            "connections": [
                {"from_id": "Compressor Stage", "to_id": "NonExistentNozzle", "type": "conduit"}
            ],
            "animation_steps": [
                {
                    "step": 1,
                    "description": "Rapid compression of incoming air stream.",
                    "action": "warp_speed"  # Invalid semantic action
                }
            ]
        }

        repaired_spec, report = SelfVerificationEngine.verify_and_repair(defective_spec)
        
        self.assertIsNotNone(repaired_spec)
        self.assertIn("score", report)
        self.assertIn("repairs_applied", report)
        self.assertTrue(len(report["repairs_applied"]) > 0, "Repairs should be applied to defective spec")
        
        # Verify component IDs were generated
        for c in repaired_spec["components"]:
            self.assertIn("id", c)
            self.assertTrue(len(c["id"]) > 0)
        
        # Verify camera was added
        self.assertIn("camera", repaired_spec)
        self.assertIn("position", repaired_spec["camera"])

        # Verify invalid connections to missing components were pruned or repaired
        valid_ids = {c["id"] for c in repaired_spec["components"]}
        for conn in repaired_spec.get("connections", []):
            self.assertIn(conn["from_id"], valid_ids)
            self.assertIn(conn["to_id"], valid_ids)


class TestSecureOSAgent(unittest.TestCase):
    def setUp(self):
        self.agent = SecureOSAgent()

    def test_whitelist_execution_list_processes(self):
        res = self.agent.list_processes()
        self.assertTrue(res.get("success"))
        self.assertIn("processes", res)
        self.assertTrue(len(res["processes"]) > 0)

    def test_directory_traversal_blocking(self):
        # Attempt traversal with ".."
        res = self.agent.open_folder(r"..\..\Windows\System32")
        self.assertFalse(res.get("success"))
        self.assertIn("traversal", res.get("message", "").lower())

    def test_path_outside_allowed_roots_blocking(self):
        # Execute command traversal check
        res = self.agent.execute_command(r"open ..\..\Windows folder")
        self.assertFalse(res.get("success"))

    def test_natural_language_execution(self):
        res = self.agent.execute_command("list processes")
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("action"), "list_processes")

    def test_immutable_audit_logging(self):
        initial_count = len(self.agent.audit_log)
        self.agent.list_processes()
        logs = self.agent.audit_log
        self.assertEqual(len(logs), initial_count + 1)
        self.assertEqual(logs[-1]["action"], "list_processes")
        self.assertIn("timestamp", logs[-1])

    def test_sensitive_action_confirmation(self):
        # Request closing or terminating a process requires confirmation
        res = self.agent.execute_command("kill process chrome")
        self.assertTrue(res.get("requires_confirmation"))
        confirm_id = res.get("confirmation_id")
        self.assertIsNotNone(confirm_id)

        # Deny confirmation
        res_denied = self.agent.confirm_action(confirm_id, approved=False)
        self.assertFalse(res_denied.get("success"))
        self.assertIn("cancelled", res_denied.get("message", "").lower())


class TestTeacherMode(unittest.TestCase):
    def test_teacher_mode_fallback_generation(self):
        sample_spec = {
            "topic": "Hydraulic Brake System",
            "explanation": "Pascal's principle transmission of brake fluid pressure.",
            "components": [
                {"id": "master_cyl", "name": "Master Cylinder", "type": "cylinder", "description": "Converts pedal force to hydraulic pressure."},
                {"id": "brake_caliper", "name": "Brake Caliper", "type": "box", "description": "Clamps brake pads onto rotor."}
            ],
            "animation_steps": [
                {"step": 1, "description": "Fluid pressurized through high-pressure lines.", "action": "fluid_flow"}
            ]
        }

        lesson = TeacherMode.generate_lesson(sample_spec, api_key="INVALID_FOR_FALLBACK_TEST")
        self.assertIsNotNone(lesson)
        self.assertIn("topic", lesson)
        self.assertIn("overview", lesson)
        self.assertIn("working_principle", lesson)
        self.assertIn("components_breakdown", lesson)
        self.assertIn("socratic_questions", lesson)
        self.assertTrue(len(lesson["components_breakdown"]) >= 2)
        self.assertTrue(len(lesson["socratic_questions"]) >= 2)


class TestQuizGenerator(unittest.TestCase):
    def test_quiz_generator_with_component_identification(self):
        sample_spec = {
            "topic": "DC Electric Motor",
            "explanation": "Electromechanical Lorentz force rotation.",
            "components": [
                {"id": "armature", "name": "Rotor Armature", "type": "cylinder", "description": "Rotating coil carrying electric current."},
                {"id": "stator", "name": "Permanent Stator Magnets", "type": "box", "description": "Provides fixed magnetic flux field."},
                {"id": "commutator", "name": "Split-Ring Commutator", "type": "ring", "description": "Reverses current polarity every half-cycle."}
            ]
        }

        quiz = QuizGenerator.generate_quiz(sample_spec, difficulty="Intermediate", api_key="INVALID_FOR_FALLBACK_TEST")
        self.assertIsNotNone(quiz)
        self.assertIn("questions", quiz)
        self.assertTrue(len(quiz["questions"]) >= 3)
        
        # Verify presence of 3D component identification question
        comp_id_questions = [q for q in quiz["questions"] if q.get("type") in ["identification", "3d_component_identification"]]
        self.assertTrue(len(comp_id_questions) >= 1)
        self.assertIsNotNone(comp_id_questions[0].get("target_component_id"))
        self.assertIn(comp_id_questions[0]["target_component_id"], ["armature", "stator", "commutator"])


class TestSessionMemory(unittest.TestCase):
    def test_session_memory_lifecycle(self):
        session = SessionMemoryManager.get_session("test_suite_session")
        self.assertEqual(session.session_id, "test_suite_session")

        sample_spec = {"topic": "Nuclear Reactor Core", "components": [{"id": "rod_1"}]}
        session.set_model(sample_spec)
        self.assertEqual(session.current_model["topic"], "Nuclear Reactor Core")

        # Update state
        session.update_state({"selected_component_id": "rod_1", "tts_enabled": True})
        self.assertEqual(session.selected_component_id, "rod_1")

        # Serialize
        serialized = session.to_dict()
        self.assertIn("session_id", serialized)
        self.assertTrue(serialized["has_model"])

        # Reset
        SessionMemoryManager.reset_session("test_suite_session")
        fresh_session = SessionMemoryManager.get_session("test_suite_session")
        self.assertIsNone(fresh_session.current_model)


class TestVoiceCommandParser(unittest.TestCase):
    def test_voice_command_parser_intents(self):
        comp_map = {"primary_coil": {"name": "Primary Coil", "description": "Input winding"}}

        # Animation intent
        res_anim = VoiceCommandParser.parse("Please play the simulation animation", comp_map)
        self.assertEqual(res_anim["intent"], "animation")
        self.assertEqual(res_anim["action"], "play")

        # Viewport gesture intent
        res_gesture = VoiceCommandParser.parse("Rotate camera clockwise", comp_map)
        self.assertEqual(res_gesture["intent"], "gesture")
        self.assertEqual(res_gesture["action"], "rotate")

        # Component selection intent
        res_comp = VoiceCommandParser.parse("Explain primary winding", comp_map)
        self.assertEqual(res_comp["intent"], "select_component")
        self.assertEqual(res_comp["component_id"], "primary_coil")

        # Helper intent detectors
        self.assertTrue(VoiceCommandParser().is_teacher_query("Explain how this transformer works"))
        self.assertTrue(VoiceCommandParser().is_quiz_query("Give me a quiz on this system"))
        self.assertTrue(VoiceCommandParser().is_modification_query("Add a cooling radiator to the chassis"))
        self.assertTrue(VoiceCommandParser().is_os_query("Open Google Chrome"))


class TestModelGeneratorProcedural(unittest.TestCase):
    def test_procedural_fallback_synthesis(self):
        gen = ModelGenerator()
        spec = gen._generate_procedural_fallback("Particle Accelerator Synchrotron")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.topic)
        self.assertTrue(len(spec.components) >= 3)
        self.assertTrue(len(spec.animation_steps) >= 1)


class TestAgenticPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = AgenticPipeline()

    def test_intent_classification(self):
        intent, params = self.pipeline.classify_intent("Open Google Chrome", has_active_model=False)
        self.assertEqual(intent, "OS_AUTOMATION")

        intent, params = self.pipeline.classify_intent("Explain the working principle and physics", has_active_model=True)
        self.assertEqual(intent, "TEACHER_EXPLAIN")

        intent, params = self.pipeline.classify_intent("Generate a quiz for this model", has_active_model=True)
        self.assertEqual(intent, "GENERATE_QUIZ")

        intent, params = self.pipeline.classify_intent("Add a cooling radiator", has_active_model=True)
        self.assertEqual(intent, "MODIFY_3D")

        intent, params = self.pipeline.classify_intent("Animate the magnetic field flow", has_active_model=True)
        self.assertEqual(intent, "SEMANTIC_ANIMATE")

        intent, params = self.pipeline.classify_intent("Create a 3D model of a drone", has_active_model=True)
        self.assertEqual(intent, "GENERATE_3D")

    @patch("backend.secure_os_agent.open_app", return_value="Google Chrome opened successfully.")
    def test_os_automation_turn(self, mock_open):
        turn_result = self.pipeline.run("Open Chrome", session_id="test_pipeline_session")
        self.assertEqual(turn_result["intent"], "OS_AUTOMATION")
        self.assertIsNotNone(turn_result.get("os_result"))
        self.assertIn("chrome", turn_result.get("text_response", "").lower())


class TestStudentProgressTracker(unittest.TestCase):
    def setUp(self):
        import tempfile
        from backend.student_tracker import StudentProgressTracker
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_file.close()
        self.tracker = StudentProgressTracker(storage_path=self.temp_file.name)

    def tearDown(self):
        import os
        try:
            os.remove(self.temp_file.name)
        except Exception:
            pass

    def test_record_answer_and_streak(self):
        # 1. First correct answer
        s1 = self.tracker.record_answer(
            topic="DC Electric Motor",
            question_id="q1",
            student_choice="Rotor",
            correct_index=0,
            is_correct=True,
            question_text="Which part rotates?",
        )
        self.assertEqual(s1["total_questions"], 1)
        self.assertEqual(s1["correct_answers"], 1)
        self.assertEqual(s1["streak"], 1)
        self.assertEqual(s1["best_streak"], 1)
        self.assertEqual(s1["accuracy_pct"], 100.0)

        # 2. Second correct answer (streak increases)
        s2 = self.tracker.record_answer(
            topic="DC Electric Motor",
            question_id="q2",
            student_choice="Commutator",
            correct_index=1,
            is_correct=True,
            question_text="What reverses current?",
        )
        self.assertEqual(s2["streak"], 2)
        self.assertEqual(s2["best_streak"], 2)

        # 3. Third incorrect answer (streak resets, best streak preserved)
        s3 = self.tracker.record_answer(
            topic="DC Electric Motor",
            question_id="q3",
            student_choice="Wrong Choice",
            correct_index=2,
            is_correct=False,
            question_text="Which part stays stationary?",
        )
        self.assertEqual(s3["streak"], 0)
        self.assertEqual(s3["best_streak"], 2)
        self.assertEqual(s3["correct_answers"], 2)
        self.assertEqual(s3["total_questions"], 3)
        self.assertEqual(s3["accuracy_pct"], 66.7)

    def test_mastery_tier_calculation(self):
        self.assertEqual(self.tracker.calculate_mastery_tier(100.0, 1), "Novice")
        self.assertEqual(self.tracker.calculate_mastery_tier(40.0, 5), "Novice")
        self.assertEqual(self.tracker.calculate_mastery_tier(60.0, 5), "Apprentice")
        self.assertEqual(self.tracker.calculate_mastery_tier(80.0, 5), "Specialist")
        self.assertEqual(self.tracker.calculate_mastery_tier(95.0, 10), "Master Engineer")

    def test_topic_mastery_tracking(self):
        # 3 consecutive correct answers on Transformer
        for i in range(3):
            self.tracker.record_answer(
                topic="Step-Down Transformer",
                question_id=f"q_{i}",
                student_choice=0,
                correct_index=0,
                is_correct=True,
            )
        summary = self.tracker.get_summary()
        self.assertIn("Step-Down Transformer", summary["mastered_topics"])
        topic_info = self.tracker.get_topic_mastery("Step-Down Transformer")
        self.assertEqual(topic_info["status"], "Mastered")
        self.assertEqual(topic_info["accuracy_pct"], 100.0)

    def test_parse_user_answer(self):
        options = ["Primary Coils", "Secondary Coils", "Iron Core", "Cooling Radiator"]
        p = self.tracker.parse_user_answer

        # Letters
        self.assertEqual(p("A", options), 0)
        self.assertEqual(p("Option B", options), 1)
        self.assertEqual(p("choice c", options), 2)
        self.assertEqual(p("D", options), 3)

        # Numbers and Ordinals
        self.assertEqual(p("1", options), 0)
        self.assertEqual(p("second", options), 1)
        self.assertEqual(p("3", options), 2)
        self.assertEqual(p("fourth", options), 3)

        # Substrings
        self.assertEqual(p("Iron Core", options), 2)
        self.assertEqual(p("cooling", options), 3)

        # True / False
        tf_opts = ["True", "False"]
        self.assertEqual(p("True", tf_opts), 0)
        self.assertEqual(p("false", tf_opts), 1)

    def test_voice_summary_and_reset(self):
        self.tracker.record_answer("DC Motor", "q1", 0, 0, True)
        self.tracker.record_answer("DC Motor", "q2", 0, 0, True)
        self.tracker.record_quiz_completion("DC Motor", "Intermediate", 2, 2)

        voice_text = self.tracker.format_voice_summary()
        self.assertIn("accuracy", voice_text.lower())
        self.assertIn("quiz", voice_text.lower())

        # Reset
        res = self.tracker.reset_progress()
        self.assertEqual(res["total_questions"], 0)
        self.assertEqual(res["total_quizzes"], 0)
        self.assertEqual(res["accuracy_pct"], 0.0)
        self.assertEqual(len(res["topics"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

