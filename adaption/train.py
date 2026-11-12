#!/usr/bin/env python3
"""Train the DoubtSahayak Adaption model on the GATE training dataset.

Follows the official Adaption AutoScientist quickstart
(docs.adaptionlabs.ai): upload the dataset, create an AutoScientist run,
wait for completion, download the best checkpoint.

Usage (owner only — needs his Adaption account):
    pip install "adaption>=0.7.0"
    ADAPTION_API_KEY=<key> python3 adaption/train.py

The key comes from the environment only — never put it in this file.
Without ADAPTION_API_KEY the script stops immediately with a clear
message and trains nothing.

What it does:
  1. Uploads adaption/training-data.csv (3,112 instruction/response rows)
     as a raw dataset (instruction -> prompt, response -> completion).
  2. Starts an AutoScientist run on it (base model auto-selected by
     Adaption; augmentation expands the 3,112 rows toward the
     recommended scale — the docs target >=20,000 domain rows plus
     general-purpose rows at 40% to avoid catastrophic forgetting).
  3. Waits for the run to finish and prints the job ID, base model and
     best win rate.
  4. Downloads the best checkpoint to adaption/best-checkpoint.tgz.
  5. Records everything in adaption/training-run.json (job ID, dataset
     ID, base model, status, credits used if reported, timestamps).

Cost: training is covered by the 1,000 free Adaption credits every
Build League participant gets. This script never enters payment details
and never deploys anything — serving the model (Together dedicated
endpoint, billed per GPU-hour) is a separate, manual step; see
adaption/README.md before deploying.
"""
import contextlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "adaption"
CSV_PATH = OUT_DIR / "training-data.csv"
RUN_JSON = OUT_DIR / "training-run.json"


def fail(msg: str, code: int = 2) -> None:
    print(f"BLOCKED: {msg}", file=sys.stderr)
    sys.exit(code)


def _clean_no_proxy() -> None:
    """Drop bracketed IPv6 entries ([::1], [fd8b:...]) from NO_PROXY.

    Same sandbox quirk as backend/solver.py: httpx rejects those entries
    at Client() construction (InvalidURL: Invalid port), which crashes the
    Adaption SDK before any request. localhost, 127.0.0.1 and unbracketed
    ::1 still bypass the proxy. No-op on Vercel, where no such entries
    exist.
    """
    for key in ("no_proxy", "NO_PROXY"):
        if key not in os.environ:
            continue
        kept = [e for e in os.environ[key].split(",")
                if not (e.strip().startswith("[") and e.strip().endswith("]"))]
        os.environ[key] = ",".join(kept)


def _upload_file_curl(client, csv_path: Path) -> str:
    """Upload the CSV via the SDK create + curl PUT + SDK complete.

    The SDK's own upload_file() PUTs the file with httpx, which stalls
    with a WriteTimeout from this sandbox (the egress proxy + httpx
    chunked streaming). The same presigned S3 PUT via curl succeeds in
    ~2s, so the file transfer goes through curl and everything else
    stays on the SDK. On failure the half-created dataset is deleted,
    mirroring the SDK's own cleanup.
    """
    import hashlib
    import subprocess

    dataset_id = None
    try:
        resp = client.datasets.create(source={
            "file_format": "csv",
            "name": csv_path.stem,
            "processing_mode": "raw",
            "column_mapping": {"prompt": "instruction", "completion": "response"},
        })
        dataset_id = resp.dataset_id
        url = resp.upload_instructions.url
        print(f"Dataset created: id={dataset_id}")
        file_bytes = csv_path.read_bytes()
        print(f"Uploading {csv_path} ({len(file_bytes)} bytes) via curl ...")
        curl = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", "600", "-X", "PUT", "--data-binary",
             f"@{csv_path}", "-H", "Content-Type: text/csv", url],
            capture_output=True, text=True, timeout=660,
        )
        if curl.returncode != 0 or curl.stdout.strip() != "200":
            raise RuntimeError(
                f"curl S3 PUT failed: returncode={curl.returncode} "
                f"http={curl.stdout.strip()} stderr={curl.stderr[:300]}"
            )
        print("S3 PUT done (HTTP 200).")
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        client.datasets.upload.complete_by_id(
            dataset_id, file_size_bytes=len(file_bytes), sha256=sha256
        )
        print("Upload completed.")
        return dataset_id
    except BaseException:
        if dataset_id:
            with contextlib.suppress(Exception):
                client.datasets.delete(dataset_id)
        raise


def main() -> None:
    api_key = os.environ.get("ADAPTION_API_KEY", "").strip()
    if not api_key:
        fail(
            "ADAPTION_API_KEY is not set. Create an Adaption account at "
            "https://adaptionlabs.ai, claim the 1,000 free Build League "
            "credits, create an API key in Settings -> API keys, then run:\n"
            "    ADAPTION_API_KEY=<key> python3 adaption/train.py\n"
            "No training was started and no credits were used."
        )
    _clean_no_proxy()
    if not CSV_PATH.exists():
        fail(f"Training data not found: {CSV_PATH}. Run "
             "python3 adaption/build_dataset.py first.")

    try:
        from adaption import Adaption
    except ImportError:
        fail('The Adaption SDK is not installed. Run: pip install "adaption>=0.7.0"')

    # Long per-request timeout: the upload + AutoScientist calls can be
    # slow, and the SDK default (60s) timed out twice on 12 Nov 2026
    # even though the API itself answers in ~1s when healthy.
    client = Adaption(timeout=300.0)  # reads ADAPTION_API_KEY from the environment
    started = datetime.now(timezone.utc).isoformat()
    print(f"[{started}] Uploading {CSV_PATH} ...")
    dataset_id = _upload_file_curl(client, CSV_PATH)
    print(f"Dataset uploaded: id={dataset_id}")
    print("Waiting for the dataset to be processed ...")
    status = client.datasets.get_status(dataset_id)
    print(f"Dataset status: row_count={getattr(status, 'row_count', status)}")

    print("Starting AutoScientist run (base model auto-selected) ...")
    run = client.autoscientist.create(dataset_id=dataset_id)
    run_id = getattr(run, "id", None) or run.get("id")
    print(f"Run started: id={run_id}")
    print("Waiting for completion (this can take a while) ...")
    run = client.autoscientist.wait_for_completion(run_id)
    best_win_rate = getattr(run, "best_win_rate", None)
    base_model = getattr(run, "model", None)
    print(f"Run finished: id={run_id} base_model={base_model} "
          f"best_win_rate={best_win_rate}")

    print("Downloading best checkpoint ...")
    with client.autoscientist.with_streaming_response.download(run_id) as resp:
        checkpoint_path = OUT_DIR / "best-checkpoint.tgz"
        with open(checkpoint_path, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    print(f"Checkpoint saved: {checkpoint_path}")

    record = {
        "run_id": run_id,
        "dataset_id": dataset_id,
        "dataset_file": "adaption/training-data.csv",
        "dataset_rows": sum(1 for _ in open(CSV_PATH, encoding="utf-8")) - 1,
        "base_model": str(base_model) if base_model else None,
        "best_win_rate": best_win_rate,
        "status": "completed",
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint": "adaption/best-checkpoint.tgz",
        "credits_used": None,  # fill in from the Adaption dashboard if shown
    }
    RUN_JSON.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Run record saved: {RUN_JSON}")
    print("NEXT: deploy the checkpoint (see adaption/README.md — check the "
          "serving cost first), then set ADAPTION_API_KEY + ADAPTION_MODEL "
          "in Vercel and redeploy.")


if __name__ == "__main__":
    main()
