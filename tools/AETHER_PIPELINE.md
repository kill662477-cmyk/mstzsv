# AetherAI Pipeline

This repo uses `tools/aether_assets.py` for AetherAI asset work. Keep the API key
only in `.env.local`.

## Safe Checks

```powershell
python .\tools\aether_assets.py auth-check
python .\tools\aether_assets.py models
python .\tools\aether_assets.py generate --asset enemy_walker --dry-run
python .\tools\aether_assets.py effect --description "blue plasma bullet effect, transparent-friendly, no text" --dry-run
```

## Main Commands

```powershell
# Image generation from manifest
python .\tools\aether_assets.py generate --asset enemy_walker --model "GPT Image 1.5"

# Effect generation
python .\tools\aether_assets.py effect --name fx-plasma --description "top-down blue plasma projectile, transparent-friendly, no text" --resolution 1K

# Existing image tuning
python .\tools\aether_assets.py upscale .\monstarz-survivors-assets\peanut_zealot.png --scale 2K
python .\tools\aether_assets.py inpaint .\monstarz-survivors-assets\enemy_walker.png --prompt "make the armor more biomechanical"
python .\tools\aether_assets.py split-layer .\monstarz-survivors-assets\peanut_zealot.png --keyword face

# Sprite tools
python .\tools\aether_assets.py make-sprite .\monstarz-survivors-assets\enemy_runner.png --text "fast running loop" --frame 36
python .\tools\aether_assets.py reskin-sprite .\monstarz-survivors-assets\enemy_brute.png --sprite-subject "alien brute" --change-description "hybrid laboratory armor" --final-result-description "hybrid laboratory brute monster" --style quater_view
```

## Promotion

Generated review files stay in `aether-output/`. Promote only selected finals:

```powershell
python .\tools\aether_assets.py promote .\aether-output\<run>\final-01.png --asset enemy_walker
```

Promotion backs up the old asset under `monstarz-survivors-assets-backup/`.
