# Recogni

Recogni is a movie analysis app. A user selects a movie, the app validates and analyzes it, the user reviews detected character results, and the app exports selected clips.

## MVP workflow

1. Select a movie.
2. Validate the file. If validation fails, show the reason and return to movie selection.
3. Analyze the movie asynchronously.
4. Review and correct character results.
5. Select results and export clips.
6. Show export completion and provide the resulting files.

## Architecture

The initial design separates the web interface, API, and media-analysis worker. The API owns workflow state and metadata; large media files and exports live in object storage; long-running analysis and export work runs asynchronously. See [docs/architecture.md](docs/architecture.md) and [docs/product-scope.md](docs/product-scope.md).

## Repository layout

```
apps/web/             Web interface
services/api/         HTTP API and workflow orchestration
services/worker/      Media analysis and clip export jobs
packages/contracts/   API schemas and generated client types
infra/local/          Local development services
docs/                 Product scope and architecture decisions
```

The directories will be added with their first implementation files. The repository currently contains the project overview and design documents; application code and the recognition model have not been selected yet.
