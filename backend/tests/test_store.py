from uuid import UUID

from app.schemas.profile import Profile
from app.services.store import InMemoryStore, UserTask

A = UUID("11111111-1111-4111-8111-111111111111")
B = UUID("22222222-2222-4222-8222-222222222222")


def test_in_memory_roundtrip():
    store = InMemoryStore()
    assert store.get_profile(A) == Profile()

    store.save_profile(A, Profile(in_us=True))
    assert store.get_profile(A).in_us is True

    store.save_user_task(A, UserTask(task_id="ssn", status="not_started", source="rule"))
    assert store.get_user_tasks(A)["ssn"].source == "rule"

    store.set_step(A, "ssn", "dso_letter", True)
    assert store.get_done_steps(A, "ssn") == {"dso_letter"}
    store.set_step(A, "ssn", "dso_letter", False)
    assert store.get_done_steps(A, "ssn") == set()

    store.append_message(A, "user", "hi", {})
    assert store.get_messages(A)[0]["content"] == "hi"

    assert store.get_profile(B) == Profile()
    assert store.get_user_tasks(B) == {}

    store.delete_user_task(A, "ssn")
    assert store.get_user_tasks(A) == {}
