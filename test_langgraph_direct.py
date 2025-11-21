"""
Debug script to see what LangGraph actually returns
"""

import asyncio
import httpx
import json


async def test_langgraph_direct():
    """Test LangGraph directly to see message structure"""
    
    payload = {
        "assistant_id": "supervisor",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "Hello! Can you help me find a laptop?"
                }
            ]
        },
        "config": {
            "configurable": {
                "thread_id": "test-thread-123"
            }
        }
    }
    
    print("Calling LangGraph directly...")
    print(f"URL: http://localhost:2024/runs/stream")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            "http://localhost:2024/runs/stream",
            json=payload
        ) as response:
            print(f"Status: {response.status_code}\n")
            
            event_count = 0
            values_events = []
            
            current_event = None
            current_data = []
            
            async for line in response.aiter_lines():
                line = line.strip()
                
                if line.startswith("event:"):
                    # Save previous event
                    if current_event and current_data:
                        data_str = "\n".join(current_data)
                        if current_event == "values":
                            try:
                                data_obj = json.loads(data_str)
                                values_events.append(data_obj)
                            except:
                                pass
                    
                    current_event = line.split(":", 1)[1].strip()
                    current_data = []
                    event_count += 1
                
                elif line.startswith("data:"):
                    data_content = line.split(":", 1)[1].strip()
                    current_data.append(data_content)
                
                elif line == "":
                    # End of event
                    if current_event and current_data:
                        data_str = "\n".join(current_data)
                        if current_event == "values":
                            try:
                                data_obj = json.loads(data_str)
                                values_events.append(data_obj)
                                print(f"Values event #{len(values_events)}: "
                                      f"{len(data_obj.get('messages', []))} messages")
                            except:
                                pass
                    current_event = None
                    current_data = []
            
            print(f"\nTotal events: {event_count}")
            print(f"Values events: {len(values_events)}")
            
            if values_events:
                print(f"\n{'='*60}")
                print("LAST VALUES EVENT")
                print(f"{'='*60}")
                last_event = values_events[-1]
                messages = last_event.get("messages", [])
                print(f"Total messages: {len(messages)}\n")
                
                for i, msg in enumerate(messages):
                    msg_type = msg.get("type", msg.get("role", "unknown"))
                    content = msg.get("content", "")
                    if isinstance(content, dict):
                        content = str(content)
                    content_preview = content[:100] if content else "(no content)"
                    
                    print(f"[{i}] {msg_type}: {content_preview}")
                
                print(f"\n{'='*60}")
                print("LAST MESSAGE DETAILS")
                print(f"{'='*60}")
                last_msg = messages[-1]
                print(json.dumps(last_msg, indent=2))


if __name__ == "__main__":
    asyncio.run(test_langgraph_direct())
