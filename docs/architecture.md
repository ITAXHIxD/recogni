# Initial architecture

## Design direction

Start with a small monorepo and three deployable parts: a web app, an API service, and a background worker. Keep the API and worker in one Python codebase initially so media-processing logic can be reused without introducing a separate service boundary.

Recommended starting stack:

- Web: React with TypeScript (Next.js unless deployment requirements point elsewhere).
- API and worker: Python with FastAPI and a Redis-backed task queue.
- Metadata: PostgreSQL.
- Movie uploads, frame thumbnails, and exported clips: S3-compatible object storage.
- Media inspection and cutting: FFprobe and FFmpeg.
- Local development: Docker Compose for PostgreSQL, Redis, and object storage.

These are starting choices, not requirements inferred from the diagram. Keep the character-detection and embedding implementation behind a worker interface; the project context does not identify a model or provider.

## Components and responsibilities

- **Web app**: movie selection, upload progress, job status, results review and correction, export selection, and download links.
- **API service**: validate requests and uploaded media, create analysis and export jobs, expose workflow status and results, and authorize access to project assets.
- **Worker**: probe media, decode/sample frames, detect and associate character appearances, persist timestamped results, and render requested clips.
- **PostgreSQL**: users/projects when defined, media metadata, jobs, workflow state, detection/track records, review edits, and export metadata.
- **Object storage**: original uploads, derived thumbnails, and exports. Store references and checksums in PostgreSQL; do not put media binaries in Git.
- **Redis/task queue**: dispatch long-running analysis and export jobs and communicate progress.

## Data and job flow

1. The web app requests an upload and sends the movie to object storage using a short-lived upload authorization from the API.
2. The API verifies the upload exists, probes it with FFprobe, checks configured size/duration/container limits, and records a validated media asset.
3. The API creates an analysis job and queues it. The web app polls or subscribes to job progress.
4. The worker samples frames, runs the replaceable recognition pipeline, and stores timestamped appearances and derived thumbnails.
5. The API serves reviewable results. User corrections are stored as review data; do not overwrite raw detections.
6. An export request creates a separate job. The worker renders clips from the source movie with FFmpeg and writes them to object storage.
7. The API marks the export complete only after the stored output has been verified and returns an authorized download link.

## Workflow state

Model analysis and export as separate jobs. Suggested analysis states: `uploaded`, `validating`, `validation_failed`, `queued`, `processing`, `results_ready`, `failed`, `cancelled`. Suggested export states: `queued`, `processing`, `completed`, `failed`, `cancelled`.

Persist state transitions and timestamps. Make job creation and retries idempotent. A worker retry must not duplicate results or exports. Keep progress events small and avoid exposing local paths or internal storage credentials.

## Initial repository structure

```
apps/
  web/                    React/TypeScript user interface
services/
  api/                    FastAPI endpoints and workflow orchestration
  worker/                 Background analysis and export jobs
packages/
  contracts/              OpenAPI schemas and generated web client types
infra/
  local/                  Docker Compose and local service configuration
docs/
  product-scope.md
  architecture.md
```

Keep this as one repository. Split services into separate repositories only if ownership, deployment, or scaling needs justify it.

## Security and reliability baseline

- Enforce upload size, duration, and accepted-media limits in configuration.
- Validate actual media content with FFprobe; do not trust filenames or browser MIME types.
- Treat uploaded movies and derived files as untrusted; isolate processing and avoid shell interpolation.
- Keep media private by default and issue short-lived authorized download links.
- Keep secrets out of source control; commit an example environment file only when implementation starts.
- Record failure reasons safe for users separately from internal diagnostics.
- Add authentication, retention, quotas, and multi-user authorization once the product’s user model is defined.

## Open decisions before implementation

Confirm supported formats and upload limits, what “character” recognition means, clip boundaries and output formats, single-user versus multi-user access, storage retention, deployment target, and whether face data needs special privacy handling. The first implementation should be a vertical slice: upload and validate one movie, enqueue a job, show progress, and persist a small set of timestamped results before selecting a production model.
