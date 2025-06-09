#!/usr/bin/env python3
"""
migrate_redis.py

High-speed migration of all keys (incl. RedisJSON) from Upstash → local Redis
Uses batching + pipelining to minimize network round-trips.
Requires: pip install redis python-dotenv
"""

import sys
import os
from dotenv import load_dotenv
import redis

# load variables from .env into os.environ
load_dotenv()

# 1) Upstash (source) connection from env:
UPSTASH_HOST     = os.getenv("UPSTASH_HOST")
UPSTASH_PORT     = int(os.getenv("UPSTASH_PORT", 6379))
UPSTASH_PASSWORD = os.getenv("UPSTASH_PASSWORD")
USE_TLS          = True

# 2) Local Redis (destination) connection:
LOCAL_HOST = 'localhost'
LOCAL_PORT = 6379
LOCAL_DB   = 0

# You can bump this up if you have the memory/bandwidth
BATCH_SIZE = 50

def connect_redis(host, port, password=None, ssl=False, db=0):
    return redis.Redis(
        host=host,
        port=port,
        password=password,
        ssl=ssl,
        db=db,
        decode_responses=False
    )

def migrate_db(src, dst, db=0, batch_size=BATCH_SIZE):
    # make sure both are on the same logical DB
    src.execute_command('SELECT', db)
    dst.execute_command('SELECT', db)

    cursor = 0
    total = 0
    while True:
        cursor, keys = src.scan(cursor=cursor, count=batch_size)
        if not keys and cursor == 0:
            break

        # 1) Pipeline all TYPE calls
        type_pipe = src.pipeline()
        for k in keys:
            type_pipe.type(k)
        types = type_pipe.execute()

        # split JSON vs “other” keys
        json_keys  = [k for k, t in zip(keys, types) if t == b'json']
        other_keys = [k for k, t in zip(keys, types) if t != b'json']

        # 2) Pipeline JSON.GET + TTL for JSON keys
        json_pipe = src.pipeline()
        for k in json_keys:
            json_pipe.execute_command('JSON.GET', k)
            json_pipe.ttl(k)
        json_results = json_pipe.execute()

        # 3) Pipeline DUMP + TTL for other keys
        other_pipe = src.pipeline()
        for k in other_keys:
            other_pipe.dump(k)
            other_pipe.ttl(k)
        other_results = other_pipe.execute()

        # 4) Pipeline restore on destination
        restore_pipe = dst.pipeline()
        # 4a) re-create JSON keys
        for i, k in enumerate(json_keys):
            val, ttl = json_results[2*i], json_results[2*i+1]
            restore_pipe.execute_command('JSON.SET', k, '.', val)
            if ttl and ttl > 0:
                restore_pipe.expire(k, ttl)

        # 4b) re-create standard keys
        for i, k in enumerate(other_keys):
            blob, ttl = other_results[2*i], other_results[2*i+1]
            if blob is None:
                continue
            pttl = (ttl * 1000) if (ttl and ttl > 0) else 0
            restore_pipe.restore(k, pttl, blob, replace=True)

        restore_pipe.execute()

        total += len(keys)
        print(f"  Migrated batch of {len(keys)} keys; cursor={cursor}", end='\r')

        if cursor == 0:
            break

    print(f"\n✅ Migration complete: {total} keys moved.")

if __name__ == '__main__':
    try:
        src = connect_redis(
            UPSTASH_HOST, UPSTASH_PORT,
            password=UPSTASH_PASSWORD,
            ssl=USE_TLS
        )
        dst = connect_redis(LOCAL_HOST, LOCAL_PORT, db=LOCAL_DB)
        print(f"Starting migration: Upstash → local Redis DB {LOCAL_DB}")
        migrate_db(src, dst, db=LOCAL_DB)
    except Exception as e:
        print(f"❌ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)