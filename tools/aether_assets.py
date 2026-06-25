#!/usr/bin/env python3
"""
AetherAI asset pipeline for CALMSV.

This tool reads an API key from .env.local, submits AetherAI jobs, polls their
status, downloads review outputs into aether-output, and can promote selected
PNG files into monstarz-survivors-assets with automatic backups.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env.local"
MANIFEST_FILE = ROOT / "tools" / "aether_asset_prompts.json"
ASSET_DIR = ROOT / "monstarz-survivors-assets"
OUTPUT_DIR = ROOT / "aether-output"
BACKUP_DIR = ROOT / "monstarz-survivors-assets-backup"
DEFAULT_BASE_URL = "https://api.aetherforgeai.com"

IMAGE_MODELS = [
    "GPT Image 1.5",
    "Grok Imagine",
    "Grok Imagine Pro",
    "Nano Banana",
    "Nano Banana 2",
    "Nano Banana Pro",
]
RESOLUTIONS = ["1K", "2K", "4K"]
SPRITE_FRAMES = [25, 36, 49, 64, 81, 100, 121, 144, 169]
SPRITE_STYLES = ["pixel", "cartoon", "sd", "quater_view"]


class AetherError(RuntimeError):
    pass


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_api_key() -> str:
    env = load_dotenv(ENV_FILE)
    names = ("AETHERFORGE_API_KEY", "AETHER_API_KEY", "AETHERAI_API_KEY", "AETHERWAVE_API_KEY")
    for name in names:
        key = os.environ.get(name) or env.get(name)
        if key and key.strip():
            return key.strip()
    raise AetherError(f"Missing API key. Put AETHERFORGE_API_KEY=your_key in {ENV_FILE}.")


def mask_key(key: str) -> str:
    if len(key) <= 12:
        return "***"
    return f"{key[:8]}...{key[-4:]}"


def auth_headers(api_key: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key or get_api_key()}",
        "Accept": "application/json",
        "User-Agent": "CALMSV-aether-assets/1.0",
    }


def load_manifest(path: Path = MANIFEST_FILE) -> dict[str, Any]:
    if not path.exists():
        raise AetherError(f"Manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_items(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in manifest.get("assets", [])}


def request_json(method: str, path: str, *, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    try:
        resp = requests.request(method.upper(), url, headers=auth_headers(), timeout=60)
    except requests.RequestException as exc:
        raise AetherError(f"{method} {path} failed: {exc}") from exc
    if not resp.ok:
        detail = response_detail(resp)
        raise AetherError(f"{method} {path} failed: HTTP {resp.status_code} {detail}".strip())
    return resp.json() if resp.text else {}


def response_detail(resp: requests.Response) -> str:
    try:
        parsed = resp.json()
        return parsed.get("detail") or parsed.get("error") or parsed.get("message") or resp.text
    except Exception:
        return resp.text


def open_files(file_specs: list[tuple[str, Path]]) -> list[tuple[str, tuple[str, Any, str]]]:
    files: list[tuple[str, tuple[str, Any, str]]] = []
    for field, path in file_specs:
        real = path.resolve()
        if not real.exists():
            raise AetherError(f"File not found for {field}: {real}")
        content_type = mimetypes.guess_type(real.name)[0] or "application/octet-stream"
        files.append((field, (real.name, real.open("rb"), content_type)))
    return files


def close_files(files: list[tuple[str, tuple[str, Any, str]]] | None) -> None:
    if not files:
        return
    for _, file_tuple in files:
        try:
            file_tuple[1].close()
        except Exception:
            pass


def post_form_job(
    path: str,
    data: dict[str, Any],
    *,
    file_specs: list[tuple[str, Path]] | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    url = base_url.rstrip("/") + path
    clean_data = {k: str(v) for k, v in data.items() if v is not None}
    files = open_files(file_specs or [])
    try:
        resp = requests.post(url, headers=auth_headers(), data=clean_data, files=files or None, timeout=90)
    finally:
        close_files(files)
    if not resp.ok:
        detail = response_detail(resp)
        raise AetherError(f"POST {path} failed: HTTP {resp.status_code} {detail}".strip())
    payload = resp.json() if resp.text else {}
    job_id = payload.get("job_id")
    if not job_id:
        raise AetherError(f"POST {path} did not return job_id: {json.dumps(payload)[:400]}")
    return job_id


def poll_job(job_id: str, *, timeout_s: int = 180, interval_s: float = 2.0) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(interval_s)
        status = request_json("GET", f"/public/v1/job/{job_id}")
        state = str(status.get("status") or "").strip()
        print(f"  {job_id}: {state or 'Pending'}", flush=True)
        if state == "Succeed":
            return status
        if state == "Failed":
            msg = status.get("error_message") or status.get("detail") or "Unknown error"
            raise AetherError(f"Job failed ({job_id}): {msg}")
    raise AetherError(f"Job timed out after {timeout_s}s (job_id={job_id}).")


def image_urls(status: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in status.get("image_urls") or []:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict):
            url = item.get("url") or item.get("imageUrl") or item.get("contentUrl")
            if url:
                urls.append(url)
    return urls


def download_file(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, headers={"User-Agent": "CALMSV-aether-assets/1.0"}, timeout=120)
    resp.raise_for_status()
    if dest.suffix == "":
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
        dest = dest.with_suffix(mimetypes.guess_extension(content_type) or ".png")
    dest.write_bytes(resp.content)
    return dest


def run_dir(name: str, base: Path = OUTPUT_DIR) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in name).strip("-")
    return base / f"{stamp}-{safe or 'aether-job'}"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def dry_run_report(endpoint: str, data: dict[str, Any], file_specs: list[tuple[str, Path]], output: Path) -> None:
    print("Dry run only; no credits spent.")
    print(f"Endpoint: {endpoint}")
    print(f"Output folder would be: {output}")
    print("Form fields:")
    for key, value in data.items():
        if value is not None:
            text = str(value)
            if len(text) > 500:
                text = text[:500] + "..."
            print(f"  {key}: {text}")
    if file_specs:
        print("Files:")
        for field, path in file_specs:
            print(f"  {field}: {path}")


def submit_and_download(
    *,
    endpoint: str,
    data: dict[str, Any],
    file_specs: list[tuple[str, Path]] | None,
    output: Path,
    timeout: int,
    dry_run: bool = False,
    prefix: str = "raw",
) -> tuple[Path, list[Path], dict[str, Any] | None]:
    file_specs = file_specs or []
    if dry_run:
        dry_run_report(endpoint, data, file_specs, output)
        return output, [], None

    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "request.json", {"endpoint": endpoint, "data": data, "files": [(f, str(p)) for f, p in file_specs]})
    print(f"Submitting {endpoint} -> {output}")
    job_id = post_form_job(endpoint, data, file_specs=file_specs)
    status = poll_job(job_id, timeout_s=timeout)
    urls = image_urls(status)
    write_json(output / "job-result.json", {"job_id": job_id, "status": status, "imageUrls": urls})
    if not urls:
        raise AetherError(f"No image URLs returned for job {job_id}: {json.dumps(status)[:500]}")
    downloaded: list[Path] = []
    for i, url in enumerate(urls, 1):
        out = download_file(url, output / f"{prefix}-{i:02d}")
        downloaded.append(out)
        print(f"  downloaded {i}: {out}")
    return output, downloaded, status


def target_size_for(file_name: str) -> tuple[int, int] | None:
    if Image is None:
        return None
    path = ASSET_DIR / file_name
    if not path.exists():
        return None
    with Image.open(path) as img:
        return img.size


def fit_image(src: Path, dest: Path, size: tuple[int, int], fit: str) -> Path:
    if Image is None:
        raise AetherError("Pillow is required for resizing but is not importable.")
    fit = fit.lower()
    with Image.open(src) as original:
        img = original.convert("RGBA")
        target_w, target_h = size
        if fit == "stretch":
            out = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        elif fit == "cover":
            scale = max(target_w / img.width, target_h / img.height)
            resized = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
            left = max(0, (resized.width - target_w) // 2)
            top = max(0, (resized.height - target_h) // 2)
            out = resized.crop((left, top, left + target_w, top + target_h))
        else:
            scale = min(target_w / img.width, target_h / img.height)
            resized = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
            out = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            out.alpha_composite(resized, ((target_w - resized.width) // 2, (target_h - resized.height) // 2))
        dest.parent.mkdir(parents=True, exist_ok=True)
        out.save(dest)
    return dest


def remove_chroma_key(src: Path, dest: Path, *, key: tuple[int, int, int] = (0, 255, 0), threshold: int = 100) -> Path:
    if Image is None:
        raise AetherError("Pillow is required for chroma-key removal but is not importable.")
    with Image.open(src) as original:
        img = original.convert("RGBA")
        pixels = img.load()
        kr, kg, kb = key
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                dist = abs(r - kr) + abs(g - kg) + abs(b - kb)
                green_dominant = g > 90 and g > r + 24 and g > b + 24
                if dist < threshold or green_dominant:
                    pixels[x, y] = (r, g, b, 0)
                elif g > r + 12 and g > b + 12:
                    neutral = max(r, b)
                    pixels[x, y] = (r, min(g, neutral), b, a)
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest)
    return dest


def build_prompt(asset: dict[str, Any], manifest: dict[str, Any]) -> str:
    parts = [
        manifest.get("globalStyle", "").strip(),
        asset.get("prompt", "").strip(),
    ]
    if asset.get("transparent", False):
        parts.append(
            "Place the subject on a perfectly flat solid #00ff00 chroma-key background for local background removal. "
            "The background must be one uniform green color with no texture, shadow, floor, gradient, reflection, or lighting variation. "
            "Do not use green inside the subject."
        )
    else:
        parts.append("No UI, no text, no watermark.")
    constraints = manifest.get("globalConstraints", "").strip()
    if constraints:
        parts.append(constraints)
    return "\n".join(p for p in parts if p)


def ref_image_files(file_name: str, no_ref: bool) -> list[tuple[str, Path]]:
    if no_ref:
        return []
    path = ASSET_DIR / file_name
    if path.exists():
        return [("ref_images", path)]
    return []


def generate_asset(args: argparse.Namespace, asset: dict[str, Any] | None = None, manifest: dict[str, Any] | None = None) -> Path:
    manifest = manifest or {"globalStyle": "", "globalConstraints": ""}
    asset = asset or {
        "id": args.asset or "custom",
        "file": args.file or f"{args.asset or 'custom'}.png",
        "prompt": args.prompt,
        "transparent": args.chroma_key,
        "fit": args.fit,
    }
    if not asset.get("prompt") and not args.prompt:
        raise AetherError("Missing prompt. Provide --prompt or use an asset from the manifest.")

    asset_id = asset["id"]
    file_name = asset.get("file") or f"{asset_id}.png"
    prompt = args.prompt or build_prompt(asset, manifest)
    model = args.model or asset.get("model") or manifest.get("defaultModel") or "GPT Image 1.5"
    chroma_key = args.chroma_key or (asset.get("transparent", False) and not args.no_chroma_key)
    fit = args.fit or asset.get("fit") or "contain"
    output = Path(args.output_dir) if args.output_dir else run_dir(asset_id)
    file_specs = ref_image_files(file_name, args.no_ref)

    if not args.dry_run:
        output.mkdir(parents=True, exist_ok=True)
        (output / "prompt.txt").write_text(prompt, encoding="utf-8")

    _, downloads, _ = submit_and_download(
        endpoint="/public/v1/generate/image",
        data={"prompt": prompt, "ai_model": model},
        file_specs=file_specs,
        output=output,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return output

    for i, raw_path in enumerate(downloads, 1):
        final_source = raw_path
        if chroma_key:
            keyed = output / f"cutout-{i:02d}.png"
            final_source = remove_chroma_key(raw_path, keyed)
            print(f"  chroma-key cutout {i}: {final_source}")
        target_size = None if args.no_resize else target_size_for(file_name)
        if target_size:
            final_path = output / f"final-{i:02d}.png"
            fit_image(final_source, final_path, target_size, fit)
            print(f"  resized final {i}: {final_path} ({target_size[0]}x{target_size[1]}, {fit})")
    return output


def selected_assets(manifest: dict[str, Any], only: list[str] | None) -> list[dict[str, Any]]:
    items = manifest_items(manifest)
    if not only:
        return manifest.get("assets", [])
    selected = []
    for asset_id in only:
        if asset_id not in items:
            raise AetherError(f"Unknown asset id in manifest: {asset_id}")
        selected.append(items[asset_id])
    return selected


def find_manifest_item_by_file(file_name: str) -> dict[str, Any] | None:
    if not MANIFEST_FILE.exists():
        return None
    manifest = load_manifest()
    for item in manifest.get("assets", []):
        if item.get("file") == file_name or item.get("id") == file_name:
            return item
    return None


def cmd_auth_check(args: argparse.Namespace) -> int:
    key = get_api_key()
    print(f"Using key {mask_key(key)}")
    dummy_job = "550e8400-e29b-41d4-a716-446655440000"
    url = DEFAULT_BASE_URL + f"/public/v1/job/{dummy_job}"
    resp = requests.get(url, headers=auth_headers(key), timeout=30)
    if resp.status_code == 401:
        print("Auth failed: API returned 401 Invalid API key.")
        return 1
    if resp.status_code in (404, 422):
        print("Auth OK: API accepted the key. Dummy job was not found, as expected.")
        return 0
    if resp.ok:
        print("Auth OK:")
        print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
        return 0
    print(f"Unexpected response: HTTP {resp.status_code} {resp.text}")
    return 1


def cmd_models(args: argparse.Namespace) -> int:
    print("Image models:")
    for value in IMAGE_MODELS:
        print(f"  {value}")
    print("Resolutions:")
    print("  " + ", ".join(RESOLUTIONS))
    print("Sprite frames:")
    print("  " + ", ".join(str(x) for x in SPRITE_FRAMES))
    print("Sprite styles:")
    print("  " + ", ".join(SPRITE_STYLES))
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    manifest = load_manifest() if MANIFEST_FILE.exists() else {"assets": []}
    asset = None
    if args.asset:
        asset = manifest_items(manifest).get(args.asset)
        if asset is None and not args.prompt:
            raise AetherError(f"Unknown asset id: {args.asset}. Use --prompt for a custom asset.")
    output = generate_asset(args, asset=asset, manifest=manifest)
    print(f"Done. Review folder: {output}")
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    selected = selected_assets(manifest, args.only)
    if args.limit:
        selected = selected[: args.limit]
    print(f"Selected {len(selected)} asset(s).")
    for item in selected:
        print(f"  {item['id']} -> {item.get('file')}")
    if args.dry_run:
        print("Batch dry run only; no credits spent.")
        for item in selected:
            prompt = build_prompt(item, manifest)
            print(f"\n[{item['id']}]\n{prompt[:900]}")
        return 0
    if not args.yes:
        raise AetherError("Batch generation spends credits. Re-run with --yes when ready.")
    for item in selected:
        generate_asset(args, asset=item, manifest=manifest)
    return 0


def cmd_effect(args: argparse.Namespace) -> int:
    output = Path(args.output_dir) if args.output_dir else run_dir(args.name or "effect")
    files = [("image", Path(args.image))] if args.image else []
    submit_and_download(
        endpoint="/public/v1/generate/effect",
        data={"description": args.description, "resolution": args.resolution},
        file_specs=files,
        output=output,
        timeout=args.timeout,
        dry_run=args.dry_run,
        prefix="effect",
    )
    print(f"Done. Review folder: {output}")
    return 0


def cmd_upscale(args: argparse.Namespace) -> int:
    src = Path(args.image)
    output = Path(args.output_dir) if args.output_dir else run_dir(f"upscale-{src.stem}")
    submit_and_download(
        endpoint="/public/v1/image-tune/upscale",
        data={"scale": args.scale},
        file_specs=[("image", src)],
        output=output,
        timeout=args.timeout,
        dry_run=args.dry_run,
        prefix="upscaled",
    )
    print(f"Done. Review folder: {output}")
    return 0


def cmd_inpaint(args: argparse.Namespace) -> int:
    src = Path(args.image)
    output = Path(args.output_dir) if args.output_dir else run_dir(f"inpaint-{src.stem}")
    submit_and_download(
        endpoint="/public/v1/image-tune/inpaint",
        data={"prompt": args.prompt},
        file_specs=[("image", src)],
        output=output,
        timeout=args.timeout,
        dry_run=args.dry_run,
        prefix="inpaint",
    )
    print(f"Done. Review folder: {output}")
    return 0


def cmd_split_layer(args: argparse.Namespace) -> int:
    src = Path(args.image)
    output = Path(args.output_dir) if args.output_dir else run_dir(f"split-{src.stem}-{args.keyword}")
    submit_and_download(
        endpoint="/public/v1/image-tune/split-layer",
        data={"keyword": args.keyword},
        file_specs=[("image", src)],
        output=output,
        timeout=args.timeout,
        dry_run=args.dry_run,
        prefix="layer",
    )
    print(f"Done. Review folder: {output}")
    return 0


def cmd_make_sprite(args: argparse.Namespace) -> int:
    src = Path(args.image)
    output = Path(args.output_dir) if args.output_dir else run_dir(f"sprite-{src.stem}")
    submit_and_download(
        endpoint="/public/v1/sprite/make-sprite",
        data={"text": args.text, "frame": args.frame, "is_pixel": str(args.is_pixel).lower()},
        file_specs=[("image", src)],
        output=output,
        timeout=args.timeout,
        dry_run=args.dry_run,
        prefix="sprite",
    )
    print(f"Done. Review folder: {output}")
    return 0


def cmd_reskin_sprite(args: argparse.Namespace) -> int:
    src = Path(args.image)
    output = Path(args.output_dir) if args.output_dir else run_dir(f"reskin-{src.stem}")
    submit_and_download(
        endpoint="/public/v1/sprite/reskin",
        data={
            "sprite_subject": args.sprite_subject,
            "change_description": args.change_description,
            "final_result_description": args.final_result_description,
            "resolution": args.resolution,
            "style": args.style,
        },
        file_specs=[("image", src)],
        output=output,
        timeout=args.timeout,
        dry_run=args.dry_run,
        prefix="reskin",
    )
    print(f"Done. Review folder: {output}")
    return 0


def load_rows_arg(value: str) -> str:
    path = Path(value)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    candidates = [value, value.replace('\\"', '"')]
    for candidate in candidates:
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue
    lenient = parse_lenient_rows(value)
    if lenient is not None:
        return lenient
    raise AetherError("--rows must be a valid JSON string or a path to a JSON file.")


def parse_lenient_rows(value: str) -> str | None:
    text = value.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return None
    inner = text[1:-1].strip()
    if not inner:
        return None
    raw_objects = inner.split("},{")
    rows: list[dict[str, Any]] = []
    for raw in raw_objects:
        obj_text = raw.strip().strip("{}")
        row: dict[str, Any] = {}
        for part in obj_text.split(","):
            if ":" not in part:
                return None
            key, val = part.split(":", 1)
            key = key.strip().strip('"').strip("'")
            val = val.strip().strip('"').strip("'")
            if key == "row":
                try:
                    row[key] = int(val)
                except ValueError:
                    return None
            else:
                row[key] = val
        if not {"row", "title", "description"}.issubset(row):
            return None
        rows.append(row)
    return json.dumps(rows, ensure_ascii=False)


def cmd_character_overlay(args: argparse.Namespace) -> int:
    src = Path(args.sprite_sheet)
    output = Path(args.output_dir) if args.output_dir else run_dir(f"overlay-{src.stem}")
    rows = load_rows_arg(args.rows)
    file_specs: list[tuple[str, Path]] = [("sprite_sheet", src)]
    file_specs.extend(("character_images", Path(path)) for path in args.character_images)
    submit_and_download(
        endpoint="/public/v1/sprite/character-overlay",
        data={"rows": rows, "resolution": args.resolution, "style": args.style},
        file_specs=file_specs,
        output=output,
        timeout=args.timeout,
        dry_run=args.dry_run,
        prefix="overlay",
    )
    print(f"Done. Review folder: {output}")
    return 0


def cmd_job(args: argparse.Namespace) -> int:
    output = Path(args.output_dir) if args.output_dir else run_dir(f"job-{args.job_id}")
    if args.dry_run:
        print("Dry run only; no credits spent.")
        print(f"Would poll job: {args.job_id}")
        print(f"Output folder would be: {output}")
        return 0
    output.mkdir(parents=True, exist_ok=True)
    status = poll_job(args.job_id, timeout_s=args.timeout)
    urls = image_urls(status)
    write_json(output / "job-result.json", {"job_id": args.job_id, "status": status, "imageUrls": urls})
    for i, url in enumerate(urls, 1):
        out = download_file(url, output / f"job-{i:02d}")
        print(f"  downloaded {i}: {out}")
    print(f"Done. Review folder: {output}")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    src = Path(args.source).resolve()
    if not src.exists():
        raise AetherError(f"Source image not found: {src}")
    file_name = args.file
    if args.asset and not file_name:
        item = find_manifest_item_by_file(args.asset) or (manifest_items(load_manifest()).get(args.asset) if MANIFEST_FILE.exists() else None)
        file_name = item.get("file") if item else args.asset
    if not file_name:
        raise AetherError("Provide --asset <manifest-id> or --file <asset.png>.")
    if not file_name.endswith(".png"):
        file_name += ".png"

    target = ASSET_DIR / file_name
    if not target.exists() and not args.allow_new:
        raise AetherError(f"Target does not exist: {target}. Use --allow-new to create it.")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = BACKUP_DIR / stamp / file_name
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
        print(f"Backup: {backup}")

    final_src = src
    item = find_manifest_item_by_file(file_name)
    fit = args.fit or (item or {}).get("fit") or "contain"
    size = None if args.no_resize else target_size_for(file_name)
    if size:
        temp = src.parent / f"promote-resized-{file_name}"
        final_src = fit_image(src, temp, size, fit)
        print(f"Resized for target: {size[0]}x{size[1]} ({fit})")
    shutil.copy2(final_src, target)
    print(f"Promoted: {target}")
    return 0


def add_common_job_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output-dir")
    parser.add_argument("--dry-run", action="store_true", help="Print request only; do not call AetherAI.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate, tune, and promote CALMSV assets through AetherAI.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("auth-check", help="Validate the API key without spending credits.")
    p.set_defaults(func=cmd_auth_check)

    p = sub.add_parser("balance", help="Alias for auth-check; AetherAI docs do not expose a balance endpoint.")
    p.set_defaults(func=cmd_auth_check)

    p = sub.add_parser("models", help="List documented AetherAI option values.")
    p.set_defaults(func=cmd_models)

    def add_generation_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--asset", help="Manifest asset id, e.g. enemy_walker.")
        p.add_argument("--file", help="Target asset filename for custom prompts.")
        p.add_argument("--prompt", help="Override prompt.")
        p.add_argument("--model", default=None, choices=IMAGE_MODELS, help="AetherAI ai_model value.")
        p.add_argument("--no-ref", action="store_true", help="Do not upload the current asset as a reference image.")
        p.add_argument("--chroma-key", action="store_true", help="Run local #00ff00 chroma-key removal after generation.")
        p.add_argument("--no-chroma-key", action="store_true", help="Skip manifest chroma-key removal.")
        p.add_argument("--no-resize", action="store_true", help="Do not resize generated output to current asset dimensions.")
        p.add_argument("--fit", choices=["contain", "cover", "stretch"], default=None)
        add_common_job_args(p)

    p = sub.add_parser("generate", help="Generate one image asset or custom prompt.")
    add_generation_args(p)
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("batch", help="Generate image assets from the manifest.")
    add_generation_args(p)
    p.add_argument("--only", nargs="+", help="Asset ids to generate.")
    p.add_argument("--limit", type=int)
    p.add_argument("--yes", action="store_true", help="Confirm credit spend.")
    p.set_defaults(func=cmd_batch)

    p = sub.add_parser("effect", help="Generate an effect asset.")
    p.add_argument("--description", required=True)
    p.add_argument("--resolution", choices=RESOLUTIONS, default="1K")
    p.add_argument("--image", help="Optional reference image.")
    p.add_argument("--name", help="Review folder suffix.")
    add_common_job_args(p)
    p.set_defaults(func=cmd_effect)

    p = sub.add_parser("upscale", help="Upscale an existing image.")
    p.add_argument("image")
    p.add_argument("--scale", choices=RESOLUTIONS, default="2K")
    add_common_job_args(p)
    p.set_defaults(func=cmd_upscale)

    p = sub.add_parser("inpaint", help="Modify an existing image with a prompt.")
    p.add_argument("image")
    p.add_argument("--prompt", required=True)
    add_common_job_args(p)
    p.set_defaults(func=cmd_inpaint)

    p = sub.add_parser("split-layer", help="Extract a layer from an image by keyword.")
    p.add_argument("image")
    p.add_argument("--keyword", required=True)
    add_common_job_args(p)
    p.set_defaults(func=cmd_split_layer)

    p = sub.add_parser("make-sprite", help="Create a sprite animation sheet from an image.")
    p.add_argument("image")
    p.add_argument("--text", required=True)
    p.add_argument("--frame", type=int, choices=SPRITE_FRAMES, default=36)
    p.add_argument("--is-pixel", action="store_true")
    add_common_job_args(p)
    p.set_defaults(func=cmd_make_sprite)

    p = sub.add_parser("reskin-sprite", help="Reskin an existing sprite image.")
    p.add_argument("image")
    p.add_argument("--sprite-subject", required=True)
    p.add_argument("--change-description", required=True)
    p.add_argument("--final-result-description", required=True)
    p.add_argument("--resolution", choices=RESOLUTIONS, default="2K")
    p.add_argument("--style", choices=SPRITE_STYLES)
    add_common_job_args(p)
    p.set_defaults(func=cmd_reskin_sprite)

    p = sub.add_parser("character-overlay", help="Overlay character images onto a sprite sheet.")
    p.add_argument("--sprite-sheet", required=True)
    p.add_argument("--character-images", nargs="+", required=True)
    p.add_argument("--rows", required=True, help="JSON string or path to JSON file.")
    p.add_argument("--resolution", choices=RESOLUTIONS, default="2K")
    p.add_argument("--style")
    add_common_job_args(p)
    p.set_defaults(func=cmd_character_overlay)

    p = sub.add_parser("job", help="Poll and download an existing AetherAI job.")
    p.add_argument("job_id")
    add_common_job_args(p)
    p.set_defaults(func=cmd_job)

    p = sub.add_parser("promote", help="Copy a selected generated PNG into monstarz-survivors-assets.")
    p.add_argument("source", help="Generated PNG path, e.g. aether-output/.../final-01.png")
    p.add_argument("--asset", help="Manifest id or filename.")
    p.add_argument("--file", help="Exact target filename.")
    p.add_argument("--fit", choices=["contain", "cover", "stretch"])
    p.add_argument("--no-resize", action="store_true")
    p.add_argument("--allow-new", action="store_true")
    p.set_defaults(func=cmd_promote)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except AetherError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
