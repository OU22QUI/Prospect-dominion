import os
import time

import redis


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def main() -> None:
    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    client.ping()
    print("worker connected to redis")

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
