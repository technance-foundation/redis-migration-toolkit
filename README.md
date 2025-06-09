# Redis Migration Toolkit

A pair of Python CLI scripts to migrate **all** keys (including RedisJSON) from a remote Upstash Redis instance into a local Redis server. Includes both a simple, straightforward version and a high-speed, pipelined version to suit different needs.

---

## Features

-   ☁️ **Upstash Source**  
    Connects to your Upstash Redis (via TLS) using credentials from an `.env` file.

-   🖥️ **Local Destination**  
    Migrates into any locally running Redis instance.

-   🔄 **Full Data Fidelity**

    -   Preserves **all key types** (strings, hashes, lists, sets, sorted sets, and RedisJSON).
    -   Preserves **TTL** on each key.

-   🚀 **High-Speed Mode**
    -   Batches & pipelines commands to minimize network round-trips.
    -   Configurable batch size for throughput tuning.

---

## Prerequisites

-   Python 3.7+
-   A local Redis server running (default: `localhost:6379`, DB 0)
-   An Upstash Redis database (host, port, and password)
-   `pip`

---

## Installation

1. Clone this repo:

    ```bash
    git clone https://github.com/technance-foundation/redis-migration-toolkit.git
    cd redis-migration-toolkit
    ```

2. Install dependencies:

    ```bash
    pip install redis python-dotenv
    ```

3. Copy and edit the example environment file:

    ```bash
    cp .env.example .env
    # then edit .env to set UPSTASH_HOST, UPSTASH_PORT, UPSTASH_PASSWORD
    ```

---

## Configuration

Your `.env` file should look like this (no quotes):

```dotenv
UPSTASH_HOST=engaging-killdeer-16317.upstash.io
UPSTASH_PORT=6379
UPSTASH_PASSWORD=your_upstash_password_here
```

---

## Scripts

### 1. Basic Migration

**File:** `migrate_redis.py`
**Use when**: You need a quick, minimal-overhead migration without special optimizations.

```bash
python migrate_redis.py
```

What it does:

-   Uses SCAN to iterate keys in batches.
-   For non-JSON keys, runs `DUMP` + `RESTORE`.
-   For JSON keys, runs `JSON.GET` + `JSON.SET`.
-   Transfers TTLs.

### 2. High-Speed Migration

**File:** `migrate_redis_batch.py`
**Use when**: You want maximum throughput via pipelining.

```bash
python migrate_redis_batch.py
```

Key differences:

-   **Batch size** is configurable via the `BATCH_SIZE` constant.
-   **Pipelines** all TYPE calls → splits keys into JSON vs. other → pipelines GET/DUMP + TTL → pipelines RESTORE/SET back into local Redis.
-   Progress indicator per batch + total keys migrated.

---

## Usage Examples

1. **Run basic migration**

    ```bash
    python migrate_redis.py
    ```

2. **Run high-speed migration** (with custom batch size)

    ```bash
    # edit BATCH_SIZE in migrate_redis_batch.py, then:
    python migrate_redis_batch.py
    ```

3. **Migrate a different logical DB**

    - By default both scripts target DB 0.
    - To migrate DB 1, modify the `LOCAL_DB = 1` (and pass `db=1` to `migrate_db`) in the script.

---

## Troubleshooting

-   **Connection errors**:

    -   Verify your `.env` values.
    -   Ensure your local Redis is running (`redis-cli ping` returns `PONG`).

-   **Missing RedisJSON support**:

    -   Make sure your local Redis has the RedisJSON module installed (e.g. via Redis Stack).

---

> **Tip:** If you only need occasional, small-scale migrations, stick with the **basic** script. For large databases or frequent runs, the **high-speed** variant can cut migration time significantly.
