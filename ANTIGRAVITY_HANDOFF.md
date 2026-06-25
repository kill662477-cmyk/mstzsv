# CALMSV / MSTZSV Handoff for Google Antigravity

Last updated: 2026-06-25 21:10 KST

This repo is the `mstzsv` game project cloned into `C:\Users\silve\OneDrive\Desktop\CALMSV`.

- Branch: `main`
- Remote: `https://github.com/kill662477-cmyk/mstzsv.git`
- Base commit before this work: `f56387c`
- Local server used for verification: `http://127.0.0.1:5173/index.html`
- The current work is not committed yet.

## User Direction

The user wants this upgraded step by step, not all at once.

Core requirements:

- Keep the existing player character faces/images. The CAMMON people faces are the main point of the game.
- Character image cleanup/upscale is allowed only if the face identity stays intact.
- Character movement currently feels like floating; improve movement/hit/attack motion later.
- Existing weapons and overlapping effects should be upgraded, including function and balance changes.
- Bosses for stages 1-3 are not distinct enough; make them visually and mechanically different.
- Add stage 4 as the final boss stage, theme: `혼종 실험실`.
- After stage 4 clear, transition to Endless.
- Existing regular monsters looked weak; replace them.
- Stage 4 should be more difficult and have additional monsters.
- Use AetherAI/AetherForge API for asset generation.

## Security / API Key

Do not expose the API key in commits, logs, screenshots, or chat.

- API key file: `.env.local`
- Environment variable: `AETHERFORGE_API_KEY`
- Template file added: `.env.example`
- `.env.local` is ignored by `.gitignore`.

Auth has been verified successfully with:

```powershell
python .\tools\aether_assets.py auth-check
```

## AetherAI Integration

Docs referenced by the user:

- `https://api.aetherforgeai.com/getting-started/authentication`

Important API facts already confirmed:

- Auth header: `Authorization: Bearer <api_key>`
- Job polling: `GET /public/v1/job/{job_id}`
- Status values observed/docs: `Pending`, `Succeed`, `Failed`
- Generate Image: `POST /public/v1/generate/image`
  - fields: `prompt`, `ai_model`
  - optional: `ref_images`
- Generate Effect: `POST /public/v1/generate/effect`
  - fields: `description`, `resolution`
  - optional: `image`
- Upscale: `POST /public/v1/image-tune/upscale`
  - fields: `image`, `scale`
- Inpaint: `POST /public/v1/image-tune/inpaint`
  - fields: `image`, `prompt`
- Split Layer: `POST /public/v1/image-tune/split-layer`
  - fields: `image`, `keyword`
- Make Sprite: `POST /public/v1/sprite/make-sprite`
  - fields: `image`, `text`, `frame`, `is_pixel`
  - frame choices include `25`, `36`, `49`, `64`, `81`, `100`, `121`, `144`, `169`
- Reskin Sprite: `POST /public/v1/sprite/reskin`
  - fields: `image`, `sprite_subject`, `change_description`, `final_result_description`, `resolution`
  - optional style values include `pixel`, `cartoon`, `sd`, `quater_view`
- Character Overlay: `POST /public/v1/sprite/character-overlay`
  - fields: `sprite_sheet`, `character_images`, `rows`, `resolution`
  - optional `style`

Local tool added:

- `tools/aether_assets.py`
- `tools/aether_asset_prompts.json`
- `tools/AETHER_PIPELINE.md`

Useful commands:

```powershell
python .\tools\aether_assets.py auth-check
python .\tools\aether_assets.py models
python .\tools\aether_assets.py generate --asset map_stage4_ground --model "GPT Image 1.5" --no-ref --timeout 300
python .\tools\aether_assets.py generate --asset enemy_hybrid_stalker --model "GPT Image 1.5" --no-ref --timeout 300
python .\tools\aether_assets.py effect --description "short effect prompt" --resolution 1K --dry-run
python .\tools\aether_assets.py make-sprite .\monstarz-survivors-assets\enemy_runner.png --text "fast running loop" --frame 36 --dry-run
python .\tools\aether_assets.py promote .\aether-output\...\final-01.png --asset enemy_walker
python .\tools\aether_assets.py promote .\aether-output\...\cutout-01.png --asset enemy_hybrid_stalker --allow-new
```

Notes:

- Generated review folders go under `aether-output/`.
- Promoted asset backups go under `monstarz-survivors-assets-backup/`.
- Both are ignored by `.gitignore`.
- For transparent assets, Aether often leaves alpha-zero pixels with green RGB. Verify by compositing on a dark background; the alpha may be correct even if a simple viewer shows green.

## Codex Skills / Tools Used

Used:

