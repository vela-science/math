#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import sys


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True, type=pathlib.Path)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--expected-payload-sha256", required=True)
    parser.add_argument("--expected-payload-bytes", required=True, type=int)
    args = parser.parse_args()

    runner = args.runner.read_bytes()
    runner_sha256 = sha256(runner)
    assert runner_sha256 == args.expected_runner_sha256
    assert b'if [[ "$work_root" != /* ]]; then' in runner
    assert b'docker run --rm -i --name "rb01-${cell,,}"' in runner

    payload = sys.stdin.buffer.read()
    payload_sha256 = sha256(payload)
    assert len(payload) == args.expected_payload_bytes
    assert payload_sha256 == args.expected_payload_sha256

    result = {
        "network_required": False,
        "payload_bytes": len(payload),
        "payload_sha256": payload_sha256,
        "runner_absolute_work_root_guard": True,
        "runner_docker_stdin_attachment": "-i",
        "runner_sha256": runner_sha256,
        "schema": "results-breakthrough-stdin-sentinel.v1",
        "sentinel": "pass",
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
