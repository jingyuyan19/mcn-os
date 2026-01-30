# Redis Queue Fix Summary

## Problem
The worker.py was not processing tasks from the Redis queue. Investigation revealed:

1. Tasks were being created in Redis (task:info:* keys existed)
2. Tasks were being added to the gpu_queue:normal queue
3. Worker's get_next_task() was failing silently
4. Root cause: Line 51 in redis_client.py tried to decode() a string that was already decoded

## Root Cause
In `/mnt/data_ssd/mcn/middleware/lib/redis_client.py`:

```python
# Line 13: Redis client initialized with decode_responses=True
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=0, decode_responses=True)

# Line 51: Attempted to decode an already-decoded string
return task[1].decode('utf-8')  # ❌ BUG: task[1] is already a string!
```

When `decode_responses=True` is set, Redis automatically decodes all responses to strings. Calling `.decode('utf-8')` on a string raises an AttributeError.

## Fix
Changed line 51 in `/mnt/data_ssd/mcn/middleware/lib/redis_client.py`:

```python
# Before (line 51):
return task[1].decode('utf-8')

# After (line 51):
return task[1]  # Already decoded as string
```

## Verification

### Test 1: Direct Redis Operations
```bash
docker exec mcn_core python3 -c "
from lib import redis_client
task_id = redis_client.enqueue_task('test', {'foo': 'bar'}, 10)
print('Enqueued:', task_id)
next_task = redis_client.get_next_task(1)
print('Dequeued:', next_task)
print('Type:', type(next_task))
"
```

Output:
```
Enqueued: 462e1631-65cf-4da6-9c1b-0e5d54b544cf
Dequeued: 462e1631-65cf-4da6-9c1b-0e5d54b544cf
Type: <class 'str'>
```

### Test 2: End-to-End Media Download
```bash
curl -X POST http://localhost:8000/media/download \
  -H "Content-Type: application/json" \
  -d '{"topic_id": "test-topic-123", "platforms": ["xhs"]}'
```

Result:
- ✅ Task enqueued to Redis
- ✅ Worker retrieved task from queue
- ✅ Worker processed task (failed due to missing MediaCrawlerPro, but that's expected)
- ✅ Task status updated to "failed" with error message

### Test 3: Automated E2E Test
Created `/mnt/data_ssd/mcn/middleware/test_redis_e2e.py` which verifies:
1. Task creation
2. Queue operations
3. Worker processing
4. Status updates

All tests passed ✅

## Files Modified
- `/mnt/data_ssd/mcn/middleware/lib/redis_client.py` (line 51)

## Files Created
- `/mnt/data_ssd/mcn/middleware/test_redis_fix.py` - Basic Redis operations test
- `/mnt/data_ssd/mcn/middleware/test_redis_e2e.py` - End-to-end integration test

## Worker Status
The worker is now running inside the mcn_core container and successfully processing tasks:

```bash
docker exec mcn_core tail -f /tmp/worker.log
```

## Next Steps
To make the worker persistent across container restarts, consider:
1. Adding worker.py to the container's startup script
2. Using a process manager (supervisord) inside the container
3. Creating a separate worker container in docker-compose.yml
