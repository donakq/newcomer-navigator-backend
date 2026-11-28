"""The AI assistant is on every page, including before sign-in; feedback still needs an account."""

MESSAGE = {"message": "What is OPT?", "current_page": "landing"}


def test_signed_out_student_can_ask(client):
    res = client.post("/api/assistant/messages", json=MESSAGE)
    assert res.status_code == 200
    assert res.json()["answer"]


def test_signed_in_student_can_ask(client, auth):
    assert client.post("/api/assistant/messages", json=MESSAGE, headers=auth).status_code == 200


def test_bad_token_is_still_rejected(client):
    res = client.post("/api/assistant/messages", json=MESSAGE, headers={"Authorization": "Bearer nope"})
    assert res.status_code == 401


def test_feedback_still_needs_login(client):
    assert client.post("/api/assistant/feedback", json={"rating": "UP"}).status_code == 401