- Local shell / PowerShell for repo inspection, running Python, git status, and server checks.
- `apply_patch` for file edits.
- `view_image` for visual inspection of generated PNGs.
- `browser:control-in-app-browser` skill for local browser verification.
- Node/browser runtime for checking the page loaded and that the asset pack reached `50/50`.

Not used:

- Built-in `imagegen` skill. The user specifically wants AetherAI API, so generation was done through `tools/aether_assets.py`.

Likely needed next:

- AetherAI image generation for boss images and effects.
- AetherAI effect generation for weapon VFX.
- AetherAI sprite endpoints only when working on character/monster animation sheets.
- Browser verification after each game code change.
- Manual gameplay/balance pass after weapon and boss changes.

## Completed Work

### Phase 0: AetherAI Pipeline

Completed.

Files added/updated:

- `.env.example`
- `.gitignore`
- `tools/aether_assets.py`
- `tools/aether_asset_prompts.json`
- `tools/AETHER_PIPELINE.md`

Verified:

```powershell
python -m py_compile .\tools\aether_assets.py
python .\tools\aether_assets.py models
python .\tools\aether_assets.py auth-check
```

### Phase 1: Maps

Completed.

Generated and promoted:

- `monstarz-survivors-assets/map_stage1_ground.png`
- `monstarz-survivors-assets/map_stage2_ground.png`
- `monstarz-survivors-assets/map_stage3_ground.png`
- `monstarz-survivors-assets/map_stage4_ground.png`

Generated output folders:

- `aether-output/20260625-202651-map_stage1_ground`
- `aether-output/20260625-202812-map_stage2_ground`
- `aether-output/20260625-202943-map_stage3_ground`
- `aether-output/20260625-203154-map_stage4_ground`

Preview:

- `aether-output/map-phase1-preview.png`

Backup folder:

- `monstarz-survivors-assets-backup/20260625-203634`

### Phase 2: Regular Monsters and Stage 4 Monsters

Completed.

Existing monsters replaced:

- `enemy_walker.png`
- `enemy_runner.png`
- `enemy_brute.png`
- `enemy_swarmling.png`
- `enemy_spitter.png`

Stage 4 monsters added:

- `enemy_hybrid_stalker.png`
- `enemy_lab_drone.png`
- `enemy_chimera_tank.png`

Generated output folders:

- `aether-output/20260625-205158-enemy_hybrid_stalker`
- `aether-output/20260625-205158-enemy_lab_drone`
- `aether-output/20260625-205158-enemy_chimera_tank`
- `aether-output/20260625-205611-enemy_walker`
- `aether-output/20260625-205611-enemy_runner`
- `aether-output/20260625-205611-enemy_brute`
- `aether-output/20260625-205611-enemy_swarmling`
- `aether-output/20260625-205611-enemy_spitter`

Previews:

- `aether-output/stage4-enemies-preview.png`
- `aether-output/enemy-phase2-preview.png`

Backup folder:

- `monstarz-survivors-assets-backup/20260625-210002`

### Phase 3: Stage 4 Progression Skeleton

Completed as a basic playable skeleton.

`index.html` changes:

- Added `FINAL_STAGE=4`.
- Stage 3 boss now opens portal to Stage 4 instead of starting Endless.
- Stage 4 boss clear now starts Endless and credits clear.
- Added stage 4 map loading.
- Added stage 4 fallback BGM key using stage 3 BGM for now.
- Added minimap tone for stage 4.
- Added 4th boss bullet pattern for stage 4.
- Added stage 4 pressure scaling and stage 4 monster spawn pool.
- Added loader slots for new stage 4 monsters.

Browser verification:

- Before monster additions: asset pack `47/47 loaded`.
- After monster additions: asset pack `50/50 loaded`.
- No console errors observed.
- Game start rendered correctly in browser.

## Current Git Status

As of the handoff:

```text
 M .gitignore
 M index.html
 M monstarz-survivors-assets/enemy_brute.png
 M monstarz-survivors-assets/enemy_runner.png
 M monstarz-survivors-assets/enemy_spitter.png
 M monstarz-survivors-assets/enemy_swarmling.png
 M monstarz-survivors-assets/enemy_walker.png
 M monstarz-survivors-assets/map_stage1_ground.png
 M monstarz-survivors-assets/map_stage2_ground.png
 M monstarz-survivors-assets/map_stage3_ground.png
?? .env.example
?? monstarz-survivors-assets/enemy_chimera_tank.png
?? monstarz-survivors-assets/enemy_hybrid_stalker.png
?? monstarz-survivors-assets/enemy_lab_drone.png
?? monstarz-survivors-assets/map_stage4_ground.png
?? tools/
```

This handoff file itself should also appear as untracked after it is created.

## Verification Commands

Use these after any code/asset changes:

