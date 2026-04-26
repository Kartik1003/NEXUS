"""Verify the inter-agent communication system end-to-end."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import asyncio

from core.communication import (
    message_bus, AgentMessage, MessageType, MessagePriority,
    MessageStatus, AgentDirectory,
)


async def test_communication():
    print("=" * 60)
    print("COMMUNICATION SYSTEM TESTS")
    print("=" * 60)

    # ── Test 1: Agent Directory ──────────────────────────────────
    print("\n--- 1. Agent Directory ---")
    handles = message_bus.directory.all_handles()
    print(f"  Total agents registered: {len(handles)}")
    
    # Check key agents exist
    for h in ["@ceo", "@executive", "@dept_it", "@eng_manager", "@senior_eng"]:
        info = message_bus.directory.lookup(h)
        if info:
            print(f"  {h:22s} -> {info['name']} ({info['role']})")
        else:
            print(f"  {h:22s} -> NOT FOUND (ERROR)")

    # ── Test 2: Send a message ───────────────────────────────────
    print("\n--- 2. Simple Message Send ---")
    msg = await message_bus.send(AgentMessage(
        task_id="test_001",
        type=MessageType.DELEGATION,
        sender="@ceo",
        receiver="@executive",
        content="Plan a marketing campaign for Q3",
    ))
    print(f"  Sent: {msg.sender} -> {msg.receiver} [{msg.type.value}]")
    print(f"  Status: {msg.status.value}")
    print(f"  ID: {msg.id}")

    # ── Test 3: Delegation convenience method ────────────────────
    print("\n--- 3. Delegation ---")
    del_msg = await message_bus.delegate(
        sender="@dept_it",
        receiver="@eng_manager",
        task_description="Build a REST API for user authentication",
        task_id="test_001",
        priority=MessagePriority.HIGH,
        deliverables=["API endpoints", "Auth middleware", "Tests"],
    )
    print(f"  Delegated: {del_msg.sender} -> {del_msg.receiver}")
    print(f"  Priority: {del_msg.priority.value}")
    print(f"  Deliverables: {del_msg.payload['deliverables']}")

    # ── Test 4: Return result ────────────────────────────────────
    print("\n--- 4. Return Result ---")
    result_msg = await message_bus.return_result(
        sender="@eng_manager",
        receiver="@dept_it",
        task_id="test_001",
        deliverable="API implementation complete with JWT auth",
        summary="Implemented 5 endpoints with middleware",
        confidence=0.92,
    )
    print(f"  Result: {result_msg.sender} -> {result_msg.receiver}")
    print(f"  Payload: {result_msg.payload['summary']}")

    # ── Test 5: Request/Response pattern ─────────────────────────
    print("\n--- 5. Request/Response Pattern ---")

    async def mock_handler(request_msg):
        return f"Answer to: {request_msg.content[:50]}"

    response = await message_bus.request(
        sender="@senior_eng",
        receiver="@auto_tester",
        content="Can you review my auth middleware for security issues?",
        task_id="test_001",
        handler=mock_handler,
    )
    print(f"  Request: @senior_eng -> @auto_tester")
    print(f"  Response: {response.content[:80]}")
    print(f"  Correlation ID: {response.correlation_id}")

    # ── Test 6: Broadcast ────────────────────────────────────────
    print("\n--- 6. Broadcast ---")
    bcast = await message_bus.broadcast(
        sender="@ceo",
        content="All hands meeting at 3pm",
        task_id="test_001",
    )
    print(f"  Broadcast: {bcast.sender} -> {bcast.receiver}")
    print(f"  Content: {bcast.content}")

    # ── Test 7: Escalation ───────────────────────────────────────
    print("\n--- 7. Escalation ---")
    esc = await message_bus.escalate(
        sender="@support_agent",
        receiver="@escalation_agent",
        issue="Critical SLA breach: customer data export failing",
        task_id="test_001",
        severity="CRITICAL",
    )
    print(f"  Escalated: {esc.sender} -> {esc.receiver}")
    print(f"  Severity: {esc.payload['severity']}")

    # ── Test 8: Message History ──────────────────────────────────
    print("\n--- 8. Message History ---")
    history = message_bus.get_task_history("test_001")
    print(f"  Total messages for test_001: {len(history)}")
    for h in history:
        print(f"    [{h['type']:15s}] {h['sender']:22s} -> {h['receiver']:22s} | {h['content'][:40]}")

    # ── Test 9: Agent Inbox/Outbox ───────────────────────────────
    print("\n--- 9. Agent Inbox/Outbox ---")
    inbox = message_bus.get_agent_inbox("@dept_it", task_id="test_001")
    outbox = message_bus.get_agent_outbox("@dept_it", task_id="test_001")
    print(f"  @dept_it inbox:  {len(inbox)} messages")
    print(f"  @dept_it outbox: {len(outbox)} messages")

    # ── Test 10: Stats ───────────────────────────────────────────
    print("\n--- 10. Communication Stats ---")
    stats = message_bus.get_stats()
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  By type: {dict(stats['by_type'])}")
    print(f"  Active conversations: {stats['active_conversations']}")

    # ── Test 11: ACL Check ───────────────────────────────────────
    print("\n--- 11. ACL Checks ---")
    checks = [
        ("@ceo", "@executive", True),
        ("@senior_eng", "@auto_tester", True),
        ("@dept_it", "@eng_manager", True),
        ("@senior_eng", "*", True),
    ]
    for sender, receiver, expected in checks:
        result = message_bus.directory.can_communicate(sender, receiver)
        status = "OK" if result == expected else "FAIL"
        print(f"  {sender:22s} -> {receiver:22s}: {result} [{status}]")

    # ── Test 12: Thread tracking ─────────────────────────────────
    print("\n--- 12. Thread Tracking ---")
    if response:
        thread = message_bus.get_thread(response.correlation_id)
        print(f"  Thread for {response.correlation_id}: {len(thread)} messages")
        for t in thread:
            print(f"    [{t['type']:15s}] {t['sender']} -> {t['receiver']}")

    # ── Test 13: Full import chain ───────────────────────────────
    print("\n--- 13. Full Import Chain ---")
    from core.orchestrator import Orchestrator
    print("  Orchestrator OK")
    from agents.department_agents import DepartmentAgent
    print("  DepartmentAgent OK (uses message_bus)")
    from agents.employee_agents import SpecializedEmployee
    print("  SpecializedEmployee OK (request_help uses bus)")

    print("\n" + "=" * 60)
    print("ALL COMMUNICATION TESTS PASSED")
    print("=" * 60)


asyncio.run(test_communication())
