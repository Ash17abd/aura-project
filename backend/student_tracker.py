"""
Student Progress & Learning Process Tracker for AURA 3D Learning Lab.

Tracks:
1. Overall accuracy, quizzes taken, questions attempted, correct answers
2. Current streak and maximum streak
3. Tiered engineering mastery levels (Novice, Apprentice, Specialist, Master Engineer)
4. Topic-level mastery breakdowns (attempts, accuracy, learning status)
5. Chronological attempt and quiz history
6. Thread-safe persistent JSON storage in memory/student_progress.json
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional


def _get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
DEFAULT_PROGRESS_PATH = BASE_DIR / "memory" / "student_progress.json"


class StudentProgressTracker:
    """Manages student quiz performance, concept mastery, and learning process tracking."""

    def __init__(self, storage_path: Path | str | None = None):
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_PROGRESS_PATH
        self._lock = Lock()
        self._data: dict[str, Any] = self._empty_state()
        self.load()

    def _empty_state(self) -> dict[str, Any]:
        return {
            "student_id": "default_student",
            "student_name": "Student",
            "total_quizzes": 0,
            "total_questions": 0,
            "correct_answers": 0,
            "accuracy_pct": 0.0,
            "streak": 0,
            "best_streak": 0,
            "mastery_tier": "Novice",
            "topics": {},
            "history": [],
            "last_active": datetime.now(timezone.utc).isoformat(),
        }

    def load(self) -> dict[str, Any]:
        """Load student progress from disk."""
        with self._lock:
            if not self.storage_path.exists():
                self._data = self._empty_state()
                return self._data

            try:
                content = self.storage_path.read_text(encoding="utf-8")
                if not content.strip():
                    self._data = self._empty_state()
                    return self._data
                loaded = json.loads(content)
                if isinstance(loaded, dict):
                    base = self._empty_state()
                    base.update(loaded)
                    self._data = base
                else:
                    self._data = self._empty_state()
            except Exception as e:
                print(f"[StudentTracker] Failed to load progress: {e}")
                self._data = self._empty_state()

            return self._data

    def save(self) -> bool:
        """Persist student progress to disk."""
        with self._lock:
            try:
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                self.storage_path.write_text(
                    json.dumps(self._data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                return True
            except Exception as e:
                print(f"[StudentTracker] Save error: {e}")
                return False

    def calculate_mastery_tier(self, accuracy_pct: float, total_questions: int) -> str:
        """Determine student's engineering mastery tier based on experience and accuracy."""
        if total_questions < 3:
            return "Novice"
        if accuracy_pct >= 90.0 and total_questions >= 8:
            return "Master Engineer"
        if accuracy_pct >= 75.0:
            return "Specialist"
        if accuracy_pct >= 50.0:
            return "Apprentice"
        return "Novice"

    def record_answer(
        self,
        topic: str,
        question_id: str,
        student_choice: int | str,
        correct_index: int,
        is_correct: bool,
        question_text: str = "",
        explanation: str = "",
        difficulty: str = "Intermediate",
    ) -> dict[str, Any]:
        """Record an individual question attempt and update learning metrics."""
        topic_key = (topic or "General Systems").strip()
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._data["total_questions"] += 1
            if is_correct:
                self._data["correct_answers"] += 1
                self._data["streak"] += 1
                if self._data["streak"] > self._data["best_streak"]:
                    self._data["best_streak"] = self._data["streak"]
            else:
                self._data["streak"] = 0

            # Overall Accuracy
            tot_q = self._data["total_questions"]
            tot_c = self._data["correct_answers"]
            self._data["accuracy_pct"] = round((tot_c / tot_q) * 100.0, 1) if tot_q > 0 else 0.0

            # Update Mastery Tier
            self._data["mastery_tier"] = self.calculate_mastery_tier(
                self._data["accuracy_pct"], tot_q
            )
            self._data["last_active"] = timestamp

            # Per-Topic Tracking
            if topic_key not in self._data["topics"]:
                self._data["topics"][topic_key] = {
                    "attempts": 0,
                    "correct": 0,
                    "accuracy_pct": 0.0,
                    "status": "In Progress",
                    "last_tested": timestamp,
                }

            top = self._data["topics"][topic_key]
            top["attempts"] += 1
            if is_correct:
                top["correct"] += 1
            top["accuracy_pct"] = round((top["correct"] / top["attempts"]) * 100.0, 1)
            top["last_tested"] = timestamp

            if top["accuracy_pct"] >= 80.0 and top["attempts"] >= 3:
                top["status"] = "Mastered"
            elif top["accuracy_pct"] < 60.0 and top["attempts"] >= 2:
                top["status"] = "Needs Review"
            else:
                top["status"] = "In Progress"

            # Attempt Log Entry
            entry = {
                "timestamp": timestamp,
                "type": "single_answer",
                "topic": topic_key,
                "question_id": question_id,
                "question_text": question_text[:120],
                "student_choice": student_choice,
                "correct_index": correct_index,
                "is_correct": is_correct,
                "difficulty": difficulty,
            }
            self._data["history"].append(entry)
            if len(self._data["history"]) > 100:
                self._data["history"].pop(0)

        self.save()
        return self.get_summary()

    def record_quiz_completion(
        self,
        topic: str,
        difficulty: str,
        score: int,
        total_questions: int,
        details: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Record the completion of a full quiz."""
        timestamp = datetime.now(timezone.utc).isoformat()
        pct = round((score / total_questions) * 100.0, 1) if total_questions > 0 else 0.0

        with self._lock:
            self._data["total_quizzes"] += 1
            entry = {
                "timestamp": timestamp,
                "type": "completed_quiz",
                "topic": topic or "General Systems",
                "difficulty": difficulty,
                "score": score,
                "total_questions": total_questions,
                "score_pct": pct,
                "details": details or [],
            }
            self._data["history"].append(entry)
            if len(self._data["history"]) > 100:
                self._data["history"].pop(0)

        self.save()
        return self.get_summary()

    def get_summary(self) -> dict[str, Any]:
        """Return a read-only snapshot of current student progress."""
        with self._lock:
            data = json.loads(json.dumps(self._data))

        # Count mastered vs review topics
        mastered = [t for t, s in data.get("topics", {}).items() if s.get("status") == "Mastered"]
        review = [t for t, s in data.get("topics", {}).items() if s.get("status") == "Needs Review"]

        data["mastered_topics_count"] = len(mastered)
        data["mastered_topics"] = mastered
        data["needs_review_topics"] = review
        return data

    def get_topic_mastery(self, topic: str) -> dict[str, Any] | None:
        """Return progress metrics for a specific topic."""
        with self._lock:
            return self._data.get("topics", {}).get(topic)

    def get_assessment_report(self) -> dict[str, Any]:
        """
        Generates a comprehensive assessment report identifying weak concepts,
        strong concepts, and recommended revision topics with 3D component focus.
        """
        summary = self.get_summary()
        topics = summary.get("topics", {})
        
        weak_concepts = []
        strong_concepts = []
        recommendations = []

        for topic_name, data in topics.items():
            acc = data.get("accuracy_pct", 0.0)
            attempts = data.get("attempts", data.get("questions_attempted", 0))
            if attempts >= 1:
                if acc < 65.0:
                    weak_concepts.append({
                        "topic": topic_name,
                        "concept": topic_name,
                        "accuracy_pct": acc,
                        "status": "Needs Revision",
                        "weak_areas": data.get("missed_concepts", [topic_name]),
                        "recommended_model": topic_name,
                    })
                    recommendations.append({
                        "topic": topic_name,
                        "concept": topic_name,
                        "recommendation": f"Review the operational dynamics and component roles of {topic_name} in the 3D lab.",
                        "suggested_action": f"Open 3D Model of {topic_name}",
                        "recommended_model": topic_name,
                    })
                elif acc >= 80.0:
                    strong_concepts.append({
                        "topic": topic_name,
                        "concept": topic_name,
                        "accuracy_pct": acc,
                        "status": "Mastered",
                    })

        return {
            "summary": summary,
            "weak_concepts": weak_concepts,
            "strong_concepts": strong_concepts,
            "recommended_revisions": recommendations,
            "total_quizzes_taken": summary.get("total_quizzes", 0),
            "mastery_tier": summary.get("mastery_tier", "Novice"),
            "overall_accuracy": summary.get("accuracy_pct", 0.0),
        }


    def reset_progress(self) -> dict[str, Any]:
        """Reset all tracked progress to initial clean state."""
        with self._lock:
            self._data = self._empty_state()
        self.save()
        return self.get_summary()

    def format_voice_summary(self) -> str:
        """Create a natural speech response summarizing student progress."""
        summary = self.get_summary()
        tot_q = summary.get("total_questions", 0)
        tot_quiz = summary.get("total_quizzes", 0)
        acc = summary.get("accuracy_pct", 0.0)
        tier = summary.get("mastery_tier", "Novice")
        streak = summary.get("streak", 0)
        mastered = summary.get("mastered_topics", [])

        if tot_q == 0:
            return "You haven't taken any quizzes yet. Say 'start quiz' on any topic to begin testing your engineering knowledge."

        msg = (
            f"You have completed {tot_quiz} quiz sessions and attempted {tot_q} questions with an overall accuracy of {acc}%. "
            f"Your current engineering rank is {tier}. "
        )

        if streak >= 3:
            msg += f"You are on a hot streak of {streak} correct answers in a row! "

        if mastered:
            topics_str = ", ".join(mastered[:3])
            msg += f"You have mastered: {topics_str}. "

        needs_review = summary.get("needs_review_topics", [])
        if needs_review:
            review_str = ", ".join(needs_review[:2])
            msg += f"Recommended review topic: {review_str}."

        return msg.strip()

    @staticmethod
    def parse_user_answer(answer_str: str, options: list[str]) -> int | None:
        """
        Parses spoken or typed user answers into an option index (0 to N-1).
        Supports:
        - "A", "B", "C", "D" (or "Option A", "Choice B")
        - Numbers: "1", "2", "3", "4", "first", "second", "third", "fourth"
        - "True" (0) / "False" (1)
        - Substring match against option contents
        """
        if not answer_str or not options:
            return None

        clean = answer_str.strip().lower()

        # Letter matching
        letter_map = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}
        # Check patterns like "option a", "choice b", "a)"
        m = re.search(r"\b(option|choice|answer)?\s*([a-e])\b", clean)
        if m and m.group(2) in letter_map:
            idx = letter_map[m.group(2)]
            if idx < len(options):
                return idx

        # Word number matching
        words = {
            "first": 0, "one": 0, "1": 0,
            "second": 1, "two": 1, "2": 1,
            "third": 2, "three": 2, "3": 2,
            "fourth": 3, "four": 3, "4": 3,
        }
        for word, idx in words.items():
            if re.search(rf"\b{word}\b", clean) and idx < len(options):
                return idx

        # True / False
        if len(options) == 2 and ("true" in options[0].lower() or "false" in options[1].lower()):
            if "true" in clean or "correct" in clean:
                return 0
            if "false" in clean or "incorrect" in clean:
                return 1

        # Text similarity / substring match
        for idx, opt in enumerate(options):
            opt_lower = opt.lower()
            if clean in opt_lower or opt_lower in clean:
                return idx

        return None


# Global singleton instance
student_tracker = StudentProgressTracker()
StudentTracker = StudentProgressTracker

def _record_quiz_result_helper(concept, score, total_questions, correct_count=None, student_id=None, missed_components=None):
    return student_tracker.record_quiz_completion(
        topic=concept,
        difficulty="Intermediate",
        score=int(score if score <= total_questions else (score / 100.0) * total_questions),
        total_questions=total_questions,
        details=[{"missed_components": missed_components or []}]
    )

StudentProgressTracker.record_quiz_result = staticmethod(_record_quiz_result_helper)
