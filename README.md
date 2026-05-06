# LLM Dixit arena

Have different LLMs play Dixit among them. To be used as a true benchmark of their ``reasoning'' capabilities.

## How to run

### 1. Setup

Requires Python 3.11+ and Node.js (for the frontend).

```bash
# install Python deps
pip install -e .

# create .env with provider API keys (OpenRouter primary, plus direct fallbacks)
# OPENROUTER_API_KEY=...
# OPENAI_API_KEY=...
# ANTHROPIC_API_KEY=...
# GOOGLE_API_KEY=...
# GROQ_API_KEY=...
# XAI_API_KEY=...
```

### 2. Run the API server

```bash
uvicorn src.api.main:app --reload --port 8000
# or
PYTHONPATH=src uvicorn api.main:app --reload --port 8000
```

### 3. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Run a game directly (CLI)

```bash
PYTHONPATH=src python src/dixitGame.py
```

### 5. Run tests

```bash
export PYTHONPATH=src
pytest
```

## Data

### Overviews
`data/overviews` contains the *original* Dixit card overviews as downloaded from https://www.libellud.com/en/resources/dixit/

### Other cards
https://uk.pinterest.com/cassagram/dixit-cards/

## Resources

- https://dl.acm.org/doi/abs/10.1145/3555858.3555863
- https://github.com/hav4ik/dixit-chatgpt
- https://arxiv.org/pdf/2010.00048
- https://arxiv.org/abs/2206.08349
- Interaction data: http://www.spronck.net/datasets/Dixit_AI_data.zip
