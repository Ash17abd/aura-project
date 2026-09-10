"""
Animation system for 3D models.

Handles step-by-step animations, component movements, highlighting, and effects.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable


class AnimationAction(Enum):
    """Types of animation actions."""
    PULSE = "pulse"
    ROTATE = "rotate"
    MOVE = "move"
    HIGHLIGHT = "highlight"
    SCALE = "scale"
    FADE = "fade"
    FLOW = "flow"  # for showing flow/energy


@dataclass
class AnimationStep:
    """A single animation step."""
    step: int
    description: str
    affected_components: list[str]
    action: AnimationAction
    duration: float = 1.0
    intensity: float = 1.0


class AnimationPlayer:
    """Manages animation playback for 3D models."""

    def __init__(self):
        self.steps: list[AnimationStep] = []
        self.current_step: int = 0
        self.is_playing: bool = False
        self.loop: bool = True
        self.on_step_changed: Optional[Callable] = None
        self.on_animation_complete: Optional[Callable] = None
        self.animation_state: dict = {}

    def load_animation_steps(self, raw_steps: list) -> None:
        """Load animation steps from model spec."""
        self.steps = []
        for raw_step in raw_steps:
            # Handle both dict and AnimationStep dataclass
            if isinstance(raw_step, dict):
                try:
                    action_str = raw_step.get("action", "pulse").lower()
                    action = AnimationAction(action_str)
                except ValueError:
                    action = AnimationAction.PULSE

                step = AnimationStep(
                    step=raw_step.get("step", len(self.steps) + 1),
                    description=raw_step.get("description", ""),
                    affected_components=raw_step.get("affected_components", []),
                    action=action,
                    duration=raw_step.get("duration", 1.0),
                    intensity=raw_step.get("intensity", 1.0),
                )
                self.steps.append(step)
            elif isinstance(raw_step, AnimationStep):
                self.steps.append(raw_step)

    def play(self) -> None:
        """Start animation playback."""
        self.is_playing = True
        self.current_step = 0
        self._emit_step_changed()

    def pause(self) -> None:
        """Pause animation playback."""
        self.is_playing = False

    def resume(self) -> None:
        """Resume animation playback."""
        self.is_playing = True

    def stop(self) -> None:
        """Stop and reset animation."""
        self.is_playing = False
        self.current_step = 0
        self.animation_state.clear()
        self._emit_step_changed()

    def next_step(self) -> bool:
        """Advance to next step."""
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self._emit_step_changed()
            return True
        elif self.loop:
            self.current_step = 0
            self._emit_step_changed()
            return True
        else:
            self.is_playing = False
            if self.on_animation_complete:
                self.on_animation_complete()
            return False

    def previous_step(self) -> bool:
        """Go to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self._emit_step_changed()
            return True
        return False

    def get_current_step(self) -> Optional[AnimationStep]:
        """Get current animation step."""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def get_affected_components(self) -> list[str]:
        """Get components affected by current step."""
        step = self.get_current_step()
        return step.affected_components if step else []

    def get_step_description(self) -> str:
        """Get description of current step."""
        step = self.get_current_step()
        if not step:
            return "Animation complete"
        return f"Step {step.step}/{len(self.steps)}: {step.description}"

    def get_animation_action(self) -> Optional[AnimationAction]:
        """Get the animation action for current step."""
        step = self.get_current_step()
        return step.action if step else None

    def _emit_step_changed(self) -> None:
        """Notify listeners of step change."""
        if self.on_step_changed:
            self.on_step_changed(self.get_current_step())

    def set_loop(self, loop: bool) -> None:
        """Set whether animation should loop."""
        self.loop = loop

    def has_animation(self) -> bool:
        """Check if model has animation steps."""
        return len(self.steps) > 0

    def get_progress(self) -> float:
        """Get animation progress 0-1."""
        if not self.steps:
            return 0.0
        return (self.current_step + 1) / len(self.steps)

    def to_dict(self) -> dict:
        """Export animation state."""
        current = self.get_current_step()
        return {
            "current_step": self.current_step,
            "total_steps": len(self.steps),
            "is_playing": self.is_playing,
            "progress": self.get_progress(),
            "description": self.get_step_description(),
            "affected_components": self.get_affected_components(),
            "action": self.get_animation_action().value if self.get_animation_action() else None,
        }
