# DiffusionGemma 26B-A4B on the Gemini Platform with vLLM

Deploy, test, and benchmark Google DeepMind's **DiffusionGemma 26B-A4B** (`nvidia/diffusiongemma-26B-A4B-it-NVFP4`) on a Dedicated Endpoint on the **Gemini platform** using the official upstream **vLLM** container (`vllm/vllm-openai:v0.31.0`) on a single 24 GB **`NVIDIA_L4`** GPU (`g2-standard-8`).

This project implements **Single-Step Structured Diffusion Reads (System One)** over `/v1/chat/completions`: evaluating multiple typed questions (`choice`, `score`, `boolean`) simultaneously in **1 forward pass** across a masked JSON token canvas, returning calibrated marginal probabilities and Shannon entropy confidence scores.

---

## Infrastructure & Architecture

| Layer | Configuration | Details |
| :--- | :--- | :--- |
| **Compute & Accelerator** | `g2-standard-8` (`1x NVIDIA_L4`) | `8 vCPUs`, `32 GiB` host RAM, and `1x NVIDIA L4` GPU (`24 GiB` GDDR6 VRAM). |
| **Model & Quantization** | `nvidia/diffusiongemma-26B-A4B-it-NVFP4` | Mixture-of-Experts (`26B` total parameters, `4B` active per token) quantized to `NVFP4` (`~20.54 GiB` VRAM footprint on the L4). |
| **Serving Container** | `vllm/vllm-openai:v0.31.0` | Official upstream vLLM release image mirrored in Artifact Registry (`--diffusion-config={"canvas_length": 64}`, `--max-logprobs=32`, `--max-num-seqs=16`, `--gpu-memory-utilization=0.92`). |
| **Endpoint Topology** | Dedicated Endpoint (`use_dedicated_endpoint=True`) | Direct HTTP/2 `rawPredict` routing without intermediate shared proxy overhead, supporting concurrent request batching on the GPU. |

---

## Project Structure

| File | Purpose |
| :--- | :--- |
| [`.env`](.env) | Default environment variables (`GOOGLE_CLOUD_REGION`, `DIFFUSIONGEMMA_MODEL_ID`, etc.) with no hardcoded project IDs. |
| [`requirements.txt`](requirements.txt) | Python dependencies for the local client, benchmark scripts, and Jupyter notebook. |
| [`config.py`](config.py) | Shared configuration module for `.env` loading, project ID resolution, and default model/endpoint constants. |
| [`deploy_diffusiongemma.py`](deploy_diffusiongemma.py) | CLI and Python module to deploy, redeploy, or delete the vLLM + DiffusionGemma Dedicated Endpoint. |
| [`diffusiongemma_client.py`](diffusiongemma_client.py) | Core client module defining [`DiffusionGemmaClient`](diffusiongemma_client.py) and [`resolve_endpoint`](diffusiongemma_client.py). |
| [`run_example.py`](run_example.py) | CLI example script for running single-step structured diffusion reads. |
| [`benchmark_load.py`](benchmark_load.py) | High-parallelism `asyncio` + `httpx` HTTP load engine and multi-concurrency saturation sweep (`1..16` workers). |
| [`benchmark_quality.py`](benchmark_quality.py) | Dataset quality evaluators (`banking77`, `ag_news`, `boolq`, `sst5`) and summary table builder. |
| [`monitoring.py`](monitoring.py) | Cloud Monitoring hardware utilization fetcher (`NVIDIA_L4` GPU & CPU metrics) and Google Cloud Experiments run logger. |
| [`benchmark_diffusiongemma.py`](benchmark_diffusiongemma.py) | CLI orchestrator combining dataset quality evaluations, concurrency sweeps, Cloud Monitoring metrics, and Experiments logging. |
| [`tests/`](tests/) | Offline 1-to-1 unit test suite (`test_config.py`, `test_diffusiongemma_client.py`, `test_deploy_diffusiongemma.py`, `test_run_example.py`, `test_benchmark_load.py`, `test_benchmark_quality.py`, `test_monitoring.py`, `test_benchmark_diffusiongemma.py`). |
| [`../gemini_platform_vllm_diffusiongemma_structured_outputs.ipynb`](../gemini_platform_vllm_diffusiongemma_structured_outputs.ipynb) | End-to-end tutorial and benchmark notebook in `open-models/serving/`. |

---

## Prerequisites & Setup

### 1. Install Python Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade -r requirements.txt
```

### 2. Configure Environment Variables (`.env`)

Edit [`.env`](.env) or export your Google Cloud project ID in your shell:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_REGION="us-central1"
```

### 3. Mirror the Official vLLM Image to Artifact Registry (One-Time)

Online Prediction on the Gemini platform requires container images to reside in **Google Cloud Artifact Registry** (`*.pkg.dev`); it cannot pull directly from external registries like `docker.io`.

