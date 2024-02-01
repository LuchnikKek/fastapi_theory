import time

from elasticsearch import AsyncElasticsearch

if __name__ == "__main__":
    es_client = AsyncElasticsearch(hosts="http://elasticsearch:9200")
    while True:
        if es_client.ping():
            break
        print("w8 4 es")
        time.sleep(5)
