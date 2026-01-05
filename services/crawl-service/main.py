from listener import connect, listen
from schemas import normalize_event, is_valid
from queue import publish
import time

def start():
    connect()
    print("Start crawling TikTok Live comments...")

    for raw_event in listen():
        event = normalize_event(raw_event)

        if is_valid(event):
            publish(event)
            print("Published:", event["content"])


if __name__ == "__main__":
    while True:
        try:
            start()
        except Exception as e:
            print("Error:", e)
            print("Reconnecting...")
            time.sleep(5)
