package maf.policies

# Default deny
default allow = false

# Allow doc_writer role
allow {
    input.role == "doc_writer"
    input.action == "process_task"
}

# Allow frontend_dev role  
allow {
    input.role == "frontend_dev"
    input.action == "process_task"
}

# Allow backend_dev role
allow {
    input.role == "backend_dev" 
    input.action == "process_task"
}

# Allow qa_tester role
allow {
    input.role == "qa_tester"
    input.action == "process_task" 
}

# Allow compliance_checker role
allow {
    input.role == "compliance_checker"
    input.action == "process_task"
}

# Resource limits by role
max_concurrent_tasks[role] = count {
    role_limits := {
        "doc_writer": 5,
        "frontend_dev": 3, 
        "backend_dev": 3,
        "qa_tester": 10,
        "compliance_checker": 2
    }
    count := role_limits[role]
}
