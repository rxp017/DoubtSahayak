#!/usr/bin/env python3
"""Serve the trained DoubtSahayak LoRA adapter on Modal's free Starter tier.

Why Modal: it is the only route found (12 Nov 2026) that serves this model
for zero real money. Starter is $0/month with $30 of compute credits every
month (recurring), billed per second, scale-to-zero — no idle charge, no
card needed for the free credits. A Gemma-3-4B + LoRA on an L4 (~$0.80/hr
GPU-only) costs ~$1 per GPU-hour all-in; the app's traffic (a few questions
a day, scale-to-zero) is a few GPU-hours a month, well inside $30.

What it serves: the AutoScientist run 206fe3ca LoRA adapter (rank 32,
alpha 64, base google/gemma-3-4b-pt) via vLLM's OpenAI-compatible server,
so the app needs NO code change — only Vercel env vars (see
adaption/MODAL_DEPLOY.md).

What this file does NOT do: it cannot create the Modal account, the
Hugging Face account, or the tokens — those need the owner (see
MODAL_DEPLOY.md). It also never spends money: with no payment method on
the Modal account, usage hard-stops at the $30 free credits.

Deploy (owner, after the account/token steps in MODAL_DEPLOY.md):
    modal deploy adaption/modal_serve.py

Then set in Vercel (never in code):
    ADAPTION_BASE_URL=https://<workspace>--doubtsahayak-adaption-serve.modal.run/v1
    ADAPTION_MODEL=doubtsahayak
    ADAPTION_API_KEY=<the same value as the vllm-api-key Modal secret>
"""

import subprocess

import modal

APP_NAME = "doubtsahayak-adaption"
BASE_MODEL = "google/gemma-3-4b-pt"  # gated on Hugging Face — needs HF_TOKEN
BASE_MODEL_DIR = "/models/base"
ADAPTER_DIR = "/models/adapter"
LORA_NAME = "doubtsahayak"  # what the app sends as ADAPTION_MODEL
VOLUME_NAME = "doubtsahayak-adapter"
SECRET_NAME = "doubtsahayak-secrets"  # holds HF_TOKEN and VLLM_API_KEY

app = modal.App(APP_NAME)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm", "huggingface_hub")
)


def download_base_model():
    """Image-build step: bake the gated base model into the image so cold
    starts don't re-download ~8 GB. Runs with the HF_TOKEN secret."""
    import os

    from huggingface_hub import snapshot_download

    token = os.environ["HF_TOKEN"]
    snapshot_download(
        repo_id=BASE_MODEL,
        local_dir=BASE_MODEL_DIR,
        token=token,
    )
    print(f"Base model downloaded to {BASE_MODEL_DIR}")


image = image.run_function(
    download_base_model,
    secrets=[modal.Secret.from_name(SECRET_NAME)],
)

adapter_volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
secrets = [modal.Secret.from_name(SECRET_NAME)]


@app.function(
    image=image,
    gpu="L4",
    volumes={ADAPTER_DIR: adapter_volume},
    secrets=secrets,
    scaledown_window=60,  # scale to zero 60 s after the last request: $0 idle
    timeout=600,
)
@modal.web_server(port=8000, startup_timeout=10 * 60)
def serve():
    """Start vLLM's OpenAI-compatible server with the LoRA adapter.

    The app calls {ADAPTION_BASE_URL}/chat/completions with
    model=doubtsahayak and Bearer <VLLM_API_KEY>; vLLM routes that model
    name to the adapter. --max-lora-rank 32 is REQUIRED: the adapter's
    rank is 32 and vLLM's default is 16.
    """
    import os

    cmd = [
        "python",
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        BASE_MODEL_DIR,
        "--enable-lora",
        "--lora-modules",
        f"{LORA_NAME}={ADAPTER_DIR}",
        "--max-lora-rank",
        "32",
        "--chat-template",
        f"{ADAPTER_DIR}/chat_template.jinja",
        "--max-model-len",
        "4096",
        "--gpu-memory-utilization",
        "0.9",
        "--api-key",
        os.environ["VLLM_API_KEY"],
        "--port",
        "8000",
    ]
    subprocess.Popen(cmd)
