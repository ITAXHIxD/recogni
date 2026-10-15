# Initial architecture

## Design direction

Start with one monorepo and three deployable parts: an editor-facing web app, an API service, and a background worker. Keep the API and worker in one Python codebase initially. Put provider-specific AI behavior behind adapters so Ollama, Gemini, and additional supported APIs can evolve independently of the workflow.

Recommended starting stack:

- Web: React with TypeScript.
- API and worker: Python with FastAPI and a Redis-backed task queue.
- Metadata: PostgreSQL.
- Source movies, derived frames, and exports: private S3-compatible object storage.
- Media inspection, scene preparation, and compilation: FFprobe and FFmpeg.
- Local development: Docker Compose for PostgreSQL, Redis, and object storage.

The recognition model and exact provider protocol are not selected. Implement them behind stable interfaces rather than coupling job logic to one vendor.

## Components and responsibilities

- **Web app**: movie selection and upload, provider/model configuration, analysis progress, scene and character review, corrections, export controls, and downloads.
- **API service**: validate requests and uploaded media, create analysis/export jobs, manage workflow state and provider configuration, expose results, and authorize project assets.
- **Worker**: inspect video, derive scene candidates and timecoded frame context, call the selected provider adapter, validate and persist analysis, then compile character videos.
- **Provider adapters**: normalize provider configuration and structured responses. Start with Ollama and Gemini adapters. Add a generic API adapter only for explicit supported protocols; arbitrary APIs need provider-specific authentication and media capabilities.
- **PostgreSQL**: projects when defined, media metadata, provider references, jobs, scenes, character groups, review edits, segment timecodes, and export metadata.
- **Object storage**: original movies, sampled frames/thumbnails, and rendered character compilations. Store references and checksums in PostgreSQL; never store video binaries in Git.
- **Redis/task queue**: dispatch long-running analysis and export work and communicate progress.

## Analysis and export flow

1. The web app requests an upload and transfers the movie to private object storage using short-lived authorization from the API.
2. The API verifies the upload, probes it with FFprobe, applies configured size/duration/container limits, and records the media asset.
3. The user selects a provider and model. The API creates an analysis job with a reference to the selected provider configuration.
4. The worker detects candidate scene boundaries, prepares timecoded visual context, and calls the selected adapter. If the provider accepts only images, send sampled frames; if it supports video, use its supported video input and limits.
5. Validate the provider response as structured scene ranges and character appearances. Reject or flag timestamps outside the source duration. Save raw analysis separately from user review edits.
6. The web app presents scenes grouped by character. The editor can rename characters, correct assignments, and remove or add scene membership before export.
7. An export job gathers each selected character’s scene ranges in chronological order, applies confirmed padding/audio/output rules, and renders one video compilation per character with FFmpeg.
8. Verify every output, store it privately, and provide the editor with a download link and a manifest mapping output segments back to source timecodes.

## Provider configuration and privacy

- Support local Ollama and remote Google Gemini as separate adapters; make local versus cloud processing clear in the UI.
- Keep credentials server-side. Encrypt user-provided API keys at rest, restrict access by project/user when that model is defined, redact secrets from logs, and never return keys to the browser after submission.
- Do not send an entire movie to a remote provider by default. Prepare only the media context required by the selected provider, show what will be sent, and honor that provider’s limits and privacy settings.
- Store provider/model identifiers and safe request metadata with each job, not raw secrets.
- Make provider failure, rate limits, unsupported media, and malformed output visible and retryable without losing the uploaded movie or review work.

## Workflow state

Keep analysis and export as separate jobs. Suggested analysis states: `uploaded`, `validating`, `queued`, `processing`, `results_ready`, `failed`, `cancelled`. Validation failure should return the user to movie selection with a reason. Suggested export states: `queued`, `processing`, `completed`, `failed`, `cancelled`.

Persist state transitions and timestamps. Make job creation and retries idempotent. A retry must not duplicate scene records or exports. Treat provider responses and uploaded media as untrusted input.

## Initial repository structure

```
apps/
  web/                    React/TypeScript editor interface
services/
  api/                    FastAPI endpoints and workflow orchestration
  worker/                 Background media analysis and compilation
packages/
  contracts/              OpenAPI schemas and generated web client types
infra/
  local/                  Docker Compose and local service configuration
docs/
  product-scope.md
  architecture.md
```

Keep this as one repository. Split services only if ownership, deployment, or scaling needs justify it.

## Security and reliability baseline

- Enforce configured upload size, duration, and accepted-media limits.
- Validate actual media content with FFprobe; do not trust filenames or browser MIME types.
- Isolate media processing and avoid shell interpolation.
- Keep movies and exports private; issue short-lived authorized download links.
- Encrypt API credentials, keep secrets out of client code and logs, and exclude local media from Git.
- Separate user-safe failure messages from internal diagnostics.
- Define retention, quotas, authentication, and multi-user authorization before offering shared projects.

## Open decisions before implementation

Confirm accepted video formats and limits, exact provider protocols and model configuration, scene-boundary padding, whether compilations keep source audio, output formats/quality, export naming/packaging, and collaboration/account requirements. The first vertical slice should upload and validate a movie, analyze one selected provider’s timecoded scene/character output, let the editor correct it, and export a single character compilation with a source-timecode manifest.
