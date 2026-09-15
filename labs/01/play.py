
import json
import time

file_path = 'fixture.json'

def stream_json (file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        print("Streaming file records...")
        #f.seek(0, 2)
        while True:
            line = f.readline()
            if line and line.strip():
                try:
                    data = json.loads(line)
                    yield data
                except json.JSONDecodeError:
                    print(f"Error decoding JSON: {line.strip()}")
            else:
                time.sleep(0.1)  # Sleep briefly to avoid busy waiting

starting = time.monotonic()
for update in stream_json(file_path):
    # i want to first wait for the time specified in the update, then print the update
    # but im not waiting for the time itself but the gap between the start of the stream and the time specified in the update
    # so we start by time equals zero and find first record saying timestamp at 1000 so we wait for a second then print record, 
    # then we find next record saying timestamp at 4200 so we wait for 3.2 seconds then print record, 
    # then we find next record saying timestamp at 9000 so we wait for 4.8 seconds then print record, and so on

    target = starting + update["t_ms"] / 1000
    time.sleep(max(0, target - time.monotonic()))
    print(f"timestamp: {update['t_ms'] / 1000} seconds, text: {update['text']}")
