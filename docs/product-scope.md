# Recogni MVP scope

## Product summary

Recogni is an AI-assisted tool for editors. It analyzes a movie, groups scenes by the characters appearing in them, and creates one reviewable video compilation per character for use in an editing workflow.

## Workflow from the project state chart and user clarification

| State | User or system action | Next state |
|---|---|---|
| Waiting for Movie | User selects a movie and an AI provider | Validating Movie |
| Validating Movie | File and provider configuration pass checks | Processing Movie |
| Validating Movie | Invalid file or configuration; explain the issue | Validation Failed, then Waiting for Movie |
| Processing Movie | Analyze scenes and character appearances | Character Results Ready |
| Character Results Ready | User opens results | Reviewing Results |
| Reviewing Results | User corrects scenes or character groupings and requests export | Exporting Clips |
| Exporting Clips | Create one chronological compilation for each selected character | Completed |

The flow chart shows validation failure and successful completion. Processing and export failures need visible error states and retry behavior.

## MVP capabilities

- Select and validate a movie file.
- Choose local Ollama, Google Gemini, or another provider implemented through a supported adapter.
- Analyze scene boundaries and return timestamped character appearances.
- Review, rename, merge, split, and correct character groupings before export.
- Export one video compilation per character, assembled from that character's scenes.
- Preserve source timecodes for every selected segment so an editor can trace compilation footage back to the original movie.
- Track analysis and export progress and report actionable failures.

## Provider behavior

Keep provider integration behind a common adapter. Each adapter declares capabilities such as native video input or image input, accepted media limits, structured-output support, and whether the service is local or remote. Use native video input when supported; otherwise prepare timecoded representative frames or scene excerpts according to that provider's limits.

“Any API” needs a defined supported protocol or adapter contract. Do not claim compatibility with arbitrary endpoints until their authentication, request, video, and response formats are implemented. Validate provider responses against a schema and movie duration before showing or exporting results.

## Explicitly undecided

The project context does not specify supported video formats, upload limits, whether exported compilations retain original audio, transition or padding rules around scene boundaries, output codecs/resolutions, the exact provider protocols, or whether projects need accounts and collaboration. These choices should be confirmed before implementing the end-to-end media pipeline.

For cloud providers, make the selected provider and the media sent to it visible to the user. Local Ollama should remain a local processing option when configured that way. Protect user-supplied API keys and never expose them in logs or client-side code.
