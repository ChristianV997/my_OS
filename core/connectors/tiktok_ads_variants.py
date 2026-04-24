from core.connectors.tiktok_creatives import upload_creative


def launch_variants(campaign_id: str, assets: list[dict]) -> list[dict]:
    """Upload each asset as a creative and build ad payloads for a campaign."""
    ad_ids = []

    for asset in assets:
        video = upload_creative(asset["file_path"])

        ad_payload = {
            "campaign_id": campaign_id,
            "creative_name": asset["name"],
            "video_id": video.get("data", {}).get("video_id"),
        }

        ad_ids.append(ad_payload)

    return ad_ids
