# CALMSV Current Work Status

Last updated: 2026-06-26 11:04 KST

## Context

Antigravity credits expired while it was fixing the Lurker weapon direction. Codex continued from the current dirty working tree without reverting Antigravity changes.

Latest pushed baseline before this note:

- `aaed599 feat: MONSTARZ SURVIVORS 2.0 대형 패치`
- `1f9801d fix: 타이틀 2.0 배지와 자석 드랍 보정 조정`

## Current Verified State

- `index.html` parses successfully with Node `vm.Script`.
- `tools/aether_assets.py` and `tools/supabase_assets.py` compile successfully.
- Browser local server tested at `http://127.0.0.1:5174/index.html`.
- Browser console had no errors or warnings during load.
- Asset loader reached `Asset pack [Local Fallback] 55/55 loaded`.
- Supabase asset dry-run reports 3 files pending upload after latest changes.

## Fixes Made After Antigravity Expired

### Lurker Weapon Direction

Problem:

- `fx_spikes.png` was a diagonal sprite, but `index.html` assumed the sprite extended horizontally to the right.
- This made the visible Lurker spike direction diverge from the damage hit line.
- The weapon also aimed using player movement direction, which felt wrong for an auto weapon.

Fix:

- Backed up the previous `fx_spikes.png`:
  - `monstarz-survivors-assets-backup/20260626-lurker-align/fx_spikes.png`
- Reprocessed `monstarz-survivors-assets/fx_spikes.png` into a horizontal left-to-right sprite strip.
- Updated `fire()` for `k === 'spikes'`:
  - aim at `nearestTarget(p.x, p.y)` when available
  - fallback to player face direction
  - spawn visual slightly ahead of the player
- Updated Lurker spike rendering:
  - draw the horizontal sprite from local x=0
  - clip reveal from `0` to `curLen`
  - rotate the whole sprite by `sp.ang`

Preview:

- `aether-output/weapon-fix-preview.png`

### Dragoon Projectile

Problem:

- Dragoon used the generic bullet effect, so the weapon looked too plain.

Fix:

- Generated a new AetherAI projectile:
  - `aether-output/20260626-004731-fx_dragoon/cutout-01.png`
- Promoted it to:
  - `monstarz-survivors-assets/fx_dragoon.png`
- Added `fx_dragoon` to `ASSET_FILES.fx`.
- Updated shot rendering:
  - `s.kind === 'dragoon'` uses `SPR.fx.dragoon`
  - size multiplier set to `5.4`
  - `lighter` blending enabled for dragoon projectiles
- Added `fx_dragoon` to `tools/aether_asset_prompts.json`.

## Commands That Passed

```powershell
node -e "const fs=require('fs'),vm=require('vm');const html=fs.readFileSync('index.html','utf8');const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]);for(const [i,s] of scripts.entries())new vm.Script(s,{filename:'index.html#script'+i});console.log('parsed',scripts.length,'inline scripts');"
python -m py_compile .\tools\aether_assets.py .\tools\supabase_assets.py
python .\tools\supabase_assets.py --dry-run
```

## Follow-Up Needed

- Upload latest changed assets to Supabase when ready:
  - dry-run currently detects 3 changed/new files, including `fx_dragoon.png` and `fx_spikes.png`.
- If testing unlocked characters is needed, do it in a normal browser or through the app UI because the in-app browser evaluation wrapper blocked localStorage mutation.
- Test Lurker and Dragoon in actual gameplay after unlocking/selecting `72` and `RANG`.

## Pre-Push Audit Update

Last updated: 2026-06-26 01:20 KST

Completed after the previous checkpoint:

- Added Supabase public asset URL wiring in `index.html`.
- Updated the remote/local manifest fallback flow.
- Uploaded changed assets to Supabase; latest dry-run reports `0` pending files.
- Added Stage 4 hybrid/drone/chimera monsters to the ordinary Stage 4 spawn pool.
- Fixed manual asset-folder loading for `prop_magnet.png`.
- Fixed character select portraits to use `assetUrl(...)` instead of hardcoded local paths.
- Removed the leftover global `ctx.restore()` debug/fix line.
- Re-generated and promoted larger, more readable pickup assets:
  - `prop_mineral.png`
  - `prop_health.png`
- Increased pickup readability in render:
  - minerals now draw at least 28px
  - health pickups now draw at least 36px
  - magnet pickups now draw at least 44px plus a visible cyan ring
- Fixed magnet pickup behavior:
  - magnets now update, render, get pulled to the player, and trigger `attractAllDrops()`
  - magnet drop chance tuned down to stay rare after play feedback
  - magnet pity added after 300 enemy kills without a magnet
- Added `MONSTARZ SURVIVORS 2.0` to the page title, rotate gate, and web manifest.
- Added a visible `2.0` badge directly beside the main title on the title screen.

Verification passed:

```powershell
node -e "const fs=require('fs'),vm=require('vm');const html=fs.readFileSync('index.html','utf8');const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]);for(const [i,s] of scripts.entries())new vm.Script(s,{filename:'index.html#script'+i});console.log('parsed',scripts.length,'inline scripts');"
python -m py_compile .\tools\aether_assets.py .\tools\supabase_assets.py
python .\tools\supabase_assets.py --dry-run
```

Browser verification:

- `MONSTARZ SURVIVORS 2.0` title appears.
- `Asset pack [Supabase CDN] 55/55 loaded`.
- Default character game start works.
- No browser console errors or warnings were observed during load/start.

Remaining after push:

- Full manual gameplay balance pass for Stages 1-4 and Endless.
- Manual unlocked-character playtest for Lurker (`72`) and Dragoon (`RANG`) because the in-app browser test scope cannot mutate `localStorage`.
- Optional next improvement: dedicated Stage 4 BGM instead of reusing Stage 3 BGM.

## Endless Level-Up Hotfix

Last updated: 2026-06-26 08:32 KST

Issue:

- After clearing the Stage 4 boss and entering Endless, level progression could feel stalled because XP depended almost entirely on mineral pickup while Endless enemy HP and screen pressure rose sharply.

Fix:

- Added a small Endless-only direct combat XP trickle on enemy kills.
- Removed the earlier delayed mineral auto-pull idea because magnet pickups should remain the dedicated full-screen collection tool.
- Removed the earlier Endless mineral XP bonus so drop value stays consistent with normal pickup balance.

Verification:

```powershell
node -e "const fs=require('fs'),vm=require('vm');const html=fs.readFileSync('index.html','utf8');const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]);for(const [i,s] of scripts.entries())new vm.Script(s,{filename:'index.html#script'+i});console.log('parsed',scripts.length,'inline scripts');"
```

- VM smoke test confirmed: Stage 4 boss death starts Endless and an Endless enemy kill increases XP without auto-latching distant minerals.

## Stage Boss XP Audit

Last updated: 2026-06-26 11:04 KST

Report:

- A tester reported that minerals did not appear to increase XP after the Stage 3 boss appeared.

Findings:

- VM phase tests confirmed minerals increase XP during Stage 1, 2, 3, and 4 boss phases.
- Stage 3 boss-phase enemy drops also increase XP.
- Invalid XP inputs are now ignored defensively so a malformed drop cannot poison the XP bar.
- `gainXP()` now syncs the HUD immediately after applying XP, so boss/level-up/phase transitions cannot leave the XP bar visually stale until the end of the update tick.

Verification:

- `index.html` parses successfully with Node `vm.Script`.
- Supabase asset dry-run reports `0` pending uploads.
- VM smoke test confirmed: Stage 3 boss phase mineral pickup changes both `G.xp` and `#xpfill` width.
