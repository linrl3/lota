# Lota

LLM-powered Dota 2 analysis tool built with LangChain/LangGraph.

## Why I create it?
- I am a software engineer also a Dota2 player. As we all know LLM is hot today. It'd be a great idea to use LLM to analyze Dota2 and see its power.
- Dota2 analysis is not new. There are many tools and websites that provide Dota2 analysis. But this project is trying to combine different APIs with the power of LLM and natural language interface to provide a more comprehensive analysis.


## Features

- **Interactive AI Chat**: Natural language interface to analyze Dota 2 data
- **Patch Notes Search**: Search patch notes by keyword, hero, or item name
- **Hero Winrate Analysis**: Track hero performance across patches (via OpenDota)
- **Hero Counters & Matchups**: Find counters and good matchups for any hero
- **Pro Scene Data**: Recent pro matches and meta statistics
- **Ward Analysis**: Analyze ward placements with heatmap visualization
- **OpenAI Compatible**: Works with OpenAI API and compatible services

## Installation

```bash
# Using uv (recommended)
uv sync
uv run lota

# Or using pip
pip install -e .
lota
```

## Usage

### Interactive Chat (Default)

```bash
lota                    # Enter AI chat mode
lota chat               # Same as above
```

### Example Questions

```
What changed for Invoker in the last 3 patches?
Who counters Anti-Mage?
What are the most picked heroes in pro?
Show me recent pro matches
Which heroes have the highest winrate in 7.40?
How is Pudge's winrate trending?
Who are the best Invoker players?
What are Anti-Mage's abilities?
What tournaments are happening right now?
What items should I buy on Invoker?
```


## Configuration

Set environment variables for chat mode:

- `OPENAI_API_KEY` or `LOTA_API_KEY`: API key (required)
- `LOTA_API_BASE`: Custom API endpoint (optional)
- `LOTA_MODEL`: Model name (default: gpt-5-mini)

See `.env.example` for full configuration options.

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run linter
uv run ruff check lota

# Run tests
uv run pytest
```

## Contribution

All contributions (from human or AI agent) are welcome! Please feel free to submit a Pull Request.

## Future thought

- Add web interface because it's more user-friendly and easier to use. Web interface has better visualization for graph and map analysis.

- Support other LLM model.

- Make it stable and precise. The current version is a prototype.

## License

MIT