```powershell
node -e "const fs=require('fs'),vm=require('vm');const html=fs.readFileSync('index.html','utf8');const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]);for(const [i,s] of scripts.entries())new vm.Script(s,{filename:'index.html#script'+i});console.log('parsed',scripts.length,'inline scripts');"
python -m py_compile .\tools\aether_assets.py
python .\tools\aether_assets.py auth-check
```

To run locally:

```powershell
python -m http.server 5173 --bind 127.0.0.1
```

Then open:

```text
http://127.0.0.1:5173/index.html
```

Expected loader status after current changes:

```text
Asset pack 50/50 loaded - characters, maps, enemies, props, and VFX are applied
```

## Recommended Next Phases

### Next Phase A: Boss 1-4 Distinction

This should probably be next.

Current gap:

- `index.html` still loads boss images only for stages 1-3.
- Rendering uses `SPR.boss[G.stage]`; stage 4 currently falls back visually if no sprite is available.
- Boss patterns are partially stage-scaled, but not truly themed per boss yet.

Recommended tasks:

- Add `boss_stage4.png` prompt to `tools/aether_asset_prompts.json`.
- Generate and promote `boss_stage4.png`.
- Update `ASSET_FILES.boss` to include stage 4.
- Update manual folder loader boss loop to use `FINAL_STAGE`.
- Regenerate or tune `boss_stage1.png`, `boss_stage2.png`, `boss_stage3.png` so each has a different silhouette.
- Add a small boss config table, e.g. `BOSS_TYPES`:
  - Stage 1: beast / simple radial
  - Stage 2: artillery / fan shots and warning circles
  - Stage 3: psionic hive / spiral and lances
  - Stage 4: hybrid lab final boss / grid, side-lanes, containment burst
- Generate or update boss-specific effects via AetherAI `effect`.

Suggested stage 4 boss prompt:

```text
Stage 4 final boss for a Korean web bullet-survivor game, hybrid laboratory monstrosity, fused alien tyrant inside broken containment armor, asymmetrical white gunmetal plating, exposed purple bio-core, cyan reactor veins, restraint cables, final boss silhouette, three-quarter top-down/isometric, centered full body on pure #00ff00 chroma key background, no text, no logo.
```

### Next Phase B: Weapon Function and VFX Rework

Current gap:

- Weapon visuals overlap in places.
- User wants function and balance changes too.

Recommended tasks:

- Inspect `WEAPONS` table in `index.html`.
- Group weapons by race/unit and make their gameplay roles clearer.
- Generate/replace VFX assets:
  - `fx_bullet.png`
  - `fx_muzzle.png`
  - `fx_psistorm.png`
  - `fx_explosion.png`
  - `fx_mine.png`
  - `fx_flame.png`
  - `fx_nova.png`
  - `fx_scarab.png`
  - `fx_glaive.png`
  - `fx_spikes.png`
  - `fx_heal.png`
- Use `python .\tools\aether_assets.py effect ...` for animated-looking single-frame effects.
- Keep balance conservative until after playtest.

### Next Phase C: Character Movement / Hit / Attack Motion

Do not regenerate character faces.

Recommended first step:

- Improve code-based motion in `drawPlayer()` / `drawActor()` before trying full sprite sheets.
- Add unit motion profiles:
  - infantry: footstep bob and attack lunge
  - vehicles: hover tilt / engine sway
  - flying units: smooth float, wing tilt
  - heavy units: slower squash, impact shake
  - caster units: glow pulse on attack

Later AetherAI usage:

- Use existing character image as reference.
- Consider `upscale`, `split-layer`, `make-sprite`, or `character-overlay`.
- For player characters, never create a new face identity. If Aether output changes the face, reject it.

### Next Phase D: Balance / Playtest

After bosses and weapons:

- Play through stages 1-4.
- Check clear time, XP curve, stage 4 pressure, boss damage, and enemy readability.
- Then discuss balance with the user before major numeric tuning.

## Known Caveats

- The source file has many Korean strings. Avoid broad encoding conversions or formatting passes.
- Use narrow edits only. Do not rewrite `index.html` wholesale.
- The Aether output folders are review artifacts and intentionally ignored.
- Backups of replaced assets exist under `monstarz-survivors-assets-backup/`.
- The current local server process may still be running on port `5173`; if the port is busy, use another port.
- Commit has not been made. Ask the user before committing if needed.

## Good Continuation Checklist

1. Run `git status --short`.
2. Read this file and `tools/AETHER_PIPELINE.md`.
3. Verify `.env.local` exists but do not print the key.
4. Run `python .\tools\aether_assets.py auth-check`.
5. Run the JS parse check.
6. Continue with boss phase first.
7. Verify browser loader count and console after each promoted asset batch.
8. Keep previews in `aether-output/` before promoting.
9. Commit only when the user says to.