Instead of downloading and pushing the ~15 GB `vllm/vllm-openai:v0.31.0` image on your workstation, run the following commands once per project to create the `containers` repository and copy the image directly from Docker Hub to Artifact Registry inside Google Cloud using Cloud Build and [`crane`](https://github.com/google/go-containerregistry/blob/main/cmd/crane/README.md) (~20 seconds, no local Docker daemon required):

```bash
gcloud artifacts repositories create containers \
    --repository-format=docker \
    --location=us \
    --project="${GOOGLE_CLOUD_PROJECT}"

gcloud builds submit --no-source \
    --project="${GOOGLE_CLOUD_PROJECT}" \
    --config=/dev/stdin <<'EOF'
steps:
  - name: 'gcr.io/go-containerregistry/crane:latest'
    args:
      - 'copy'
      - '--platform=linux/amd64'
      - 'docker.io/vllm/vllm-openai:v0.31.0'
      - 'us-docker.pkg.dev/$PROJECT_ID/containers/vllm-openai:v0.31.0'
EOF
```

**What this repository contains**:
- It stores **only the `vllm/vllm-openai:v0.31.0` Docker image layers** (the vLLM server, PyTorch, and CUDA/Triton runtime libraries). It does **not** store the DiffusionGemma model weights (`nvidia/diffusiongemma-26B-A4B-it-NVFP4`), which `vllm serve` downloads from Hugging Face at container startup.

---

## Usage

### 1. Deploy the Endpoint

```bash
python3 deploy_diffusiongemma.py \
    --project "${GOOGLE_CLOUD_PROJECT}" \
    --region us-central1
```

- Uses `--max-num-seqs=16` by default so vLLM batches concurrent requests on the `NVIDIA_L4` GPU.
- Pass `--redeploy` to update an existing endpoint with new container flags, or `--delete` to undeploy and delete all resources when finished.

### 2. Send Structured Diffusion Requests

```bash
python3 run_example.py \
    --project "${GOOGLE_CLOUD_PROJECT}" \
    --region us-central1 \
    --runs 5
```

### 3. Run Unit Tests

The unit test suite runs completely offline in `<0.1s` using a deterministic fake tokenizer and mocked Google Cloud SDK objects:

```bash
python3 -m unittest discover -s tests -v
```

### 4. Run Quality, Saturation Load-Testing & GPU/CPU Utilization Benchmarks

Evaluates model quality across four standard Hugging Face benchmarks (**`legacy-datasets/banking77`**, **`fancyzhx/ag_news`**, **`google/boolq`**, and **`SetFit/sst5`**), runs a high-parallelism concurrency sweep (`1, 2, 4, 8, 16` workers), fetches endpoint **GPU and CPU utilization** from Google Cloud Monitoring (`google.cloud.monitoring_v3`), writes `benchmark_results.json`, and logs the run to **Google Cloud Experiments**:

```bash
python3 benchmark_diffusiongemma.py \
    --project "${GOOGLE_CLOUD_PROJECT}" \
    --region us-central1 \
    --tasks banking77,ag_news,boolq,sst5 \
    --num-samples 100 \
    --concurrency 1,2,4,8,16 \
    --requests-per-level 600 \
    --fetch-utilization \
    --experiment diffusiongemma-benchmarks
```

- Pass `--num-samples 0` to evaluate **all 16,160 examples** across all four datasets (`3,080` Banking77, `7,600` AG News, `3,270` BoolQ, and `2,210` SST-5).
- Pass `--requests-per-level 600` (with `--fetch-utilization`) so each concurrency level runs for 1–3 minutes (~7.5 minutes total across `c = 1, 2, 4, 8, 16`), allowing Cloud Monitoring's 60-second sampling to record GPU duty cycle (`%`), GPU memory bandwidth (`%`), GPU VRAM (`GiB`), and CPU utilization (`%`) at each concurrency stage.

### 5. Interactive Jupyter Notebook (`gemini_platform_vllm_diffusiongemma_structured_outputs.ipynb`)

Open [`../gemini_platform_vllm_diffusiongemma_structured_outputs.ipynb`](../gemini_platform_vllm_diffusiongemma_structured_outputs.ipynb) in VS Code, JupyterLab, or Colab to interactively:
1. Run the offline `unittest` suite inside the notebook.
2. Deploy (or reuse) the `diffusiongemma-vllm` Dedicated Endpoint on `1x NVIDIA_L4`.
3. Execute a single-step structured diffusion read (`DiffusionGemmaClient`).
4. Run the multi-minute concurrency sweep (`c = 1, 2, 4, 8, 16`) and inspect the **Concurrency vs. GPU/CPU Saturation DataFrame** and minute-by-minute hardware time series.
5. Run the dataset quality benchmarks (`NUM_SAMPLES = 100`, `1000`, or `0` for all `16,160` examples) and compare historical runs from Google Cloud Experiments.

### 6. Clean Up Resources

To stop ongoing GPU charges when you are done testing:

```bash
python3 deploy_diffusiongemma.py \
    --project "${GOOGLE_CLOUD_PROJECT}" \
    --region us-central1 \
    --delete
```
