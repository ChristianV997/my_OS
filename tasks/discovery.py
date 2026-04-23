from core.bridge import Bridge
from core.celery_app import celery_app

bridge = Bridge()


@celery_app.task
def run_discovery():
    keywords = ["weight loss", "skincare", "productivity", "fitness", "biohacking"]
    return bridge.execute(keywords)


@celery_app.task
def run_intelligence_pipeline(keywords):
    return bridge.execute(keywords or [])
