# 1️⃣ Public Documentation Rewrite (Docs-portal ready)

## Q.Bot (Agent Starter Pack)

Q.Bot is a Python-based **agent starter pack** that helps teams build, deploy, and operate production-ready GenAI agents on Google Cloud.

It provides opinionated templates, infrastructure, and tooling so you can focus on **agent logic**, not platform setup.

---

## What You Get

**From prototype to production, out of the box:**

* Pre-built agent templates (ReAct, RAG, multi-agent, real-time)
* Production-ready infrastructure (CI/CD, observability, security)
* Local development + cloud deployment workflows
* Extensible templates you can customize to your needs

---

## Quick Start (1 Minute)

Create a new agent project using [`uv`](https://docs.astral.sh/uv/getting-started/installation/):

```bash
uvx agent-starter-pack create
```

That’s it. You now have a working agent project with backend, frontend, and deployment configuration.

### Alternative: pip

<details>
<summary>Use pip instead of uv</summary>

```bash
python -m venv .venv && source .venv/bin/activate
pip install --upgrade agent-starter-pack
agent-starter-pack create
```

</details>

---

## Enhance an Existing Agent

Already have an agent? Add production infrastructure without rewriting it:

```bash
uvx agent-starter-pack enhance
```

This adds CI/CD, deployment, and observability to your existing project.

---

## Available Agent Templates

| Agent         | Description                                                            |
| ------------- | ---------------------------------------------------------------------- |
| `adk`         | Base ReAct agent using Google’s Agent Development Kit                  |
| `adk_a2a`     | ADK agent with Agent-to-Agent (A2A) protocol support                   |
| `agentic_rag` | Retrieval-augmented generation with Vertex AI Search and Vector Search |
| `langgraph`   | ReAct agent built with LangChain’s LangGraph                           |
| `adk_live`    | Real-time multimodal RAG (audio, video, text) powered by Gemini        |

More templates are added regularly. Feature requests are welcome.

---

## Key Features

* **CI/CD Automation**
  One-command setup for Google Cloud Build or GitHub Actions.

* **RAG Data Pipelines**
  Terraform-managed ingestion pipelines for embeddings and search.

* **Remote Templates**
  Share and consume templates from any Git repository.

* **Gemini CLI Integration**
  Query your agent architecture and template directly from the terminal.

---

## Architecture Overview

Q.Bot supports the full agent lifecycle:

* Prototyping
* Evaluation
* Deployment
* Monitoring and observability

*(High-level architecture diagram available in the documentation.)*

---

## Requirements

* Python 3.10+
* Google Cloud SDK
* Terraform (for deployment)
* Make

---

## Documentation & Learning

* Documentation site:
  [https://googlecloudplatform.github.io/agent-starter-pack/](https://googlecloudplatform.github.io/agent-starter-pack/)
* Getting Started
* Installation
* Deployment
* Agent templates overview
* CLI reference

### Video Walkthroughs

* Exploring the Agent Starter Pack (full tutorial)
* 6-minute introduction (Kaggle GenAI Intensive)

---

## Community & Support

* Community showcase of real projects
* Contributions welcome
* GitHub issues for bugs and feature requests
* Email: [agent-starter-pack@google.com](mailto:agent-starter-pack@google.com)

---

## Disclaimer

This repository is for demonstration purposes and is not an officially supported Google product.

---

# 2️⃣ Internal Onboarding Summary (New Engineers – One Page)

## What is Q.Bot?

Q.Bot is a **production-ready agent starter pack** for building GenAI agents on Google Cloud. It gives you templates, infra, and tooling so you don’t have to assemble everything from scratch.

---

## What You’ll Use Most

* Agent templates (ReAct, RAG, real-time)
* CLI (`agent-starter-pack`)
* CI/CD + deployment configs
* Observability hooks

---

## First 15 Minutes

```bash
uvx agent-starter-pack create
cd <new-project>
```

Explore:

* `agents/` – agent logic
* `infra/` – Terraform + deployment
* `frontend/` – UI
* `.github/` or `cloudbuild.yaml` – CI/CD

---

## If You Already Have an Agent

```bash
uvx agent-starter-pack enhance
```

This adds deployment, CI/CD, and monitoring without changing your agent logic.

---

## When to Use Q.Bot

Use it when you want:

* A fast path to production
* Opinionated defaults
* Cloud-native deployment on Google Cloud
* RAG or multi-agent patterns without boilerplate

---

## What Q.Bot Is *Not*

* Not a low-level SDK
* Not a research sandbox
* Not framework-agnostic by default

It favors **speed, consistency, and production readiness**.

---

## Where to Learn More

* Docs site (primary reference)
* Agent templates overview
* Architecture diagram
* Video walkthroughs

---

## Mental Model

> “Q.Bot gives you the rails.
> You build the agent.”

---
