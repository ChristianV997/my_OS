def prepare_assets(variants: list[dict]) -> list[dict]:
    """Convert script variants into asset descriptors (video file placeholders)."""
    assets = []
    for i, v in enumerate(variants):
        assets.append(
            {
                "name": f"creative_{i}",
                "script": v["script"],
                "file_path": f"/tmp/creative_{i}.mp4",
            }
        )
    return assets
