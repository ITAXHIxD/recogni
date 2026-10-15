# Recogni

Recogni is an AI-assisted movie workflow for editors. It analyzes a movie, separates scenes by the characters that appear in them, and creates one reviewable video compilation per character.

## MVP workflow

1. Select a movie and an AI provider: local Ollama, Google Gemini, or another supported API.
2. Validate the movie and provider configuration.
3. Analyze scenes and timestamped character appearances.
4. Review and correct scenes and character groupings.
5. Export one chronological video compilation for each character.
6. Keep source timecodes available so editors can trace a compilation segment back to the movie.

If movie validation fails, explain why and return to movie selection. Analysis and export run as background jobs.

## Architecture

The initial design separates the web interface, API, background media worker, and AI provider adapters. The worker prepares video and timecoded scene context for the selected provider, then validates the structured analysis before compiling character videos. See [docs/product-scope.md](docs/product-scope.md) and [docs/architecture.md](docs/architecture.md).

## Repository layout

```
apps/web/             Editor-facing web interface
services/api/         HTTP API and workflow orchestration
services/worker/      Scene analysis and character-video exports
packages/contracts/   API schemas and generated client types
infra/local/          Local development services
docs/                 Product scope and architecture
```

The repository currently contains design documents only. The recognition pipeline, supported provider protocols, and output settings are still to be implemented and confirmed.
