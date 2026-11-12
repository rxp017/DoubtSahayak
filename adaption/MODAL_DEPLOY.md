# Serving the trained model for $0 — Modal free tier

Status (12 Nov 2026): the model is **trained** (AutoScientist run
`206fe3ca`, base `google/gemma-3-4b-pt`, best win rate 0.545) but **not
deployed**. The app's Adaption mode falls back to BharatCode Qwen until
this is deployed. This page is the only zero-real-money route found.

## Why Modal (and why not the others)

| Route | Verdict | Cost |
|---|---|---|
| **Modal Starter (chosen)** | **$0/mo + $30/mo recurring compute credits**, per-second billing, scale-to-zero ($0 idle). L4 GPU ~$0.80/hr GPU-only (~$1/hr all-in). The app's traffic is a few GPU-hours a month — inside the free $30. No card is needed for the free credits; without a payment method, usage hard-stops at $30, so no real money can be spent. | $0 real money |
| Together AI dedicated endpoint | Works, OpenAI-compatible, but $5.49/hr per H100, billed per minute while a replica is ready, billed while idle (~$132/day). No free trial; prepaid credits required (min $15 purchase). | ~$132/day |
| Fireworks serverless LoRA | Pay-per-token, no idle charge — but only **one** supported base model (GLM 5.3 Flash). Adapters on any other base model (ours is gemma-3-4b-pt) can't load. | n/a — unsupported |
| Hugging Face ZeroGPU | Free, but **5 GPU-minutes/day**, Gradio-only, account must be 30+ days old, no always-on API. A demo toy, not a serving route. | $0, unusable |
| Adaption credits | **No inference product exists.** Adaption's docs and Python SDK offer only Adaptive Data + AutoScientist (training). There is nothing to spend the 1,250 credits on for serving. | n/a |

## What needs the owner (cannot be done by Muse)

1. **Modal account** — sign up free at https://modal.com (Starter plan,
   $0). Then on your own machine:
   `pip install modal && modal setup` (opens a browser to create a token).
2. **Hugging Face account + Gemma license** — create an account at
   https://huggingface.co, accept the Gemma license at
   https://huggingface.co/google/gemma-3-4b-pt (gated model), then
   create a read token at https://huggingface.co/settings/tokens.
3. **Modal secret** — `modal secret create doubtsahayak-secrets
   HF_TOKEN=<your HF token> VLLM_API_KEY=<pick any long random string;
   this becomes the app's ADAPTION_API_KEY>`.
4. **Adapter volume** — extract the checkpoint and upload it once:
   ```
   mkdir -p /tmp/ckpt && tar -I zstd -xf adaption/best-checkpoint.tgz -C /tmp/ckpt
   modal volume create doubtsahayak-adapter
   modal volume put doubtsahayak-adapter /tmp/ckpt adapter/
   ```
   (The volume must contain `adapter/adapter_config.json`,
   `adapter/adapter_model.safetensors`, `adapter/chat_template.jinja`, …)

## Deploy (owner, after the steps above)

```
cd <repo root>
modal deploy adaption/modal_serve.py
```

Note the web endpoint URL it prints, e.g.
`https://<workspace>--doubtsahayak-adaption-serve.modal.run`.

## Wire the app (Vercel env vars — never in code)

| Vercel var | Value |
|---|---|
| `ADAPTION_BASE_URL` | `<modal endpoint URL>/v1` (note the `/v1` — vLLM serves OpenAI paths under it) |
| `ADAPTION_MODEL` | `doubtsahayak` (the LoRA name vLLM routes to the adapter) |
| `ADAPTION_API_KEY` | the same `VLLM_API_KEY` value from the Modal secret (NOT the Adaption API key) |

No app code change is needed: `backend/solver.py` already posts
OpenAI-style chat completions to `{ADAPTION_BASE_URL}/chat/completions`
with the Bearer key and model name. Redeploy Vercel after setting the
vars, pick "Adaption-tuned" in the app, and ask a GATE question.

## Honest limits

- **Cold start:** the first request after idle takes ~1–2 minutes
  (container start + vLLM loading the 8 GB base model). The app's
  solver times out at 60 s, so that first request falls back to
  BharatCode Qwen and says so; the next request (container warm) uses
  the tuned model. Keeping a container warm 24/7 would cost ~$700+/mo
  — that is exactly what the free tier cannot do, so don't.
- **Free-tier ceiling:** $30/month ≈ 25–30 L4 GPU-hours. At the app's
  traffic (a few questions a day, scale-to-zero) that is plenty, but if
  usage ever spikes past it, Modal halts the endpoint until the next
  month — it does not charge without a payment method on file.
- **vLLM flag that matters:** the adapter is rank 32 and vLLM's
  default `--max-lora-rank` is 16 — `modal_serve.py` passes 32. If you
  ever re-train with a different rank, update that flag.
