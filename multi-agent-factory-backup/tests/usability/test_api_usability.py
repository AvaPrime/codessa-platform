class TestAPIUsability:
    def test_error_message_clarity(self):
        """Test that error messages are helpful"""
        # Submit invalid task
        response = self.client.post("/tasks", json={"invalid": "data"})
        error_msg = response.json()["detail"]
        
        # Verify error message is descriptive
        assert "required" in error_msg.lower()
        assert "role" in error_msg or "payload" in error_msg
    
    def test_response_consistency(self):
        """Test consistent response formats"""
        endpoints = ["/tasks", "/agents", "/results"]
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Verify consistent structure
            assert "data" in response.json() or "items" in response.json()