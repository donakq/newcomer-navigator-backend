def test_root_redirects_to_api_docs(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/docs"


def test_root_not_in_api_docs(client):
    assert "/" not in client.get("/openapi.json").json()["paths"]
