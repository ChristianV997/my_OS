import pytest
from core.pods import Pod
from agents.execution.product_agent import ProductAgent
from agents.execution.creative_agent import CreativeAgent
from agents.execution.ads_agent import AdsAgent
from agents.execution.funnel_agent import FunnelAgent


# --- ProductAgent ---

def test_product_agent_select_returns_products():
    agent = ProductAgent()
    signals = [
        {"product": "widget", "score": 0.8, "source": "mock", "market": "US", "platform": "meta"},
    ]
    products = agent.select(signals)
    assert len(products) == 1
    assert products[0]["name"] == "widget"
    assert products[0]["score"] == 0.8


def test_product_agent_select_defaults():
    agent = ProductAgent()
    products = agent.select([{}])
    assert products[0]["name"] == "unknown"
    assert products[0]["market"] == "global"
    assert products[0]["platform"] == "meta"


def test_product_agent_validate_valid():
    agent = ProductAgent()
    assert agent.validate({"name": "widget", "score": 0.5}) is True


def test_product_agent_validate_no_name():
    agent = ProductAgent()
    assert agent.validate({"name": "", "score": 0.5}) is False


def test_product_agent_validate_zero_score():
    agent = ProductAgent()
    assert agent.validate({"name": "widget", "score": 0.0}) is False


# --- CreativeAgent ---

def test_creative_agent_generate():
    pod = Pod("gadget", "US", "meta", budget=100.0)
    agent = CreativeAgent()
    creative = agent.generate(pod)
    assert creative["pod_id"] == pod.id
    assert "gadget" in creative["headline"]
    assert creative["cta"] == "Shop Now"


def test_creative_agent_batch_generate():
    pod = Pod("gadget", "US", "meta")
    agent = CreativeAgent()
    result = agent.batch_generate([pod], count=3)
    assert pod.id in result
    assert len(result[pod.id]) == 3


# --- AdsAgent ---

def test_ads_agent_launch():
    pod = Pod("widget", "US", "meta", budget=200.0)
    agent = AdsAgent()
    result = agent.launch(pod)
    assert result["pod_id"] == pod.id
    assert result["status"] == "launched"
    assert result["budget"] == 200.0


def test_ads_agent_pause():
    agent = AdsAgent()
    result = agent.pause("pod-123")
    assert result == {"pod_id": "pod-123", "status": "paused"}


def test_ads_agent_resume():
    agent = AdsAgent()
    result = agent.resume("pod-123")
    assert result == {"pod_id": "pod-123", "status": "resumed"}


# --- FunnelAgent ---

def test_funnel_agent_build():
    pod = Pod("sneaker", "US", "tiktok")
    agent = FunnelAgent()
    page = agent.build(pod)
    assert page["pod_id"] == pod.id
    assert page["url"] == f"/funnel/{pod.id}"
    assert "sneaker" in page["product"]
    assert page["platform"] == "tiktok"
