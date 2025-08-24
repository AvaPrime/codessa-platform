from locust import HttpUser, task, between
import json
import random

class MultiAgentFactoryUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Authenticate user on start"""
        response = self.client.post("/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        self.token = response.json()["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})
    
    @task(3)
    def submit_documentation_task(self):
        """Submit documentation tasks (most common)"""
        task_data = {
            "task_id": f"doc-{random.randint(1000, 9999)}",
            "role": "doc_writer",
            "payload": {
                "doc_type": "api",
                "content": "Generate API documentation",
                "format": "markdown"
            }
        }
        self.client.post("/tasks", json=task_data)
    
    @task(2)
    def check_task_status(self):
        """Check task status (frequent operation)"""
        task_id = f"doc-{random.randint(1000, 9999)}"
        self.client.get(f"/tasks/{task_id}")
    
    @task(1)
    def submit_development_task(self):
        """Submit development tasks (less frequent)"""
        roles = ["frontend_dev", "backend_dev"]
        task_data = {
            "task_id": f"dev-{random.randint(1000, 9999)}",
            "role": random.choice(roles),
            "payload": {
                "framework": "react",
                "requirements": ["responsive", "accessible"]
            }
        }
        self.client.post("/tasks", json=task_data)