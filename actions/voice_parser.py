"""
Voice command parser for component Q&A.

Parses natural language requests and identifies components to explain.
"""

import re
from typing import Optional


class VoiceCommandParser:
    """Parses voice commands and extracts component queries."""

    def __init__(self, component_map: dict[str, any] = None):
        """
        Initialize parser with optional component map.
        
        Args:
            component_map: Dict of {component_id: {"name": "...", "description": "..."}}
        """
        self.component_map = component_map or {}
        self.common_queries = [
            "explain",
            "tell me about",
            "what is",
            "show",
            "describe",
            "how does",
            "what does",
            "highlight",
        ]

    def parse_component_query(self, user_input: str) -> Optional[str]:
        """
        Parse user input to extract component query.
        
        Args:
            user_input: Natural language input (e.g., "Explain the transformer primary winding")
            
        Returns:
            Component name/ID if found, None otherwise
        """
        if not user_input or not isinstance(user_input, str):
            return None

        lower_input = user_input.lower()

        # Check for common query phrases
        for query in self.common_queries:
            if query in lower_input:
                # Extract text after the query phrase
                pattern = rf"{query}\s+(?:the\s+)?(.+?)(?:\s*[?.!]|$)"
                match = re.search(pattern, lower_input)
                if match:
                    component_name = match.group(1).strip()
                    return self._find_component_match(component_name)

        # Fallback: try to find any component name mentioned
        for comp_id, comp_info in self.component_map.items():
            comp_name = comp_info.get("name", "").lower()
            if comp_name and comp_name in lower_input:
                return comp_id

        return None

    def _find_component_match(self, query: str) -> Optional[str]:
        """
        Find component ID matching the query string.
        
        Handles partial matches, aliases, and variations.
        """
        query = query.lower().strip()

        # Exact match
        for comp_id, comp_info in self.component_map.items():
            comp_name = comp_info.get("name", "").lower()
            if comp_name == query:
                return comp_id

        # Substring match (find component name that contains the query)
        for comp_id, comp_info in self.component_map.items():
            comp_name = comp_info.get("name", "").lower()
            if query in comp_name or comp_name in query:
                return comp_id

        # Partial word match (match first word or last word of multi-word names)
        words = query.split()
        if words:
            first_word = words[0]
            last_word = words[-1]

            for comp_id, comp_info in self.component_map.items():
                comp_name = comp_info.get("name", "").lower()
                comp_words = comp_name.split()

                # Check if first/last word matches
                if first_word in comp_words or last_word in comp_words:
                    return comp_id

        return None

    def parse_animation_command(self, user_input: str) -> Optional[str]:
        """
        Parse animation control commands.
        
        Returns: "play", "pause", "next", "previous", "reset", or None
        """
        if not user_input:
            return None

        lower_input = user_input.lower()

        if any(w in lower_input for w in ["play", "start", "run", "begin", "go"]):
            return "play"
        elif any(w in lower_input for w in ["pause", "stop", "hold"]):
            return "pause"
        elif any(w in lower_input for w in ["next", "continue", "forward"]):
            return "next"
        elif any(w in lower_input for w in ["previous", "back", "backward", "prior"]):
            return "previous"
        elif any(w in lower_input for w in ["reset", "restart", "begin", "from start"]):
            return "reset"

        return None

    def parse_gesture_command(self, user_input: str) -> Optional[str]:
        """
        Parse gesture control commands.
        
        Returns: "toggle_gestures", "rotate", "zoom_in", "zoom_out", "pan", "reset", or None
        """
        if not user_input:
            return None

        lower_input = user_input.lower()

        # Webcam gesture tracking toggle
        if any(w in lower_input for w in [
            "hand gesture", "gestures", "webcam gesture", "camera gesture",
            "gesture control", "enable gesture", "start gesture", "toggle gesture",
            "move through gesture", "gesture mode", "hand tracking"
        ]):
            return "toggle_gestures"

        # Viewport reset
        if any(w in lower_input for w in ["reset view", "reset camera", "recenter", "re-center", "center model", "default view"]):
            return "reset"

        if any(w in lower_input for w in ["rotate", "turn", "spin", "twist", "roll"]):
            return "rotate"
        elif any(w in lower_input for w in ["zoom in", "magnify", "enlarge", "closer"]):
            return "zoom_in"
        elif any(w in lower_input for w in ["zoom out", "shrink", "reduce", "away"]):
            return "zoom_out"
        elif any(w in lower_input for w in ["pan", "move", "scroll", "slide"]):
            return "pan"

        return None

    def is_component_query(self, user_input: str) -> bool:
        """Check if input is asking about a component."""
        if not user_input:
            return False

        lower_input = user_input.lower()

        # Check for query phrases
        for query in self.common_queries:
            if query in lower_input:
                return True

        # Check if any component name is mentioned
        for comp_id, comp_info in self.component_map.items():
            comp_name = comp_info.get("name", "").lower()
            if comp_name and comp_name in lower_input:
                return True

        return False

    def is_teacher_query(self, user_input: str) -> bool:
        """Check if input is asking for a comprehensive teacher explanation."""
        if not user_input:
            return False
        low = user_input.lower()
        triggers = ["teacher mode", "explain the model", "explain this system", "how does this work", "how does it work", "explain how", "how this", "how it works", "working principle", "teach me", "deep explanation", "lecture"]
        return any(t in low for t in triggers)

    def is_quiz_query(self, user_input: str) -> bool:
        """Check if input is asking for an interactive quiz."""
        if not user_input:
            return False
        low = user_input.lower()
        triggers = ["quiz", "test me", "test my knowledge", "quiz mode", "ask me questions", "practice questions", "exam"]
        return any(t in low for t in triggers)

    def is_modification_query(self, user_input: str) -> bool:
        """Check if input is asking to modify the active 3D model."""
        if not user_input:
            return False
        low = user_input.lower()
        triggers = ["recolor", "change color", "add a ", "add another", "remove ", "delete ", "make it bigger", "make it smaller", "resize", "scale", "rotate the", "move the"]
        return any(t in low for t in triggers)

    def is_os_query(self, user_input: str) -> bool:
        """Check if input is an OS automation instruction."""
        if not user_input:
            return False
        low = user_input.lower()
        triggers = ["open chrome", "open google chrome", "google chrome", "open vs code", "open vscode", "open code", "open notepad", "open calculator", "open calc", "open explorer", "open terminal", "open powershell", "open spotify", "open downloads", "open desktop", "open documents", "open project", "mute volume", "unmute", "take screenshot"]
        return any(t in low for t in triggers) or (low.startswith("open ") and any(w in low for w in ["app", "folder", "window", "directory"]))

    def update_component_map(self, components: list[dict]) -> None:
        """Update component map from model spec components."""
        self.component_map = {}
        for comp in components:
            comp_id = comp.get("id")
            if comp_id:
                self.component_map[comp_id] = {
                    "name": comp.get("name", ""),
                    "description": comp.get("description", ""),
                }

    @classmethod
    def parse(cls, text: str, component_map: dict[str, any] = None) -> dict[str, any]:
        """Unified parse helper returning intent and parameters."""
        p = cls(component_map or {})
        anim = p.parse_animation_command(text)
        if anim:
            return {"intent": "animation", "action": anim}
        gesture = p.parse_gesture_command(text)
        if gesture:
            return {"intent": "gesture", "action": gesture}
        comp_id = p.parse_component_query(text)
        if comp_id:
            return {"intent": "select_component", "component_id": comp_id}
        if p.is_teacher_query(text):
            return {"intent": "teacher_explain"}
        if p.is_quiz_query(text):
            return {"intent": "quiz"}
        if p.is_os_query(text):
            return {"intent": "os_automation"}
        return {"intent": "general", "query": text}


