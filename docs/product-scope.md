# Recogni MVP scope

## Product summary

Recogni analyzes a user-selected movie, presents character results for review, and exports clips based on the reviewed results.

## Workflow from the project state chart

| State | User or system action | Next state |
|---|---|---|
| Waiting for Movie | User selects a movie | Validating Movie |
| Validating Movie | File passes validation | Processing Movie |
| Validating Movie | File is invalid; show an actionable reason | Validation Failed, then Waiting for Movie |
| Processing Movie | Analysis finishes | Character Results Ready |
| Character Results Ready | User opens results | Reviewing Results |
| Reviewing Results | User requests an export | Exporting Clips |
| Exporting Clips | Export succeeds | Completed |

Failures during processing or export need visible error states and retry behavior. The original chart only depicts validation failure and successful completion; those failure paths remain to be designed.

## MVP capabilities

- Select and upload a movie file.
- Validate the uploaded media before analysis.
- Track asynchronous analysis progress and report failures.
- Produce timestamped character detections or appearances.
- Let the user review results and correct character groupings or labels.
- Export clips for selected results and report when the files are ready.

## Explicitly undecided

The project context does not yet define supported formats and limits, whether identity means face matching or broader character recognition, the recognition model, clip boundary rules, user accounts, retention, or deployment target. Keep these choices configurable or behind interfaces until product requirements are confirmed. Do not claim that the app recognizes a person across different films unless that behavior is specifically designed and validated.
