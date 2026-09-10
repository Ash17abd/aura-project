"""
Production FastAPI Web Server for AURA 3D Learning Lab.

Connects the browser WebGL frontend to the existing Python application logic:
- Dynamic AI 3D Model Generation (Google Gemini & Procedural Geometry)
- ModelSpec Validation & Auto-Repair
- Study Material Text & Topic Extraction (PDF/DOCX/PPTX/TXT/CSV)
- Natural Language & Voice Command Parsing
- Contextual Learning Assistant Chat
- Safe System Telemetry
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import psutil
import requests
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from actions.aura_3d import _explain_topic, _read_material, _topics
from actions.example_prompts import ExamplePromptLibrary
from actions.image_search import search_diagram_images
from actions.model_generator import AIModelGenerator, ModelSpec
from actions.voice_parser import VoiceCommandParser
from backend.model_spec_schema import validate_and_repair_model_spec
from backend.agentic_pipeline import agentic_pipeline
from backend.self_verification import SelfVerificationEngine
from backend.secure_os_agent import secure_agent
from backend.session_memory import session_manager
from backend.teacher_mode import TeacherModeGenerator
from backend.quiz_generator import QuizGenerator
from backend.student_tracker import student_tracker

# Initialize FastAPI app
app = FastAPI(
    title="AURA 3D Learning Lab API",
    description="Production web backend for AURA 3D Learning Lab and AI Agent",
    version="2.0.0",
)

# Enable secure CORS with environment variable configuration
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
WEB_DIR.mkdir(parents=True, exist_ok=True)

START_TIME = time.time()
generator = AIModelGenerator()


# ---------- Request / Response Schemas ----------

class ModelGenerateRequest(BaseModel):
    prompt: str
    force_catalog: bool = False


class ModelModifyRequest(BaseModel):
    current_spec: dict[str, Any]
    instruction: str


class ModelAnimateRequest(BaseModel):
    current_spec: dict[str, Any]
    instruction: str


class VoiceParseRequest(BaseModel):
    text: str
    component_map: Optional[dict[str, Any]] = None


class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    model: Optional[str] = "gemini-3.5-flash-lite"
    document_context: Optional[str] = ""
    current_model_context: Optional[dict[str, Any]] = None
    level: Optional[str] = "Intermediate"


class AgentRunRequest(BaseModel):
    user_instruction: str
    session_id: Optional[str] = "default_user_session"


class TeacherExplainRequest(BaseModel):
    model_spec: dict[str, Any]
    level: Optional[str] = "Intermediate"


class ComponentExplainRequest(BaseModel):
    model_spec: dict[str, Any]
    component_id: str
    component_name: Optional[str] = None
    level: Optional[str] = "Intermediate"


class AnalyzeMaterialRequest(BaseModel):
    text: Optional[str] = None
    filename: Optional[str] = "document.txt"


class QuizGenerateRequest(BaseModel):
    model_spec: dict[str, Any]
    difficulty: Optional[str] = "Intermediate"



class OSExecuteRequest(BaseModel):
    command: str
    session_id: Optional[str] = "default"
    auth_token: Optional[str] = None


class ReferenceSearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 8


class ModelValidateRequest(BaseModel):
    model_spec: Optional[dict[str, Any]] = None


class OSConfirmRequest(BaseModel):
    confirmation_id: str
    approved: bool


class SessionUpdateRequest(BaseModel):
    session_id: Optional[str] = "default_user_session"
    updates: dict[str, Any]


class StudentRecordAnswerRequest(BaseModel):
    topic: str
    question_id: str
    student_choice: Any
    correct_index: int
    is_correct: bool
    question_text: Optional[str] = ""
    explanation: Optional[str] = ""
    difficulty: Optional[str] = "Intermediate"


class StudentRecordQuizRequest(BaseModel):
    topic: str
    difficulty: Optional[str] = "Intermediate"
    score: int
    total_questions: int
    details: Optional[list[dict[str, Any]]] = None



# ---------- Static Frontend Files ----------

@app.get("/")
async def serve_index():
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "AURA 3D Learning Lab API is running. Frontend bundle is loading."})


@app.get("/api/health")
def health_endpoint():
    """Production healthcheck returning service status, environment, and uptime."""
    return {
        "status": "ok",
        "service": "AURA",
        "environment": os.environ.get("ENVIRONMENT", "production"),
        "uptime_seconds": int(time.time() - START_TIME),
        "version": "2.0.0",
        "timestamp": time.time(),
    }



# ============================================================
# 1. PRIMARY AGENTIC PIPELINE ORCHESTRATOR
# ============================================================

@app.post("/api/agent/run")
def run_agent_endpoint(req: AgentRunRequest):
    """
    Primary autonomous agentic entry point.
    Executes complete end-to-end learning lifecycle:
    Voice/Text -> Intent -> Planning -> Schematics -> 3D Generation ->
    Verification -> Teacher Pedagogy -> Quiz Assessment -> OS Execution.
    """
    prompt = req.user_instruction.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="User instruction cannot be empty.")
    try:
        res = agentic_pipeline.run(prompt, session_id=req.session_id or "default_user_session")
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution error: {e}")


# ============================================================
# 2. 3D MODEL GENERATION, MODIFICATION & VERIFICATION
# ============================================================

@app.post("/api/model/generate")
@app.post("/api/generate-scene")
def generate_model_endpoint(req: ModelGenerateRequest):

    """
    Dynamically generates a 3D ModelSpec from natural language instructions.
    Pipeline: User Prompt -> AI Planning -> 8-Dimension Verification & Repair -> References -> Session Update.
    """
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Instruction prompt cannot be empty.")

    try:
        raw_spec = generator.generate_model(prompt, force_catalog=req.force_catalog)
        spec_dict = raw_spec.to_dict() if raw_spec else {"topic": prompt, "components": []}
        
        # 8-Dimension Self-Verification and Auto-Repair
        verified, report = SelfVerificationEngine.verify_and_repair(spec_dict)
        verified["verification_report"] = report

        # Search real-world reference images and diagrams
        try:
            ref_images = search_diagram_images(verified["topic"], max_results=6)
            if len(ref_images) < 2 and prompt.lower() != verified["topic"].lower():
                extra = search_diagram_images(prompt, max_results=4)
                for item in extra:
                    if not any(x.get("image") == item.get("image") for x in ref_images):
                        ref_images.append(item)
            verified["reference_images"] = ref_images
        except Exception:
            verified["reference_images"] = []

        # Synchronize continuous session state
        session = session_manager.get_or_create("default_user_session")
        session.set_model(verified, record_history=True)

        # Proactively generate interactive quiz for this model
        try:
            quiz = QuizGenerator.generate_quiz(verified, difficulty=session.difficulty)
            verified["quiz"] = quiz
            session.current_quiz = quiz
        except Exception as qe:
            print(f"[web_server] Quiz generation fallback: {qe}")
            verified["quiz"] = None

        return verified
    except Exception as e:
        fallback, rep = SelfVerificationEngine.verify_and_repair({"topic": prompt, "components": []})
        fallback["verification_report"] = rep
        try:
            fallback["reference_images"] = search_diagram_images(prompt, max_results=4)
        except Exception:
            fallback["reference_images"] = []
        return fallback


@app.post("/api/model/modify")
def modify_model_endpoint(req: ModelModifyRequest):
    """Contextually modifies an existing 3D model according to user instruction."""
    try:
        updated = generator.modify_model(req.current_spec, req.instruction)
        raw_dict = updated.to_dict() if updated else req.current_spec
        verified, report = SelfVerificationEngine.verify_and_repair(raw_dict)
        verified["verification_report"] = report
        verified["reference_images"] = req.current_spec.get("reference_images", [])

        session = session_manager.get_or_create("default_user_session")
        session.set_model(verified, record_history=True)
        return verified
    except Exception as e:
        return validate_and_repair_model_spec(req.current_spec)


@app.post("/api/model/animate")
def animate_model_endpoint(req: ModelAnimateRequest):
    """Generates or customizes semantic animation steps for a model."""
    try:
        steps = generator.generate_animation(req.current_spec, req.instruction)
        spec_copy = dict(req.current_spec)
        spec_copy["animation_steps"] = steps
        verified = validate_and_repair_model_spec(spec_copy)
        return {"animation_steps": verified["animation_steps"]}
    except Exception as e:
        return {"animation_steps": req.current_spec.get("animation_steps", [])}


@app.post("/api/model/validate")
def validate_model_endpoint(payload: dict[str, Any]):
    """
    Validates and auto-repairs a 3D ModelSpec against 8 structural dimensions.
    Returns verification report, validity flag, and repaired specification.
    """
    try:
        spec = payload.get("model_spec", payload)
        if not isinstance(spec, dict):
            raise HTTPException(status_code=400, detail="Invalid ModelSpec: payload must be a dictionary.")
        verified, report = SelfVerificationEngine.verify_and_repair(spec)
        return {
            "valid": report.get("valid", True),
            "score": report.get("score", 100.0),
            "verified_spec": verified,
            "verification_report": report,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Model validation error: {e}")


@app.get("/api/model/catalog/{topic}")
def get_catalog_model(topic: str):
    """Fetch a specific catalog model fixture."""
    match = generator._match_catalog(topic)
    if match:
        model = validate_and_repair_model_spec(match.to_dict())
    else:
        model = validate_and_repair_model_spec({"topic": topic})
    try:
        model["quiz"] = QuizGenerator.generate_quiz(model, difficulty="Intermediate")
    except Exception:
        pass
    return model


@app.get("/api/images/search")
def search_images_endpoint(query: str):
    """Search the web for real-world reference images, schematics, and diagrams."""
    try:
        images = search_diagram_images(query.strip(), max_results=8)
        return {"query": query, "images": images, "source": "Web Reference"}
    except Exception as e:
        return {"query": query, "images": [], "source": "Web Reference"}


@app.post("/api/reference/search")
def search_reference_post_endpoint(req: ReferenceSearchRequest):
    """Search web for real educational reference images, labeled distinctly from 3D models."""
    query = (req.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    try:
        images = search_diagram_images(query, max_results=req.max_results or 8)
        return {
            "query": query,
            "references": images,
            "images": images,
            "source": "Web Reference",
            "disclaimer": "Real-world web reference diagrams for conceptual comparison. 3D model is autonomously generated by AURA.",
        }
    except Exception as e:
        return {"query": query, "references": [], "images": [], "source": "Web Reference", "error": str(e)}


@app.get("/api/reference/search")
def search_reference_get_endpoint(query: str, max_results: Optional[int] = 8):
    """GET alias for educational reference search."""
    q = (query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    try:
        images = search_diagram_images(q, max_results=max_results or 8)
        return {
            "query": q,
            "references": images,
            "images": images,
            "source": "Web Reference",
            "disclaimer": "Real-world web reference diagrams for conceptual comparison. 3D model is autonomously generated by AURA.",
        }
    except Exception as e:
        return {"query": q, "references": [], "images": [], "source": "Web Reference", "error": str(e)}




# ============================================================
# 3. AI TEACHER MODE & INTERACTIVE QUIZ LAB
# ============================================================

@app.post("/api/teacher/explain")
def teacher_explain_endpoint(req: TeacherExplainRequest):
    """Generates comprehensive structured educational lesson from a ModelSpec."""
    try:
        lesson = TeacherModeGenerator.generate_lesson(req.model_spec, level=req.level or "Intermediate")
        session = session_manager.get_or_create("default_user_session")
        session.current_lesson = lesson
        return lesson
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Teacher mode generation error: {e}")


@app.post("/api/explain-component")
def explain_component_endpoint(req: ComponentExplainRequest):
    """Deep contextual explanation of a specific selected 3D component."""
    try:
        explanation = TeacherModeGenerator.explain_component(
            model_spec=req.model_spec,
            component_id=req.component_id,
            component_name=req.component_name,
            level=req.level or "Intermediate",
        )
        return explanation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Component explanation error: {e}")


@app.post("/api/quiz/generate")
@app.post("/api/quiz")
def quiz_generate_endpoint(req: QuizGenerateRequest):
    """Generates an interactive model-specific quiz."""
    try:
        quiz = QuizGenerator.generate_quiz(req.model_spec, difficulty=req.difficulty or "Intermediate")
        session = session_manager.get_or_create("default_user_session")
        session.current_quiz = quiz
        return quiz
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quiz generation error: {e}")


@app.get("/api/assessment")
@app.post("/api/assessment")
def assessment_endpoint():
    """Unified assessment and mastery report with weak concept identification and 3D review links."""
    return student_tracker.get_assessment_report()


@app.get("/api/student/progress")
def student_progress_endpoint():
    """Returns the current student learning progress, accuracy, and topic mastery."""
    return student_tracker.get_summary()



@app.post("/api/student/record-answer")
def student_record_answer_endpoint(req: StudentRecordAnswerRequest):
    """Records an answered question and updates student learning metrics."""
    return student_tracker.record_answer(
        topic=req.topic,
        question_id=req.question_id,
        student_choice=req.student_choice,
        correct_index=req.correct_index,
        is_correct=req.is_correct,
        question_text=req.question_text or "",
        explanation=req.explanation or "",
        difficulty=req.difficulty or "Intermediate",
    )


@app.post("/api/student/record-quiz")
def student_record_quiz_endpoint(req: StudentRecordQuizRequest):
    """Records full quiz completion with score and accuracy."""
    return student_tracker.record_quiz_completion(
        topic=req.topic,
        difficulty=req.difficulty or "Intermediate",
        score=req.score,
        total_questions=req.total_questions,
        details=req.details,
    )


@app.post("/api/student/reset")
def student_reset_endpoint():
    """Resets student tracking data."""
    return student_tracker.reset_progress()


# ============================================================
# 4. VISUAL UNDERSTANDING (IMAGE TO 3D MODEL)
# ============================================================

@app.post("/api/vision/analyze-3d")
async def vision_analyze_endpoint(
    file: UploadFile = File(...),
    instruction: Optional[str] = "",
    session_id: Optional[str] = "default_user_session",
):
    """
    Visual Understanding: Analyzes uploaded blueprint, schematic, or diagram
    and synthesizes an interactive 3D model.
    """
    try:
        content = await file.read()
        mime = file.content_type or "image/jpeg"
        res = agentic_pipeline.run(
            user_instruction=instruction or f"Reconstruct 3D model from diagram {file.filename}",
            session_id=session_id or "default_user_session",
            image_bytes=content,
            mime_type=mime,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision analysis error: {e}")


# ============================================================
# 5. SECURE LOCAL OS AUTOMATION
# ============================================================

@app.post("/api/os/execute")
def os_execute_endpoint(req: OSExecuteRequest):
    """Executes a validated, safe local OS operation via strict whitelist."""
    if os.getenv("AURA_CLOUD_DEPLOYED") == "1" or os.getenv("AURA_DISABLE_LOCAL_OS") == "1":
        return {
            "success": False,
            "status": "OFFLINE",
            "message": "Local OS Agent is offline. To control your local computer, run AURA desktop locally.",
        }
    if os.getenv("AURA_REQUIRE_OS_AUTH") == "1":
        if not secure_agent.validate_auth(req.auth_token):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Valid Local Agent authentication token is required.",
            )
    try:
        res = secure_agent.execute_command(
            req.command, session_id=req.session_id or "default", auth_token=req.auth_token
        )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OS execution error: {e}")


@app.post("/api/os/confirm")
def os_confirm_endpoint(req: OSConfirmRequest):
    """Confirms or rejects a pending sensitive OS action."""
    try:
        res = secure_agent.confirm_action(req.confirmation_id, req.approved)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Confirmation error: {e}")


@app.get("/api/os/status")
def os_status_endpoint():
    """Returns local secure agent capabilities, telemetry, and recent audit log."""
    status = secure_agent.get_status()
    if os.getenv("AURA_CLOUD_DEPLOYED") == "1" or os.getenv("AURA_DISABLE_LOCAL_OS") == "1":
        status["status"] = "OFFLINE"
        status["mode"] = "cloud"
        status["message"] = "Local OS Agent is offline (Cloud Mode). Run desktop agent for local actions."
    else:
        status["mode"] = "local"
    return status



# ============================================================
# 6. PERSISTENT SESSION MEMORY
# ============================================================

@app.get("/api/session/state")
def get_session_state(session_id: Optional[str] = "default_user_session"):
    """Returns stateful session memory."""
    session = session_manager.get_or_create(session_id)
    return session.to_dict()


@app.post("/api/session/update")
def update_session_state(req: SessionUpdateRequest):
    """Updates active session memory."""
    session = session_manager.get_or_create(req.session_id)
    session.update_state(req.updates)
    return session.to_dict()


@app.post("/api/session/reset")
async def reset_session_state(session_id: Optional[str] = "default_user_session"):
    """Resets session memory."""
    session = session_manager.reset_session(session_id)
    return session.to_dict()



# ---------- Example Prompts Library ----------

@app.get("/api/examples")
async def get_examples():
    """Return categorized example prompts for student exploration."""
    categories: dict[str, list[dict[str, str]]] = {}
    for ex in ExamplePromptLibrary.EXAMPLES:
        cat = ex.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "title": ex.title,
            "prompt": ex.prompt,
            "description": ex.description,
            "difficulty": ex.difficulty,
        })
    return {"categories": categories, "total": len(ExamplePromptLibrary.EXAMPLES)}


# ---------- Reading & Document Intelligence ----------

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md", ".csv", ".json", ".html"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


@app.post("/api/reading/extract")
async def extract_reading_endpoint(file: UploadFile = File(...)):
    """
    Extracts text from uploaded study material (PDF, DOCX, PPTX, TXT, CSV),
    identifies key educational topics, and provides 3D generation targets.
    Enforces maximum 25MB file upload limit with safe temporary storage.
    """
    filename = file.filename or "uploaded_document.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Supported: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check Content-Length or size attribute up-front if available
    if hasattr(file, "size") and file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of 25MB (got {file.size / (1024*1024):.1f}MB).",
        )

    # Write securely to temporary file with stream-size enforcement
    temp_dir = Path(tempfile.gettempdir()) / "aura_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / f"reading_{int(time.time())}_{Path(filename).name}"

    try:
        total_bytes = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        with open(temp_file, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds maximum allowed size of 25MB.",
                    )
                buffer.write(chunk)

        extracted_text = _read_material(str(temp_file))
        topics_list = _topics(extracted_text)

        formatted_topics = []
        for topic_name, explanation in topics_list:
            formatted_topics.append({
                "topic": topic_name,
                "explanation": explanation,
            })

        return {
            "filename": filename,
            "char_count": len(extracted_text),
            "text_preview": extracted_text[:1000] + ("..." if len(extracted_text) > 1000 else ""),
            "full_text": extracted_text[:25000],
            "topics": formatted_topics,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


@app.post("/api/analyze-material")
def analyze_material_endpoint(req: AnalyzeMaterialRequest):
    """Unified study material text and concept extraction endpoint."""
    txt = (req.text or "").strip()
    if not txt:
        raise HTTPException(status_code=400, detail="Text content cannot be empty.")
    topics_list = _topics(txt)
    formatted_topics = [{"topic": t, "explanation": exp} for t, exp in topics_list]
    primary_topic = formatted_topics[0]["topic"] if formatted_topics else "Engineering Concept"
    return {
        "status": "success",
        "filename": req.filename or "direct_text.txt",
        "char_count": len(txt),
        "text_preview": txt[:1000] + ("..." if len(txt) > 1000 else ""),
        "full_text": txt[:25000],
        "topics": formatted_topics,
        "key_concepts": [t["topic"] for t in formatted_topics] if formatted_topics else ["Engineering Principles"],
        "recommended_3d_model": primary_topic,
        "visualization_plan": f"Constructing interactive 3D model representation for {primary_topic}.",
        "source": "Text/Document Analysis"
    }


# ---------- Natural Language & Voice Command Parser ----------

@app.post("/api/voice/parse")
@app.post("/api/voice")
def parse_voice_endpoint(req: VoiceParseRequest):
    """
    Parses voice or text commands for component Q&A, animations, and viewport gestures.
    """

    parser = VoiceCommandParser(component_map=req.component_map or {})
    text = req.text.strip()

    # 1. Check animation commands (play, pause, next, previous, reset)
    anim_cmd = parser.parse_animation_command(text)
    if anim_cmd:
        return {"intent": "animation", "action": anim_cmd, "raw": text}

    # 2. Check component inspection queries ("explain primary winding")
    if parser.is_component_query(text):
        comp_id = parser.parse_component_query(text)
        if comp_id:
            return {"intent": "select_component", "component_id": comp_id, "raw": text}

    # 3. Check gesture commands ("rotate", "zoom in", "zoom out", "reset")
    gesture_cmd = parser.parse_gesture_command(text)
    if gesture_cmd:
        return {"intent": "gesture", "action": gesture_cmd, "raw": text}

    # 4. Check quiz queries ("quiz", "give me a quiz", "test me", "option quiz")
    if parser.is_quiz_query(text) or any(w in text.lower() for w in ["quiz", "test me", "take a quiz", "option quiz", "question me", "assessment"]):
        return {"intent": "generate_quiz", "raw": text}

    # 5. Check teacher queries ("teach me", "explain how this works")
    if parser.is_teacher_query(text) or any(w in text.lower() for w in ["teach me", "teacher mode", "lesson", "socratic", "how does it work"]):
        return {"intent": "teacher_explain", "raw": text}

    # 6. Check model generation intent ("create", "build", "visualize", "show")
    low = text.lower()
    create_triggers = ["create a 3d model", "create 3d model", "build a 3d", "visualize", "make a 3d", "generate a 3d"]
    if any(t in low for t in create_triggers):
        clean_prompt = text
        for t in create_triggers:
            clean_prompt = clean_prompt.replace(t, "").strip()
        return {"intent": "generate_model", "prompt": clean_prompt or text, "raw": text}

    return {"intent": "chat", "raw": text}


# ---------- Contextual AURA Learning Assistant Chat ----------

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """
    Conversational learning assistant maintaining context of the active 3D model,
    selected components, uploaded reading, and user questions.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        from config import get_config
        api_key = get_config().get("gemini_api_key", "")

    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured on the server.")

    # Formulate contextual system instructions
    system_text = (
        "You are AURA, an elite interactive 3D science and engineering learning assistant. "
        "You are accurate, clear, engaging, and directly connect explanations to 3D spatial components. "
    )

    pedagogy_level = (req.level or "Intermediate").lower()
    if pedagogy_level == "beginner":
        system_text += "\nPEDAGOGY MODE: BEGINNER. Use intuitive analogies, simple language, and everyday conceptual examples.\n"
    elif pedagogy_level == "advanced":
        system_text += "\nPEDAGOGY MODE: ADVANCED. Use rigorous equations, physical laws, engineering tolerances, and scientific precision.\n"
    elif pedagogy_level == "socratic":
        system_text += "\nPEDAGOGY MODE: SOCRATIC. Do NOT immediately lecture or give answers. Ask guiding questions that lead the student to deduce the underlying mechanism.\n"
    else:
        system_text += "\nPEDAGOGY MODE: INTERMEDIATE. Balance technical accuracy with clear explanations of component roles and systemic interactions.\n"

    if req.current_model_context:
        topic = req.current_model_context.get("topic", "System")
        components = [c.get("name", "") for c in req.current_model_context.get("components", [])]
        system_text += f"\nACTIVE 3D MODEL: {topic}\nCOMPONENTS IN 3D VIEW: {', '.join(components[:12])}\n"


    if req.document_context:
        system_text += f"\nUPLOADED STUDY MATERIAL CONTEXT:\n{req.document_context[:8000]}\n"

    contents = []
    for m in req.messages:
        role = "model" if m.get("role") in ("assistant", "model") else "user"
        contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

    if not contents:
        contents = [{"role": "user", "parts": [{"text": "Hello AURA!"}]}]

    payload = {
        "system_instruction": {"parts": [{"text": system_text}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.4},
    }

    model_to_use = req.model or "gemini-3.5-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_to_use}:generateContent?key={api_key}"

    try:
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code in (503, 429) and model_to_use != "gemini-3.5-flash-lite":
            # Fallback to flash-lite on upstream spikes
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
            resp = requests.post(fallback_url, json=payload, timeout=60)

        resp.raise_for_status()
        data = resp.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
        return {"response": text, "model_used": model_to_use}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI model inference error: {e}")


# ---------- Safe System Telemetry ----------

@app.get("/api/telemetry")
async def telemetry_endpoint():
    """Returns safe application and host telemetry for the AURA HUD."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        net = psutil.net_io_counters()
        uptime_sec = int(time.time() - START_TIME)
        return {
            "status": "ONLINE",
            "cpu_percent": cpu,
            "ram_percent": mem,
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "uptime_seconds": uptime_sec,
            "engine": "FastAPI + Three.js WebGL",
        }
    except Exception:
        return {"status": "ONLINE", "cpu_percent": 12.0, "ram_percent": 35.0}


# Mount static assets directory
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


# SPA catch-all for clean HTML5 frontend navigation
@app.get("/{full_path:path}")
async def serve_spa_fallback(full_path: str):
    """Serves static file if it exists, otherwise falls back to index.html for SPA."""
    file_path = WEB_DIR / full_path
    if file_path.is_file():
        return FileResponse(str(file_path))
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Page not found")



if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8501))
    print("=" * 60)
    print(" Starting AURA 3D Learning Lab Production Web Server")
    print(f" Local URL:   http://localhost:{port}")
    print(f" Network URL: http://0.0.0.0:{port}")
    print(f" Web Assets:  {WEB_DIR}")
    print("=" * 60)
    uvicorn.run("web_server:app", host="0.0.0.0", port=port, reload=False)
