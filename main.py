import asyncio
import threading
import json
import sys
import traceback
from pathlib import Path

# Ensure UTF-8 console output on Windows to prevent UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import sounddevice as sd
import google
from google.genai import types
from ui import AuraUI, AureUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
    should_extract_memory, extract_memory
)


from actions.file_processor import file_processor
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import screen_process
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater
from actions.aura_3d           import open_3d_lab
from actions.model_generator   import AIModelGenerator
from actions.lab_ui_components import ExamplePromptsBrowser, VoiceCommandWidget, OptionQuizDialog
from backend.student_tracker import student_tracker
from backend.quiz_generator import QuizGenerator



def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are AURA, an AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )
    
_last_memory_input = ""

def _update_memory_async(user_text: str, aura_text: str) -> None:
    global _last_memory_input

    user_text   = (user_text   or "").strip()
    aura_text = (aura_text or "").strip()

    if len(user_text) < 5 or user_text == _last_memory_input:
        return
    _last_memory_input = user_text

    try:
        api_key = _get_api_key()
        if not should_extract_memory(user_text, aura_text, api_key):
            return
        data = extract_memory(user_text, aura_text, api_key)
        if data:
            update_memory(data)
            print(f"[Memory] ✅ {list(data.keys())}")
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] ⚠️ {e}")

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": (
            "Opens any application on the Windows computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Windows Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls the computer: volume, brightness, window management, keyboard shortcuts, "
            "typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, "
            "scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. "
            "Use for ANY single computer control command. NEVER route to agent_task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": (
            "Controls the web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, any web-based task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | press | close"},
                "url":         {"type": "STRING", "description": "URL for go_to action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up or down for scroll"},
                "key":         {"type": "STRING", "description": "Key name for press action"},
                "incognito":   {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Executes complex multi-step tasks requiring multiple different tools. "
            "Examples: 'research X and save to file', 'find and organize files'. "
            "DO NOT use for single commands. NEVER use for Steam/Epic — use game_updater."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "open_3d_lab",
        "description": (
            "Opens AURA 3D Learning Lab with interactive 3D models. Use when the user asks to:\n"
            "• Create, show, or explain a 3D model/diagram\n"
            "• Visualize a concept, system, or device (e.g., 'Show me a transformer', 'Create a hydraulic brake')\n"
            "• Generate a 3D diagram from uploaded reading material\n"
            "The lab creates interactive 3D diagrams, explains each component, and enables webcam hand gestures "
            "to rotate, zoom, switch diagrams, and reset the view.\n"
            "MODES: user_instruction (AI-generated model), file-based (from uploaded reading), or topic-specific."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_instruction": {"type": "STRING", "description": "Natural language instruction to create a custom 3D model (e.g., 'Create a transformer', 'Show a hydraulic brake system'). When provided, uses AI to generate the model dynamically."},
                "file_path": {"type": "STRING", "description": "Optional reading file path; leave empty to use uploaded file"},
                "topic": {"type": "STRING", "description": "Optional topic to visualize from reading"},
                "text": {"type": "STRING", "description": "Optional short reading/topic text"}
            },
            "required": []
        }
    },
    {
        "name": "browse_3d_examples",
        "description": (
            "Opens the AURA 3D Example Browser to browse and create models from pre-built example prompts.\n"
            "Use when user asks to:\n"
            "• See example 3D models\n"
            "• Browse available topics\n"
            "• Get suggestions for visualization\n"
            "• Create a model from category (e.g., 'electrical engineering', 'biology')\n"
            "Provides 20+ ready-to-use examples across engineering, physics, chemistry, and biology."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING", "description": "Optional category filter: Electrical Engineering, Mechanical Engineering, Biology, Physics, Chemistry, Civil Engineering"},
                "difficulty": {"type": "STRING", "description": "Optional difficulty level: beginner, intermediate, advanced"},
                "keyword": {"type": "STRING", "description": "Optional keyword to search examples"}
            },
            "required": []
        }
    },
    {
        "name": "option_quiz",
        "description": (
            "Starts an interactive multiple-choice option quiz on any engineering, science, or physics topic, "
            "evaluates student answers, and tracks the student's learning progress and mastery level.\n"
            "Use when user asks to:\n"
            "• Take a quiz or test knowledge (e.g., 'give me a quiz on transformers', 'option quiz', 'start quiz')\n"
            "• Submit an answer to a question (e.g., 'Option A', 'Choice B', 'The answer is 1', 'True')\n"
            "• Check learning process/progress (e.g., 'How am I doing?', 'Show my quiz progress', 'Track student progress')\n"
            "• Reset quiz progress"
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "start | answer | view_progress | reset (default: start)"
                },
                "topic": {
                    "type": "STRING",
                    "description": "Subject or 3D model topic for the quiz, e.g., 'Step-Down Electrical Transformer', 'DC Motor', 'Photosynthesis'"
                },
                "difficulty": {
                    "type": "STRING",
                    "description": "Difficulty tier: Beginner, Intermediate, Advanced (default: Intermediate)"
                },
                "answer": {
                    "type": "STRING",
                    "description": "The student's option answer (e.g., 'A', 'Option 2', 'True', or component text)"
                },
                "question_index": {
                    "type": "INTEGER",
                    "description": "Optional question index (1-based or 0-based)"
                }
            },
            "required": []
        }
    },
    {
        "name": "gesture_control",
        "description": (
            "Controls webcam hand gestures for rotating, zooming, and interacting with 3D models in AURA 3D Learning Lab.\n"
            "Use when user asks to:\n"
            "• Enable, start, or toggle webcam hand gestures (e.g., 'through hand gestures we can move the 3d models', 'enable gestures', 'start hand tracking')\n"
            "• Rotate, zoom in, zoom out, or reset 3D models using hand gesture tracking\n"
            "• Inquire how to control 3D models using hand gestures"
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "toggle | start | stop | status (default: toggle)"
                }
            },
            "required": []
        }
    },
    {
        "name": "game_updater",
        "description": (
            "THE ONLY tool for ANY Steam or Epic Games request. "
            "Use for: installing, downloading, updating games, listing installed games, "
            "checking download status, scheduling updates. "
            "ALWAYS call directly for any Steam/Epic/game request. "
            "NEVER use agent_task, browser_control, or web_search for Steam/Epic."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
    "name": "file_processor",
    "description": (
        "Processes any file that the user has uploaded or dropped onto the interface. "
        "Use this when the user refers to an uploaded file and wants an action on it. "
        "Supports: images (describe/ocr/resize/compress/convert), "
        "PDFs (summarize/extract_text/to_word), "
        "Word docs & text files (summarize/fix/reformat/translate), "
        "CSV/Excel (analyze/stats/filter/sort/convert), "
        "JSON/XML (validate/format/analyze), "
        "code files (explain/review/fix/optimize/run/document/test), "
        "audio (transcribe/trim/convert/info), "
        "video (trim/extract_audio/extract_frame/compress/transcribe/info), "
        "archives (list/extract), "
        "presentations (summarize/extract_text). "
        "ALWAYS call this tool when a file has been uploaded and the user gives a command about it. "
        "If the user's command is ambiguous, pick the most logical action for that file type."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
            },
            "action": {
                "type": "STRING",
                "description": (
                    "What to do with the file. Examples by type:\n"
                    "image: describe | ocr | resize | compress | convert | info\n"
                    "pdf: summarize | extract_text | to_word | info\n"
                    "docx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\n"
                    "csv/excel: analyze | stats | filter | sort | convert | info\n"
                    "json: validate | format | analyze | to_csv\n"
                    "code: explain | review | fix | optimize | run | document | test\n"
                    "audio: transcribe | trim | convert | info\n"
                    "video: trim | extract_audio | extract_frame | compress | transcribe | info | convert\n"
                    "archive: list | extract\n"
                    "pptx: summarize | extract_text | analyze"
                )
            },
            "instruction": {
                "type": "STRING",
                "description": "Free-form instruction if action doesn't cover it. E.g. 'translate this to Turkish', 'find all email addresses'"
            },
            "format": {
                "type": "STRING",
                "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
            },
            "width":     {"type": "INTEGER", "description": "Target width for image resize"},
            "height":    {"type": "INTEGER", "description": "Target height for image resize"},
            "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
            "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
            "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
            "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
            "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
            "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
            "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
            "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
            "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
            "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
            "destination": {"type": "STRING", "description": "Output folder for archive extract"},
        },
        "required": []
    }
},
    {
    "name": "shutdown_aura",
    "description": (
        "Shuts down the assistant completely. "
        "Call this when the user expresses intent to end the conversation, "
        "close the assistant, say goodbye, or stop AURA. "
        "The user can say this in ANY language."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
    },
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving — just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
]


