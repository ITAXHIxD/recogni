# Model assets

## SFace recognition model

- File: models/face_recognition_sface_2021dec.onnx
- Source: OpenCV Zoo, face_recognition_sface model directory.
- License: Apache 2.0, as stated in the upstream model README.
- Repository size: 38,696,353 bytes (about 36.9 MiB). It remains a regular tracked model asset; the measured file is below GitHub's 100 MB single-file limit. Git LFS is not configured in this repository.

## YuNet face detector

The application obtains face_detection_yunet_2023mar.onnx from the official OpenCV Zoo media endpoint on first use. It is cached under the user's local RECOGNI models directory and is not copied into the source repository. The video, sampled frames, face crops, and embeddings are processed locally and are not uploaded.

The detector download requires an internet connection once. The app checks that the downloaded file is non-empty before replacing its cache file. A future packaging milestone should pin a model revision and checksum.
