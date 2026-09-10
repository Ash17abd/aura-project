"""
Quick-access tool for AURA 3D Learning Lab examples and voice commands.

Provides UI for browsing example prompts and sending voice commands to the 3D lab.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QListWidget, 
    QListWidgetItem, QPushButton, QLabel, QTextEdit, QWidget, QLineEdit,
    QProgressBar, QFrame
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, pyqtSignal


try:
    from actions.example_prompts import ExamplePromptLibrary
except ImportError:
    from example_prompts import ExamplePromptLibrary


class ExamplePromptsBrowser(QDialog):
    """Browser and search engine for 3D model example prompts."""

    def __init__(self, parent=None, on_select_callback=None):
        super().__init__(parent)
        self.setWindowTitle("AURA — 3D Models & Examples Browser")
        self.resize(850, 640)
        self.setStyleSheet("""
            QDialog, QWidget { background:#0d0b09; color:#ffffff; }
            QPushButton { background:#1c1611; color:#ff8c00; border:1px solid #382d24; padding:7px 10px; border-radius:4px; font-weight:bold; }
            QPushButton:hover { border:1px solid #ff8c00; background:#2e1500; color:#ffffff; }
            QListWidget, QComboBox, QTextEdit, QLineEdit { background:#161310; color:#ffffff; border:1px solid #382d24; border-radius:3px; }
            QLineEdit:focus { border:1px solid #ff8c00; }
        """)
        self.on_select_callback = on_select_callback
        self._build()
        self._populate_categories()
        self._filter_examples()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Title
        title = QLabel("◈ AURA 3D MODEL & PROMPTS EXPLORER")
        title.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
        title.setStyleSheet("color:#ff8c00;")
        layout.addWidget(title)

        # Search and Category filter row
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        search_lbl = QLabel("🔍 Search:")
        search_lbl.setStyleSheet("color:#00d4ff; font-weight:bold;")
        filter_layout.addWidget(search_lbl)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search 3D models (e.g. engine, motor, dna, cell, robot, rocket)...")
        self.search_input.setFixedHeight(30)
        self.search_input.textChanged.connect(self._filter_examples)
        filter_layout.addWidget(self.search_input, 2)

        cat_lbl = QLabel("Category:")
        cat_lbl.setStyleSheet("color:#00ff88; font-weight:bold;")
        filter_layout.addWidget(cat_lbl)
        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(30)
        self.category_combo.currentTextChanged.connect(self._filter_examples)
        filter_layout.addWidget(self.category_combo, 1)

        layout.addLayout(filter_layout)

        # Examples list
        self.examples_list = QListWidget()
        self.examples_list.itemSelectionChanged.connect(self._on_example_selected)
        self.examples_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.examples_list, 2)

        # Example details
        desc_lbl = QLabel("Description & Engineering Scope:")
        desc_lbl.setStyleSheet("color:#ff8c00; font-weight:bold; font-size:11px;")
        layout.addWidget(desc_lbl)
        self.description = QTextEdit()
        self.description.setReadOnly(True)
        self.description.setMaximumHeight(65)
        layout.addWidget(self.description)

        prompt_lbl = QLabel("AI Generation Prompt:")
        prompt_lbl.setStyleSheet("color:#00ff88; font-weight:bold; font-size:11px;")
        layout.addWidget(prompt_lbl)
        self.prompt_text = QTextEdit()
        self.prompt_text.setReadOnly(True)
        self.prompt_text.setMaximumHeight(65)
        layout.addWidget(self.prompt_text)

        # Buttons
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("✨ CREATE & LOAD 3D MODEL")
        create_btn.setFixedHeight(32)
        create_btn.setStyleSheet("background:#2e1500; color:#ff8c00; border:1px solid #ff8c00; font-weight:bold;")
        create_btn.clicked.connect(self._on_create_clicked)
        btn_layout.addWidget(create_btn)

        close_btn = QPushButton("CLOSE")
        close_btn.setFixedHeight(32)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _populate_categories(self):
        """Populate category dropdown."""
        categories = ExamplePromptLibrary.get_categories()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItems(["All Categories"] + categories)
        self.category_combo.blockSignals(False)

    def _filter_examples(self):
        """Handle keyword or category filter change."""
        category = self.category_combo.currentText()
        query = self.search_input.text().strip().lower() if hasattr(self, "search_input") else ""

        self.examples_list.clear()
        self.prompt_text.clear()
        self.description.clear()

        if category == "All Categories" or not category:
            base_examples = ExamplePromptLibrary.get_all()
        else:
            base_examples = ExamplePromptLibrary.get_by_category(category)

        matched = []
        for ex in base_examples:
            if not query or (query in ex.title.lower() or query in ex.description.lower() or query in ex.prompt.lower()):
                matched.append(ex)

        for example in matched:
            item = QListWidgetItem(f"[{example.difficulty.upper()}] {example.title}  —  {example.category}")
            item.setData(Qt.ItemDataRole.UserRole, example)
            self.examples_list.addItem(item)

        if self.examples_list.count() > 0:
            self.examples_list.setCurrentRow(0)

    def _on_example_selected(self):
        """Handle example selection."""
        if self.examples_list.currentItem():
            example = self.examples_list.currentItem().data(Qt.ItemDataRole.UserRole)
            if example:
                self.description.setText(example.description)
                self.prompt_text.setText(example.prompt)

    def _on_item_double_clicked(self, item):
        """Double click to immediately create and load model."""
        self._on_create_clicked()

    def _on_create_clicked(self):
        """Handle create button."""
        if self.examples_list.currentItem():
            example = self.examples_list.currentItem().data(Qt.ItemDataRole.UserRole)
            if example and self.on_select_callback:
                self.on_select_callback(example.prompt)
            self.close()
        elif hasattr(self, "search_input") and self.search_input.text().strip():
            # If nothing selected from list, generate from custom search query
            query = self.search_input.text().strip()
            if self.on_select_callback:
                self.on_select_callback(query)
            self.close()


class VoiceCommandWidget(QWidget):
    """Widget for sending voice commands to 3D lab."""

    def __init__(self, parent=None, on_command_callback=None):
        super().__init__(parent)
        self.on_command_callback = on_command_callback
        self.setStyleSheet("""
            QWidget { background:#0d0b09; color:#ffffff; }
            QPushButton { background:#1c1611; color:#ff8c00; border:1px solid #382d24; padding:5px 8px; border-radius:4px; font-weight:bold; }
            QPushButton:hover { border:1px solid #ff8c00; background:#2e1500; color:#ffffff; }
            QTextEdit { background:#161310; color:#ffffff; border:1px solid #382d24; border-radius:3px; }
        """)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)

        title_lbl = QLabel("💬 VOICE COMMANDS")
        title_lbl.setStyleSheet("color:#ff8c00; font-weight:bold;")
        layout.addWidget(title_lbl)
        
        # Command suggestions
        suggestions_text = QLabel(
            "Examples:\n"
            "• 'Explain the primary winding'\n"
            "• 'Play animation'\n"
            "• 'Rotate it'\n"
            "• 'Zoom in'\n"
            "• 'Show the next step'"
        )
        suggestions_text.setStyleSheet("color:#00ff88; font-size:10px;")
        layout.addWidget(suggestions_text)


        # Command input
        self.command_input = QTextEdit()
        self.command_input.setMaximumHeight(60)
        self.command_input.setPlaceholderText("Enter voice command or description...")
        layout.addWidget(self.command_input)

        # Send button
        send_btn = QPushButton("📤 SEND COMMAND")
        send_btn.clicked.connect(self._send_command)
        layout.addWidget(send_btn)

    def _send_command(self):
        """Send voice command."""
        text = self.command_input.toPlainText().strip()
        if text and self.on_command_callback:
            self.on_command_callback(text)
            self.command_input.clear()


class OptionQuizDialog(QDialog):
    """Interactive Multiple-Choice Option Quiz dialog with real-time student tracking."""

    answer_recorded = pyqtSignal(dict)

    def __init__(self, quiz_data: dict, speak=None, on_answer_callback=None, on_complete_callback=None, parent=None):
        super().__init__(parent)
        self.quiz_data = quiz_data or {}
        self.topic = self.quiz_data.get("topic", "Engineering System")
        self.difficulty = self.quiz_data.get("difficulty", "Intermediate")
        self.questions = self.quiz_data.get("questions", [])
        self.current_idx = 0
        self.score = 0
        self.speak = speak
        self.on_answer_callback = on_answer_callback
        self.on_complete_callback = on_complete_callback

        try:
            from backend.student_tracker import student_tracker
            self.tracker = student_tracker
        except Exception:
            self.tracker = None

        self.setWindowTitle(f"AURA — Interactive 3D Option Quiz: {self.topic}")
        self.resize(780, 620)
        self.setStyleSheet("""
            QDialog, QWidget { background: #0b0f14; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; }
            QPushButton { background: #131d27; color: #38bdf8; border: 1px solid #1e3a5f; padding: 10px 14px; border-radius: 6px; font-weight: bold; text-align: left; }
            QPushButton:hover:not(:disabled) { border: 1px solid #38bdf8; background: #1a2c3f; color: #ffffff; }
            QPushButton:disabled { color: #94a3b8; }
            QFrame.card { background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; }
            QProgressBar { background: #131d27; border: 1px solid #1e3a5f; border-radius: 4px; height: 10px; text-align: center; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8); border-radius: 4px; }
        """)

        self._build_ui()
        self._load_current_question()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header: Title & Difficulty
        header_row = QHBoxLayout()
        title = QLabel(f"🧪 {self.topic.upper()}")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8; letter-spacing: 1px;")
        header_row.addWidget(title)

        header_row.addStretch()

        self.diff_badge = QLabel(self.difficulty.upper())
        self.diff_badge.setStyleSheet("background: #0369a1; color: #ffffff; font-weight: bold; font-size: 11px; padding: 4px 10px; border-radius: 4px;")
        header_row.addWidget(self.diff_badge)
        layout.addLayout(header_row)

        # Student Progress Tracker HUD Banner
        self.progress_banner = QFrame()
        self.progress_banner.setProperty("class", "card")
        self.progress_banner.setStyleSheet("background: #111b27; border: 1px solid #1e3a5f; border-radius: 6px; padding: 8px;")
        prog_layout = QHBoxLayout(self.progress_banner)
        prog_layout.setContentsMargins(10, 6, 10, 6)

        self.lbl_mastery = QLabel("RANK: NOVICE")
        self.lbl_mastery.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 11px;")
        prog_layout.addWidget(self.lbl_mastery)

        prog_layout.addSpacing(20)

        self.lbl_accuracy = QLabel("ACCURACY: 0.0%")
        self.lbl_accuracy.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        prog_layout.addWidget(self.lbl_accuracy)

        prog_layout.addSpacing(20)

        self.lbl_streak = QLabel("STREAK: 0")
        self.lbl_streak.setStyleSheet("color: #ec4899; font-weight: bold; font-size: 11px;")
        prog_layout.addWidget(self.lbl_streak)

        prog_layout.addStretch()

        self.lbl_q_counter = QLabel(f"Question 1 of {max(1, len(self.questions))}")
        self.lbl_q_counter.setStyleSheet("color: #94a3b8; font-size: 11px;")
        prog_layout.addWidget(self.lbl_q_counter)

        layout.addWidget(self.progress_banner)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, max(1, len(self.questions)))
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Question Statement Card
        self.q_card = QFrame()
        self.q_card.setStyleSheet("background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 14px;")
        q_layout = QVBoxLayout(self.q_card)
        q_layout.setSpacing(6)

        self.lbl_q_type = QLabel("MULTIPLE CHOICE QUESTION")
        self.lbl_q_type.setStyleSheet("color: #0ea5e9; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        q_layout.addWidget(self.lbl_q_type)

        self.lbl_q_text = QLabel("Loading question...")
        self.lbl_q_text.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.lbl_q_text.setStyleSheet("color: #ffffff; line-height: 1.4;")
        self.lbl_q_text.setWordWrap(True)
        q_layout.addWidget(self.lbl_q_text)
        layout.addWidget(self.q_card)

        # Options Container
        self.opt_layout = QVBoxLayout()
        self.opt_layout.setSpacing(8)
        self.option_buttons = []
        for i in range(4):
            btn = QPushButton(f"Option {chr(65 + i)}")
            btn.setFixedHeight(44)
            btn.clicked.connect(lambda checked, idx=i: self._handle_option_click(idx))
            self.option_buttons.append(btn)
            self.opt_layout.addWidget(btn)
        layout.addLayout(self.opt_layout)

        # Explanation Box
        self.explanation_box = QLabel("")
        self.explanation_box.setWordWrap(True)
        self.explanation_box.setStyleSheet("background: #111b27; border-left: 3px solid #0284c7; padding: 10px; border-radius: 4px; font-size: 11px;")
        self.explanation_box.setVisible(False)
        layout.addWidget(self.explanation_box)

        # Bottom Action Bar
        action_layout = QHBoxLayout()
        self.lbl_footer_score = QLabel(f"Current Quiz Score: 0 / {len(self.questions)}")
        self.lbl_footer_score.setStyleSheet("color: #94a3b8; font-size: 11px;")
        action_layout.addWidget(self.lbl_footer_score)

        action_layout.addStretch()

        self.btn_next = QPushButton("NEXT QUESTION →")
        self.btn_next.setStyleSheet("background: #0284c7; color: #ffffff; border: none; padding: 10px 18px; border-radius: 6px; font-weight: bold;")
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self._next_question)
        action_layout.addWidget(self.btn_next)

        layout.addLayout(action_layout)
        self._refresh_tracker_ui()

    def _refresh_tracker_ui(self):
        if not self.tracker:
            return
        summary = self.tracker.get_summary()
        self.lbl_mastery.setText(f"RANK: {summary.get('mastery_tier', 'Novice').upper()}")
        self.lbl_accuracy.setText(f"ACCURACY: {summary.get('accuracy_pct', 0.0)}%")
        self.lbl_streak.setText(f"STREAK: {summary.get('streak', 0)}")

    def _load_current_question(self):
        if self.current_idx >= len(self.questions):
            self._show_quiz_completion()
            return

        q = self.questions[self.current_idx]
        total = len(self.questions)
        self.lbl_q_counter.setText(f"Question {self.current_idx + 1} of {total}")
        self.progress_bar.setValue(self.current_idx)
        self.lbl_q_type.setText(q.get("type", "mcq").replace("_", " ").upper())
        self.lbl_q_text.setText(f"{self.current_idx + 1}. {q.get('question', '')}")

        options = q.get("options", [])
        for i, btn in enumerate(self.option_buttons):
            if i < len(options):
                btn.setText(f"  {chr(65 + i)})  {options[i]}")
                btn.setStyleSheet("""
                    QPushButton { background: #131d27; color: #e2e8f0; border: 1px solid #1e3a5f; padding: 10px 14px; border-radius: 6px; font-weight: bold; text-align: left; }
                    QPushButton:hover { border: 1px solid #38bdf8; background: #1a2c3f; color: #ffffff; }
                """)
                btn.setEnabled(True)
                btn.setVisible(True)
            else:
                btn.setVisible(False)

        self.explanation_box.setVisible(False)
        self.btn_next.setEnabled(False)
        if self.current_idx == total - 1:
            self.btn_next.setText("VIEW FINAL RESULTS 🏁")
        else:
            self.btn_next.setText("NEXT QUESTION →")

    def _handle_option_click(self, selected_idx: int):
        if self.current_idx >= len(self.questions):
            return

        q = self.questions[self.current_idx]
        correct_idx = q.get("correct_index", 0)
        is_correct = (selected_idx == correct_idx)

        if is_correct:
            self.score += 1

        # Disable all option buttons and apply correct/wrong styling
        for i, btn in enumerate(self.option_buttons):
            btn.setEnabled(False)
            if i == correct_idx:
                btn.setStyleSheet("background: #064e3b; color: #6ee7b7; border: 2px solid #10b981; border-radius: 6px; font-weight: bold; padding: 10px 14px; text-align: left;")
            elif i == selected_idx and not is_correct:
                btn.setStyleSheet("background: #450a0a; color: #fca5a5; border: 2px solid #ef4444; border-radius: 6px; font-weight: bold; padding: 10px 14px; text-align: left;")
            else:
                btn.setStyleSheet("background: #0f172a; color: #64748b; border: 1px solid #1e293b; border-radius: 6px; padding: 10px 14px; text-align: left;")

        # Display explanation
        expl = q.get("explanation", "")
        self.explanation_box.setText(f"{'✅ CORRECT! ' if is_correct else '❌ INCORRECT. '}{expl}")
        border_col = "#10b981" if is_correct else "#ef4444"
        bg_col = "#06281e" if is_correct else "#2b1010"
        self.explanation_box.setStyleSheet(f"background: {bg_col}; border-left: 4px solid {border_col}; padding: 10px; border-radius: 4px; font-size: 11px; color: #ffffff;")
        self.explanation_box.setVisible(True)

        # Update persistent Student Tracker
        if self.tracker:
            opts = q.get("options", [])
            choice_text = opts[selected_idx] if selected_idx < len(opts) else str(selected_idx)
            self.tracker.record_answer(
                topic=self.topic,
                question_id=q.get("id", f"q_{self.current_idx}"),
                student_choice=choice_text,
                correct_index=correct_idx,
                is_correct=is_correct,
                question_text=q.get("question", ""),
                explanation=expl,
                difficulty=self.difficulty,
            )
            self._refresh_tracker_ui()

        self.lbl_footer_score.setText(f"Current Quiz Score: {self.score} / {len(self.questions)}")
        self.btn_next.setEnabled(True)

        # Call optional external callbacks
        if self.on_answer_callback:
            try:
                self.on_answer_callback(self.current_idx, is_correct, q)
            except Exception:
                pass

        if self.speak:
            msg = f"{'Correct.' if is_correct else 'Incorrect.'} {expl}"
            try:
                self.speak(msg)
            except Exception:
                pass

    def _next_question(self):
        self.current_idx += 1
        self._load_current_question()

    def _show_quiz_completion(self):
        total = max(1, len(self.questions))
        pct = round((self.score / total) * 100.0, 1)

        if self.tracker:
            self.tracker.record_quiz_completion(
                topic=self.topic,
                difficulty=self.difficulty,
                score=self.score,
                total_questions=total,
            )
            self._refresh_tracker_ui()

        self.progress_bar.setValue(total)
        self.lbl_q_type.setText("ASSESSMENT COMPLETE")
        self.lbl_q_text.setText(f"🏆 Quiz Finished! You scored {self.score} out of {total} ({pct}%).")

        for btn in self.option_buttons:
            btn.setVisible(False)

        summary_text = (
            f"Great effort on the {self.topic} assessment!\n"
            f"• Difficulty: {self.difficulty}\n"
            f"• Final Score: {self.score} / {total} ({pct}%)\n"
        )
        if self.tracker:
            s = self.tracker.get_summary()
            summary_text += f"• Updated Engineering Rank: {s.get('mastery_tier', 'Novice')}\n"
            summary_text += f"• Overall Accuracy: {s.get('accuracy_pct', 0.0)}%\n"
            summary_text += f"• Current Streak: {s.get('streak', 0)} in a row"

        self.explanation_box.setText(summary_text)
        self.explanation_box.setStyleSheet("background: #0c1e33; border-left: 4px solid #38bdf8; padding: 12px; border-radius: 4px; font-size: 12px; color: #e0f2fe;")
        self.explanation_box.setVisible(True)

        self.btn_next.setText("CLOSE QUIZ ✕")
        self.btn_next.setEnabled(True)
        self.btn_next.clicked.disconnect()
        self.btn_next.clicked.connect(self.accept)

        if self.on_complete_callback:
            try:
                self.on_complete_callback(self.score, total, pct)
            except Exception:
                pass

        if self.speak:
            try:
                self.speak(f"Quiz complete! You scored {self.score} out of {total}, achieving {pct} percent.")
            except Exception:
                pass


