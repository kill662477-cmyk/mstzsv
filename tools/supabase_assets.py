import os
import sys
import json
import hashlib
import time
import requests
import argparse
from datetime import datetime

# Load .env.local
def load_env():
    env = {}
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env.local')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    return env

def get_hash(filepath):
    sha = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()

def ensure_bucket(url, key, bucket):
    print(f"Ensuring bucket '{bucket}' exists and is public...")
    headers = {"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": "application/json"}
    r = requests.get(f"{url}/storage/v1/bucket/{bucket}", headers=headers)
    if r.status_code == 200:
        print(f"Bucket {bucket} already exists.")
        return True
    if r.status_code == 404 or r.status_code == 400:
        # Create bucket
        r = requests.post(f"{url}/storage/v1/bucket", headers=headers, json={"id": bucket, "name": bucket, "public": True})
        if r.status_code == 200:
            print(f"Bucket {bucket} created successfully.")
            return True
        else:
            print(f"Failed to create bucket: {r.text}")
            return False
    print(f"Error checking bucket: {r.text}")
    return False

def get_public_url(url, bucket, path):
    return f"{url}/storage/v1/object/public/{bucket}/{path}"

def upload_file(url, key, bucket, path, filepath):
    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key,
        "Content-Type": "image/png",
        "Cache-Control": "max-age=31536000, immutable",
        "x-upsert": "true"
    }
    with open(filepath, 'rb') as f:
        r = requests.post(f"{url}/storage/v1/object/{bucket}/{path}", headers=headers, data=f)
    if r.status_code == 200:
        return True
    else:
        print(f"Failed to upload {filepath}: {r.text}")
        return False

def upload_json(url, key, bucket, path, data):
    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key,
        "Content-Type": "application/json",
        "Cache-Control": "max-age=60",
        "x-upsert": "true"
    }
    r = requests.post(f"{url}/storage/v1/object/{bucket}/{path}", headers=headers, json=data)
    return r.status_code == 200

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Do not actually upload')
    parser.add_argument('--force', action='store_true', help='Force reupload even if hash matches')
    args = parser.parse_args()

    env = load_env()
    supabase_url = env.get('NEXT_PUBLIC_SUPABASE_URL') or env.get('SUPABASE_URL')
    supabase_key = env.get('SUPABASE_SERVICE_ROLE_KEY') or env.get('SUPABASE_SECRET_KEY')
    bucket = env.get('SUPABASE_ASSET_BUCKET', 'calmsv-assets')
    prefix = env.get('SUPABASE_ASSET_PREFIX', 'assets')

    if not supabase_url or not supabase_key:
        print("Missing Supabase credentials in .env.local")
        sys.exit(1)

    if not args.dry_run:
        if not ensure_bucket(supabase_url, supabase_key, bucket):
            sys.exit(1)

    assets_dir = os.path.join(os.path.dirname(__file__), '..', 'monstarz-survivors-assets')
    manifest_file = os.path.join(os.path.dirname(__file__), '..', 'asset-manifest.json')

    old_manifest = {}
    if os.path.exists(manifest_file):
        with open(manifest_file, 'r', encoding='utf-8') as f:
            try:
                old_manifest = json.load(f)
            except:
                pass
    old_assets = old_manifest.get('assets', {})

    new_version = f"v{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    new_assets = {}

    files_to_upload = []
    total_bytes = 0

    print("Scanning local assets...")
    for f in os.listdir(assets_dir):
        if not f.endswith('.png'): continue
        filepath = os.path.join(assets_dir, f)
        b = os.path.getsize(filepath)
        h = get_hash(filepath)

        # Check if unchanged
        old_info = old_assets.get(f)
        if old_info and old_info.get('contentHash') == h and not args.force:
            new_assets[f] = old_info
            continue

        # Needs upload
        path = f"{prefix}/{new_version}/{f}"
        files_to_upload.append({
            'fileName': f,
            'path': path,
            'filepath': filepath,
            'bytes': b,
            'contentHash': h
        })
        total_bytes += b

    print(f"Found {len(files_to_upload)} files to upload (Total: {total_bytes / 1024 / 1024:.2f} MB)")

    if args.dry_run:
        print("DRY RUN: Skipping uploads.")
        return

    for item in files_to_upload:
        print(f"Uploading {item['fileName']}...")
        if upload_file(supabase_url, supabase_key, bucket, item['path'], item['filepath']):
            pub_url = get_public_url(supabase_url, bucket, item['path'])
            new_assets[item['fileName']] = {
                'fileName': item['fileName'],
                'path': item['path'],
                'publicUrl': pub_url,
                'bytes': item['bytes'],
                'contentHash': item['contentHash']
            }

    manifest = {
        'version': new_version,
        'bucket': bucket,
        'prefix': prefix,
        'generatedAt': datetime.utcnow().isoformat() + 'Z',
        'assets': new_assets
    }

    print("Saving local manifest...")
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print("Uploading manifest to Supabase...")
    upload_json(supabase_url, supabase_key, bucket, f"{prefix}/asset-manifest.json", manifest)

    print("Asset pipeline complete!")

if __name__ == '__main__':
    main()
