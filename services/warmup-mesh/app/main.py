import os
import time

import requests

POSTAL_API_URL = os.getenv("POSTAL_API_URL", "http://localhost:5000")


def main() -> None:
    while True:
        try:
            response = requests.get(f"{POSTAL_API_URL}/health", timeout=5)
            if response.ok:
                print("warmup mesh is ready")
                break
        except Exception as exc:
            print(f"waiting for postal: {exc}")
        time.sleep(5)

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
