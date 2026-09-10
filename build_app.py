import os
import sys
import subprocess
from pathlib import Path

def build():
    base_dir = Path(__file__).parent.resolve()
    print(f"Building MARK XXXIX-OR from {base_dir}...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Mark-XXXIX-OR",
        "--onedir",
        "--clean",
        "--noconfirm",
        "--add-data=core/prompt.txt;core",
        "--add-data=config/api_keys.json;config",
        "--add-data=config/hand_landmarker.task;config",
        "--add-data=web;web",
        "--hidden-import=PyQt6",
        "--hidden-import=google.genai",
        "--hidden-import=google.generativeai",
        "--hidden-import=mediapipe",
        "--hidden-import=cv2",
        "--hidden-import=matplotlib",
        "--hidden-import=sounddevice",
        "--hidden-import=pyautogui",
        "--hidden-import=playwright",
        "--hidden-import=actions",
        "--hidden-import=actions.aura_3d",
        "--hidden-import=actions.aure_3d",
        "--hidden-import=actions.animation_player",
        "--hidden-import=actions.component_selector",
        "--hidden-import=actions.example_prompts",
        "--hidden-import=actions.lab_ui_components",
        "--hidden-import=actions.model_generator",
        "--hidden-import=actions.voice_parser",
        "--hidden-import=actions.image_search",
        "--hidden-import=actions.cmd_control",
        "--hidden-import=actions.code_helper",
        "--hidden-import=actions.dev_agent",
        "--hidden-import=actions.file_processor",
        "--hidden-import=actions.file_controller",
        "--hidden-import=actions.game_updater",
        "--hidden-import=actions.flight_finder",
        "--hidden-import=actions.browser_control",
        "--hidden-import=actions.weather_report",
        "--hidden-import=actions.youtube_video",
        "--hidden-import=actions.send_message",
        "--hidden-import=actions.reminder",
        "--hidden-import=actions.desktop",
        "--hidden-import=actions.computer_settings",
        "--hidden-import=actions.computer_control",
        "--hidden-import=actions.screen_processor",
        "--hidden-import=actions.open_app",
        "--hidden-import=actions.web_search",
        "--hidden-import=agent.planner",
        "--hidden-import=agent.executor",
        "--hidden-import=agent.task_queue",
        "--hidden-import=agent.error_handler",
        "--hidden-import=memory.memory_manager",
        "--hidden-import=memory.config_manager",
        "--hidden-import=or_client",
        "--hidden-import=backend",
        "--hidden-import=backend.student_tracker",
        "--hidden-import=backend.quiz_generator",
        "--hidden-import=backend.secure_os_agent",
        "--hidden-import=backend.agentic_pipeline",
        "--hidden-import=backend.model_spec_schema",
        "--hidden-import=backend.self_verification",
        "--hidden-import=backend.session_memory",
        "--hidden-import=backend.teacher_mode",
        os.path.join(base_dir, "main.py")
    ]

    print("Running command:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=base_dir)
    if res.returncode == 0:
        print("\n[SUCCESS] BUILD SUCCESSFUL! Executable directory created at:")
        print(base_dir / "dist" / "Mark-XXXIX-OR")
    else:
        print("\n[ERROR] BUILD FAILED with exit code:", res.returncode)
        sys.exit(res.returncode)

if __name__ == "__main__":
    build()

