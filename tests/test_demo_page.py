def test_root_serves_demo_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "Newcomer Navigator" in resp.text


def test_demo_page_not_in_api_docs(client):
    assert "/" not in client.get("/openapi.json").json()["paths"]
