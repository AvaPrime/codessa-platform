from guardrails import Guard

action_guard = Guard().use_schema({
  "type": "object",
  "properties": {
    "action": {"enum": ["READ","WRITE","CALL_API"]},
    "payload": {"type": "object"}
  },
  "required": ["action","payload"]
})
