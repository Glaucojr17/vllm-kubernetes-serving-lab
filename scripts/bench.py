#!/usr/bin/env python3
"""Smoke e latência de uma API OpenAI compatível, sem dependências externas."""
import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def percentile(values, fraction):
    if not values:
        return 0.0
    values = sorted(values)
    position = (len(values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (position - low)


def call(base, model, api_key):
    body = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': 'Responda com uma frase: o que é uma readiness probe?'}],
        'max_tokens': 48,
        'temperature': 0,
    }).encode()
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    request = urllib.request.Request(base.rstrip('/') + '/v1/chat/completions', data=body, headers=headers)
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
        if not payload.get('choices'):
            return False, time.monotonic() - start, 'resposta sem choices'
        return True, time.monotonic() - start, ''
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return False, time.monotonic() - start, str(exc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--model', default='qwen-0.5b-lab')
    parser.add_argument('--requests', type=int, default=10)
    parser.add_argument('--concurrency', type=int, default=2)
    parser.add_argument('--api-key', default='')
    args = parser.parse_args()
    if not 1 <= args.requests <= 1000 or not 1 <= args.concurrency <= 32:
        parser.error('requests: 1..1000; concurrency: 1..32')
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(call, args.url, args.model, args.api_key) for _ in range(args.requests)]
        results = [future.result() for future in as_completed(futures)]
    elapsed = time.monotonic() - started
    good = [latency for ok, latency, _ in results if ok]
    report = {
        'requests': len(results), 'success': len(good), 'errors': len(results) - len(good),
        'elapsed_s': round(elapsed, 3), 'rps': round(len(good) / elapsed, 2) if elapsed else 0,
        'latency_p50_s': round(statistics.median(good), 3) if good else None,
        'latency_p95_s': round(percentile(good, .95), 3) if good else None,
        'first_errors': [err for ok, _, err in results if not ok][:3],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if len(good) == len(results) else 1)


if __name__ == '__main__':
    main()