class AuraLive:

    def __init__(self, ui: AuraUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command
        self.ui._speak = self.speak
        if hasattr(self.ui, "_win") and self.ui._win:
            self.ui._win._speak = self.speak
        self._active_voice_quiz = None
        self._active_voice_q_index = 0


    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon"
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[AURA] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")
        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."

            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."

            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(
                    None,
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Done."


            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."

            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result   = f"Task started (ID: {task_id})."

            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "open_3d_lab":
                # --- Step 1: AI model generation runs in executor (background thread) ---
                def _generate_3d_model():
                    if not args.get("file_path") and self.ui.current_file:
                        args["file_path"] = self.ui.current_file

                    user_instruction = args.get("user_instruction") or args.get("topic") or args.get("text")
                    file_path = args.get("file_path")
                    model_spec = None

                    # Extract reading text if file is uploaded
                    reading_content = ""
                    if file_path:
                        from actions.aura_3d import _read_material
                        reading_content = _read_material(file_path)
                        if reading_content.startswith("The reading file") or reading_content.startswith("No reading") or reading_content.startswith("Could not read"):
                            reading_content = ""

                    # Prepare prompt for model generator if instruction or reading is present
                    prompt_for_ai = ""
                    if user_instruction and reading_content:
                        prompt_for_ai = f"Create an educational 3D model based on this uploaded reading:\n\n{reading_content[:4000]}\n\nSpecific Instruction: {user_instruction}"
                    elif reading_content:
                        prompt_for_ai = f"Create an educational 3D model visualizing the key concepts in this uploaded reading:\n\n{reading_content[:4000]}"
                    elif user_instruction:
                        prompt_for_ai = user_instruction

                    if prompt_for_ai:
                        print(f"[AURA] 🎨 Generating 3D model from prompt: {prompt_for_ai[:80]}...")
                        self.ui.write_log(f"Generating 3D model...")
                        generator = AIModelGenerator()
                        model_spec = generator.generate_model(prompt_for_ai)
                        if model_spec:
                            print(f"[AURA] ✅ Model generated: {model_spec.topic}")
                            self.ui.write_log(f"Generated 3D model: {model_spec.topic}")

                    return model_spec

                # Run AI generation in background thread
                model_spec_result = await loop.run_in_executor(None, _generate_3d_model)

                # --- Step 2: Qt window creation MUST happen on the main GUI thread ---
                import threading as _threading
                _done_event = _threading.Event()
                _lab_result = [None]

                def _open_lab_on_main_thread():
                    try:
                        _lab_result[0] = open_3d_lab(
                            parameters=args, player=self.ui,
                            speak=self.speak, model_spec=model_spec_result
                        )
                    except Exception as _e:
                        print(f"[AURA] ❌ 3D Lab open error: {_e}")
                        _lab_result[0] = f"Error opening 3D lab: {_e}"
                    finally:
                        _done_event.set()

                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, _open_lab_on_main_thread)
                await loop.run_in_executor(None, _done_event.wait)
                result = _lab_result[0] or "3D Learning Lab opened."

            elif name == "browse_3d_examples":
                # Qt widget creation must be on main thread
                import threading as _threading
                _done_event_ex = _threading.Event()

                def _open_browser_on_main_thread():
                    try:
                        def on_example_selected(prompt):
                            print(f"[AURA] 📚 User selected example: {prompt[:50]}...")
                            # Generate model in background, open lab on main thread
                            def _gen_and_open():
                                generator = AIModelGenerator()
                                model_spec = generator.generate_model(prompt)
                                if model_spec:
                                    _ev = _threading.Event()
                                    def _show():
                                        try:
                                            open_3d_lab(model_spec=model_spec, speak=self.speak)
                                            print(f"[AURA] ✅ Example model created: {model_spec.topic}")
                                        finally:
                                            _ev.set()
                                    from PyQt6.QtCore import QTimer as _QT
                                    _QT.singleShot(0, _show)
                                    _ev.wait(timeout=10)
                            _threading.Thread(target=_gen_and_open, daemon=True).start()

                        browser = ExamplePromptsBrowser(on_select_callback=on_example_selected)
                        browser.show()
                    except Exception as _e:
                        print(f"[AURA] ❌ Examples browser error: {_e}")
                    finally:
                        _done_event_ex.set()

                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, _open_browser_on_main_thread)
                await loop.run_in_executor(None, _done_event_ex.wait)
                result = "3D Examples Browser opened."

            elif name in ("option_quiz", "student_quiz"):
                action = (args.get("action") or "start").lower()
                topic = args.get("topic") or "Step-Down Electrical Transformer"
                difficulty = args.get("difficulty") or "Intermediate"
                answer_input = args.get("answer") or ""

                if action in ("view_progress", "progress", "status", "track"):
                    report = student_tracker.format_voice_summary()
                    self.ui.write_log(f"STUDENT PROGRESS: {report}")
                    self.speak(report)
                    result = report

                elif action == "reset":
                    student_tracker.reset_progress()
                    msg = "Student quiz progress and learning history have been reset."
                    self.ui.write_log(f"STUDENT PROGRESS: {msg}")
                    self.speak(msg)
                    result = msg

                elif action in ("answer", "submit"):
                    active_quiz = getattr(self, "_active_voice_quiz", None)
                    q_idx = getattr(self, "_active_voice_q_index", 0)

                    if not active_quiz or not active_quiz.get("questions"):
                        msg = f"No quiz is currently active. Say 'start quiz on {topic}' to begin."
                        self.speak(msg)
                        result = msg
                    else:
                        questions = active_quiz["questions"]
                        if q_idx >= len(questions):
                            msg = "All questions in this quiz have already been completed. Say 'start quiz' to take a new one."
                            self.speak(msg)
                            result = msg
                        else:
                            curr_q = questions[q_idx]
                            options = curr_q.get("options", [])
                            selected_idx = student_tracker.parse_user_answer(answer_input, options)
                            correct_idx = curr_q.get("correct_index", 0)

                            if selected_idx is None:
                                msg = f"I didn't catch which option you chose. Please select an option: {', '.join(options)}."
                                self.speak(msg)
                                result = msg
                            else:
                                is_correct = (selected_idx == correct_idx)
                                expl = curr_q.get("explanation", "")
                                student_tracker.record_answer(
                                    topic=active_quiz.get("topic", topic),
                                    question_id=curr_q.get("id", f"q_{q_idx}"),
                                    student_choice=options[selected_idx] if selected_idx < len(options) else str(selected_idx),
                                    correct_index=correct_idx,
                                    is_correct=is_correct,
                                    question_text=curr_q.get("question", ""),
                                    explanation=expl,
                                    difficulty=active_quiz.get("difficulty", difficulty),
                                )
                                self._active_voice_q_index += 1
                                next_idx = self._active_voice_q_index

                                if is_correct:
                                    feedback = f"Correct! {expl}"
                                else:
                                    correct_text = options[correct_idx] if correct_idx < len(options) else str(correct_idx)
                                    feedback = f"Incorrect. The correct answer was option {chr(65 + correct_idx)}: {correct_text}. {expl}"

                                if next_idx < len(questions):
                                    next_q = questions[next_idx]
                                    next_opts = " ".join([f"Option {chr(65 + i)}: {opt}." for i, opt in enumerate(next_q.get("options", []))])
                                    feedback += f" Next question: {next_q.get('question')} {next_opts}"
                                else:
                                    summary = student_tracker.get_summary()
                                    feedback += f" Quiz finished! Your updated rank is {summary.get('mastery_tier', 'Novice')} with {summary.get('accuracy_pct', 0.0)}% overall accuracy."

                                self.ui.write_log(f"QUIZ ANSWER: {feedback[:100]}")
                                self.speak(feedback)
                                result = feedback

                else:
                    self.ui.write_log(f"Generating option quiz for {topic} ({difficulty})...")
                    from actions.aura_3d import _active_lab
                    active_spec = None
                    if _active_lab and hasattr(_active_lab, "model_spec"):
                        active_spec = _active_lab.model_spec
                    if not active_spec:
                        try:
                            from backend.agentic_pipeline import AgenticPipeline
                            gen_res = AgenticPipeline().synthesizer.generate_model(topic)
                            active_spec = gen_res.model_spec.model_dump() if gen_res and gen_res.model_spec else {"topic": topic, "components": []}
                        except Exception:
                            active_spec = {"topic": topic, "components": []}

                    quiz = QuizGenerator.generate_quiz(active_spec, difficulty=difficulty)
                    self._active_voice_quiz = quiz
                    self._active_voice_q_index = 0

                    questions = quiz.get("questions", [])
                    first_q = questions[0] if questions else None

                    # Open PyQt OptionQuizDialog on the main GUI thread
                    import threading as _threading
                    _dialog_done = _threading.Event()
                    def _open_quiz_dialog_on_main():
                        try:
                            dlg = OptionQuizDialog(
                                quiz_data=quiz,
                                speak=self.speak,
                                parent=getattr(self.ui, "_win", None),
                            )
                            dlg.show()
                        except Exception as _ex:
                            print(f"[AURA] ⚠️ Quiz dialog error: {_ex}")
                        finally:
                            _dialog_done.set()

                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, _open_quiz_dialog_on_main)

                    if first_q:
                        opt_str = " ".join([f"Option {chr(65 + i)}: {o}." for i, o in enumerate(first_q.get("options", []))])
                        speech_msg = (
                            f"Starting {difficulty} option quiz on {topic}. "
                            f"Question 1: {first_q.get('question')} {opt_str}"
                        )
                        self.speak(speech_msg)
                        result = speech_msg
                    else:
                        result = f"Option quiz created for {topic}."

            elif name in ("gesture_control", "toggle_gestures", "hand_gestures"):
                act = str(args.get("action", "toggle")).lower()
                import time as _time
                from actions.aura_3d import _active_lab, open_3d_lab
                lab = _active_lab
                if not lab:
                    # Open 3D learning lab first
                    open_3d_lab(player=self.ui, speak=self.speak)
                    await asyncio.sleep(1.0)
                    from actions.aura_3d import _active_lab as new_lab
                    lab = new_lab
                
                if lab:
                    if act in ("start", "enable") and not getattr(lab, "worker", None):
                        lab.toggle_gestures()
                    elif act in ("stop", "disable") and getattr(lab, "worker", None):
                        lab.toggle_gestures()
                    elif act in ("toggle", ""):
                        lab.toggle_gestures()
                    
                    is_on = getattr(lab, "worker", None) is not None
                    status_text = "ACTIVE" if is_on else "OFF"
                    msg = (
                        f"Webcam hand gesture tracking is {status_text}. "
                        "Point your index finger to rotate the 3D model, pinch to zoom in or out, "
                        "swipe open palm to switch models, and form a fist to reset the view."
                    )
                    self.ui.write_log(f"GESTURES: {status_text}")
                    self.speak(msg)
                    result = msg
                else:
                    result = "AURA 3D Learning Lab could not be opened for webcam hand gesture tracking."

            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."
            elif name in ("shutdown_aura", "shutdown_aure"):
                self.ui.write_log("SYS: Shutdown requested.")
                self.speak("Goodbye, sir.")

                def _shutdown():
                    import time, sys, os
                    time.sleep(1)
                    os._exit(0)

                threading.Thread(target=_shutdown, daemon=True).start()
            else:
                result = f"Unknown tool: {name}"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[AURA] 📤 {name} → {str(result)[:80]}")

        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[AURA] 🎤 Mic started")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                aura_speaking = self._is_speaking
            if not aura_speaking and not self.ui.muted:
                data = indata.tobytes()
                loop.call_soon_threadsafe(
                    self.out_queue.put_nowait,
                    {"data": data, "mime_type": "audio/pcm"}
                )

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[AURA] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[AURA] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[AURA] 👂 Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            self.set_speaking(True)
                            txt = sc.output_transcription.text.strip()
                            if txt:
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                in_buf.append(txt)

                        if sc.turn_complete:
                            self.set_speaking(False)

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"AURA: {full_out}")
                            out_buf = []

                            if full_in and len(full_in) > 5:
                                threading.Thread(
                                    target=_update_memory_async,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[AURA] 📞 {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )

        except Exception as e:
            print(f"[AURA] ❌ Recv: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[AURA] 🔊 Play started")
        loop = asyncio.get_event_loop()

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        stream.start()
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                self.set_speaking(True)
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[AURA] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def run(self):
        client = google.genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        while True:
            try:
                print("[AURA] 🔌 Connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=10)

                    print("[AURA] ✅ Connected.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: AURA online.")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    
            except Exception as e:
                print(f"[AURA] ⚠️ {e}")
                traceback.print_exc()

            self.set_speaking(False)
            self.ui.set_state("THINKING")
            print("[AURA] 🔄 Reconnecting in 3s...")
            await asyncio.sleep(3)

# Backward-compatibility alias
AureLive = AuraLive


def main():
    ui = AuraUI("face.png")

    def runner():
        ui.wait_for_api_key()
        aura = AuraLive(ui)
        try:
            asyncio.run(aura.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()