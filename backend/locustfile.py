"""Load test (haathi.md §10.4): `uv run --extra loadtest locust -f locustfile.py --headless -u 20 -r 5 -t 1m --host http://localhost:8000`"""
import random

from locust import HttpUser, between, task

QUESTIONS = [
    ("నేను తెలంగాణలో రైతుని, 2 ఎకరాల భూమి ఉంది", "te"), ("రైతు భరోసా కింద ఎంత డబ్బు వస్తుంది?", "te"),
    ("mera income 2 lakh hai", "hi"), ("PM Kisan me kitna paisa milta hai?", "hi"),
    ("What documents do I need for Kalyana Lakshmi?", "en"), ("I am 72 years old", "en"),
    ("How do I apply for Aarogyasri?", "en"), ("Who won the world cup?", "en"),
]


class HaathiUser(HttpUser):
    wait_time = between(1, 3)

    @task(5)
    def chat(self):
        q, lang = random.choice(QUESTIONS)
        with self.client.post("/api/chat", json={"message": q, "lang": lang}, stream=True, name="/api/chat", catch_response=True) as r:
            body = r.content.decode()
            if '"type": "done"' not in body:
                r.failure("no done event")

    @task(2)
    def next_question(self):
        self.client.post("/api/eligibility/next", json={"profile": {"state": "Telangana"}, "lang": "te"})

    @task(1)
    def source(self):
        self.client.get("/api/sources/ts_rythu_bharosa.md/page/2?quote=Investment%20support")
