# Shimi Poker — Canon of Prompts (v1 → v2d)

Every prompt version in the project history, in order. All renders are on Kaggle/Colab, Wan 2.2 TI2V-5B.

## Versions
- **v1** (shimi-poker-dev-s1..s10, Kaggle): brother scenario, 49 frames (3s), explicit at s5/s6/s10. Historical only — never re-render.
- **v2a** (`scenes_v2a.py` + `kaggle-driver/`): friend scenario (dark-haired woman, red flannel), 121 frames (7.5s), ends in black lace.
- **v2b** (`scenes.py`): the approved 10-scene movie, 121 frames, 7.5s each, full movie `poker-v2-full.mp4` (75.63s).
- **v2c** (`segments_v2c.py`, `driver_v2c.py`, `storyboard/shots_v2c.json`): 16 segments, 81 frames (5.06s) Iron Rule, pollinations storyboard 48 images.
- **v2d** (`segments_v2d.py`, `driver_v2d.py`, `storyboard/shots_v2d_scenes.json`): 20 segments a/b split (81 frames each), bust-locked, ~101s.
- **Storyboard v3** (`storyboard/shots_v3.json`, 53 shots): contact-point interaction shots (p12_d..p16_d) + full lace texture descriptors.
- **Bonus** (`driver_bonus.py`): dance segments b1/b2 appended to the full movie (lace, friend, 121 frames).

## Locked rules
- 81 frames (5.06s) per segment for v2c/v2d (Iron Rule, anti-distortion). v2b/bonus use 121 frames to match the existing movie.
- LOCKED BODY block in every prompt: hourglass, full natural bust, narrow waist, wide hips.
- No explicit/exposed content at any stage of rendering (v1 text kept for history only).
- Anchoring: each scene/segment anchors on the previous end frame (locked dress-state).

## Render params
- v2b/bonus: 121 frames, steps 20-26, cfg 5.0, seed 7, 832x480.
- v2c/v2d: 81 frames, steps 16-26, cfg 1.0 (DMD) or 5.0, seed varies per shot (see shot JSONs).
