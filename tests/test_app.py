"""Local smoke tests for the main LearnMind workflows.

Run with: python -m unittest discover -s tests
"""
import os
import re
import tempfile
import unittest

import app as learnmind


class LearnMindWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        learnmind.app.config.update(
            TESTING=True,
            SECRET_KEY="test-only-secret",
            DATABASE=os.path.join(self.temp_dir.name, "test.db"),
        )
        learnmind.init_db()
        self.client = learnmind.app.test_client()
        response = self.client.get("/signup")
        self.csrf = re.search(
            rb'name="csrf_token" value="([^"]+)"', response.data
        ).group(1).decode()
        response = self.client.post(
            "/signup",
            data={
                "csrf_token": self.csrf,
                "name": "Test Student",
                "email": "student@example.test",
                "password": "test-password-123",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.csrf = re.search(
            rb'<meta name="csrf-token" content="([^"]+)"', response.data
        ).group(1).decode()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_all_main_pages_render(self):
        for path in (
            "/home", "/my-learning", "/study-debugger", "/ai-assistant",
            "/progress", "/resources", "/settings",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_quiz_is_scored_and_saved(self):
        response = self.client.post(
            "/api/quiz/submit",
            json={"subject": "Natural Language Processing", "answers": [0, 1, 2, 0, 1]},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["score"], 5)
        self.assertEqual(self.client.get("/progress").status_code, 200)

    def test_subject_can_be_added(self):
        response = self.client.post(
            "/subjects/add",
            data={"csrf_token": self.csrf, "subject_name": "Python Programming"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        questions = self.client.get(
            "/api/quiz/questions?subject=Python%20Programming"
        )
        self.assertEqual(questions.status_code, 200)

    def test_chat_history_and_clear(self):
        original = learnmind.make_ai_answer
        learnmind.make_ai_answer = lambda question, history: "Test reply: " + question
        try:
            response = self.client.post(
                "/api/chat/send",
                json={"question": "What is AI?"},
                headers={"X-CSRF-Token": self.csrf},
            )
            self.assertEqual(response.status_code, 200)
            history = self.client.get("/api/chat/history").get_json()["messages"]
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["role"], "user")
            clear = self.client.post(
                "/api/chat/clear", headers={"X-CSRF-Token": self.csrf}
            )
            self.assertEqual(clear.status_code, 200)
            self.assertEqual(
                self.client.get("/api/chat/history").get_json()["messages"], []
            )
        finally:
            learnmind.make_ai_answer = original

    def test_csrf_is_required_for_state_changes(self):
        response = self.client.post(
            "/api/quiz/submit",
            json={"subject": "Natural Language Processing", "answers": [0, 1, 2, 0, 1]},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
