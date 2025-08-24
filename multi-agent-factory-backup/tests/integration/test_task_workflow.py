@pytest.mark.asyncio
@pytest.mark.integration
class TestTaskWorkflow:
    @pytest.mark.critical
    async def test_complete_task_lifecycle(self, api_client):
        """Test full task submission to completion workflow"""
        # Submit task
        task_payload = {
            "task_id": "test-doc-001",
            "role": "doc_writer",
            "payload": {
                "doc_type": "api",
                "content": "Create API documentation",
                "format": "markdown"
            }
        }
        
        response = await api_client.post("/tasks", json=task_payload)
        assert response.status_code == 201
        task_id = response.json()["task_id"]
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Check task status
        status_response = await api_client.get(f"/tasks/{task_id}")
        assert status_response.status_code == 200
        assert status_response.json()["status"] in ["processing", "completed"]
        
        # Verify result persistence
        if status_response.json()["status"] == "completed":
            result_response = await api_client.get(f"/results/{task_id}")
            assert result_response.status_code == 200
            assert "content" in result_response.json()
    
    async def test_agent_communication(self, api_client):
        """Test NATS messaging between API and agents"""
        # Test message publishing and consumption
        pass
    
    async def test_database_operations(self, test_database):
        """Test database CRUD operations"""
        # Test vector store operations
        # Test task persistence
        # Test user management
        pass