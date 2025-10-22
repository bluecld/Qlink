import concurrent.futures
import statistics
import time
import urllib.error
import urllib.request

BASE = "http://100.81.88.76:8000"
# Sample load ids to hit (a subset to mimic opening a room with multiple loads)
LOAD_IDS = [249, 250, 251, 252, 253, 254, 255, 256, 257, 258]

CONCURRENCY = 10
DURATION = 30  # seconds

end = time.time() + DURATION

results = []


def hit_load(load_id):
    url = f"{BASE}/load/{load_id}/status"
    start = time.time()
    try:
        with urllib.request.urlopen(url, timeout=6) as r:
            _ = r.read()
        latency = time.time() - start
        return True, latency
    except Exception as e:
        return False, repr(e)


with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
    futures = []
    while time.time() < end:
        for lid in LOAD_IDS:
            futures.append(ex.submit(hit_load, lid))
        # throttle a bit to avoid overwhelming the bridge
        time.sleep(0.2)

    # collect
    for f in concurrent.futures.as_completed(futures, timeout=10):
        try:
            ok, data = f.result()
            results.append((ok, data))
        except Exception as e:
            results.append((False, repr(e)))

success = [r[1] for r in results if r[0] is True]
failures = [r[1] for r in results if r[0] is False]

print(f"Total requests: {len(results)}")
print(f"Successes: {len(success)}")
print(f"Failures: {len(failures)}")
if success:
    try:
        p95 = statistics.quantiles(success, n=20)[18]
    except Exception:
        p95 = max(success)
    print(
        f"latency ms: min={min(success) * 1000:.1f} avg={statistics.mean(success) * 1000:.1f} p95={p95 * 1000:.1f}"
    )
if failures:
    print("Recent failures examples:")
    for f in failures[:5]:
        print(f)
