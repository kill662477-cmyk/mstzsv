# Supabase Asset Pipeline for CALMSV

This document describes the Supabase asset pipeline used to serve game assets via Supabase CDN, reducing local storage load and providing a production-ready asset delivery system.

## 1. Setup

You must configure the `.env.local` file with your Supabase credentials:

```env
NEXT_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<your-publishable-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
SUPABASE_SECRET_KEY=<your-secret-key>
SUPABASE_ASSET_BUCKET=calmsv-assets
SUPABASE_ASSET_PREFIX=assets
```

**SECURITY WARNING**: Never expose `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_SECRET_KEY` in the client code (`index.html`). The frontend should only ever receive the public URLs via the generated manifest.

## 2. Generating the Manifest and Uploading

We use a versioned path strategy. Instead of overwriting files and risking CDN cache invalidation issues, each batch of uploads goes into a new timestamped folder. We avoid redundant uploads by checking content hashes.

To run the uploader:

```bash
# Dry run to see what will be uploaded
python tools/supabase_assets.py --dry-run

# Actual upload
python tools/supabase_assets.py
```

This script will:
1. Ensure the `calmsv-assets` bucket exists and is public.
2. Scan the local `monstarz-survivors-assets/` directory.
3. Compute hashes and upload new/modified `.png` files to `assets/vYYYYMMDD-HHMMSS/`.
4. Generate a local `asset-manifest.json` and upload it to the root of the bucket (`assets/asset-manifest.json`).

## 3. Client Integration (`index.html`)

The game now uses `ASSET_MODE` to determine where to load assets from.

- **`remote` mode**: Fetches the `asset-manifest.json` from Supabase. All asset loads (`_mkSprite`) use the `publicUrl` defined in the manifest.
- **`local` mode**: Fallback mechanism. Loads assets directly from the local `monstarz-survivors-assets/` folder.

If the remote manifest fetch fails or an asset is missing, the game falls back to local loading seamlessly to ensure continuous gameplay.

## 4. Performance Checklist
- [x] Versioned immutable assets for maximum caching
- [x] Content-hash checks to prevent duplicate uploads
- [x] Manifest-driven asset loading to reduce directory listing overhead
- [x] Local fallback logic on network failure
