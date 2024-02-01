import time

from redis.asyncio import Redis

if __name__ == "__main__":
    redis = Redis()
    while True:
        if redis.ping():
            break
        print("w8 4 redis")
        time.sleep(5)
