#!/bin/bash
# Stress test script

echo "Starting stress test..."

# Gradually increase load
for users in 10 50 100 200 500 1000; do
    echo "Testing with $users concurrent users"
    locust -f locustfile.py --headless -u $users -r 10 -t 300s --host http://localhost:8000
    
    # Check system health
    curl -f http://localhost:8000/health || echo "System unhealthy at $users users"
    
    # Wait for system to stabilize
    sleep 30
done