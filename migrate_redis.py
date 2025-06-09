#!/usr/bin/env python3
"""
migrate_redis.py

Migrate all keys (incl. RedisJSON) from a remote Upstash Redis to a local Redis.
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

# 2) Configure your local Redis (destination) connection:
LOCAL_HOST = 'localhost'
LOCAL_PORT = 6379
LOCAL_DB = 0

def connect_redis(host, port, password=None, ssl=False, db=0):
    return redis.Redis(
        host=host,
        port=port,
        password=password,
        ssl=ssl,
        db=db,
        decode_responses=False
    )

def migrate_db(src, dst, db=0, batch_size=1000):
    # Select the same logical DB on both ends
    src.execute_command('SELECT', db)
    dst.execute_command('SELECT', db)

    cursor = 0
    while True:
        cursor, keys = src.scan(cursor=cursor, count=batch_size)
        for key in keys:
            t = src.type(key)
            if t == b'json':
                # Export & re-import JSON tree
                val = src.execute_command('JSON.GET', key)
                dst.execute_command('JSON.SET', key, '.', val)
                ttl = src.ttl(key)
                if ttl and ttl > 0:
                    dst.expire(key, ttl)
            else:
                # Use DUMP/RESTORE for all other types
                blob = src.dump(key)
                if blob:
                    ttl = src.ttl(key)
                    pttl = (ttl * 1000) if (ttl and ttl > 0) else 0
                    dst.restore(key, pttl, blob, replace=True)
        if cursor == 0:
            break

if __name__ == '__main__':
    try:
        src = connect_redis(
            UPSTASH_HOST, UPSTASH_PORT,
            password=UPSTASH_PASSWORD,
            ssl=USE_TLS
        )
        dst = connect_redis(LOCAL_HOST, LOCAL_PORT)
        print(f"Starting migration from Upstash @ {UPSTASH_HOST}:{UPSTASH_PORT} → local @ {LOCAL_HOST}:{LOCAL_PORT}/{LOCAL_DB}")
        migrate_db(src, dst, db=LOCAL_DB)
        print("✅ Migration complete.")
    except Exception as e:
        print(f"❌ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)