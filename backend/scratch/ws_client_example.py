import asyncio
import websockets
import json
import sys

async def listen_to_execution(task_id: str):
    uri = f"ws://localhost:8000/ws/execution/{task_id}"
    print(f"Connecting to execution telemetry tracker for task: {task_id}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")
            print("Listening for stream updates...")
            
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "execution_log":
                    log = data["data"]
                    print(f"=> [{log['timestamp']}] {log['agent'].upper()} ({log['agent_name']}) - {log['status'].upper()}: {log['message']} [Elapsed: {log['duration']}]")
                    
    except websockets.exceptions.ConnectionClosed:
        print("❌ Connection closed by server.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ws_client_example.py <task_id>")
        sys.exit(1)
        
    target_task = sys.argv[1]
    asyncio.run(listen_to_execution(target_task))
