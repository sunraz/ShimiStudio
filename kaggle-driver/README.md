# Kaggle Poker Driver (v2a) — canonical sources

Fixes locked in here (11-12/10, Shimi-Dev):
- kernel_template.py: T4-safe dtypes — UMT5-XXL text encoder bf16 on CPU (no NaN black-output), VAE fp32, transformer fp16, cpu-offload + VAE tiling.
- kernel_template.py: range fix (mean255) — pipeline outputs float 0-1; old validator assumed 0-255 and misflagged healthy renders as BLACK.
- scenes_v2a.py: one-layer-per-scene wardrobe logic (friend scenario, ends at lingerie), body lock from BODY_LOCK.md.
- driver.py: parallel multi-slot Kaggle kernel launcher + slot polling + concat.

Usage: driver.py pushes kernel_template.py as a Kaggle script kernel per scene with SCENE injected from scenes_v2a.py.
