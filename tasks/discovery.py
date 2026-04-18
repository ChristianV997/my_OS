from core.bridge import Bridge
from core.celery_app import celery_app

bridge = Bridge()


@celery_app.task
def run_discovery():
    keywords = ["weight loss", "skincare", "productivity", "fitness", "biohacking"]
    return bridge.execute(keywords)
