import os

UGC_LIBRARY_PATH = "./ugc_clips"


def load_ugc_clips() -> list[str]:
    """Return a list of .mp4 file paths from the UGC clip library directory."""
    if not os.path.isdir(UGC_LIBRARY_PATH):
        return []

    clips = []
    for f in os.listdir(UGC_LIBRARY_PATH):
        if f.endswith(".mp4"):
            clips.append(os.path.join(UGC_LIBRARY_PATH, f))

    return clips
