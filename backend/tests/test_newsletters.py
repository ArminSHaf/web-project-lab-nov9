from tests.conftest import auth_headers


def create_user(client, admin, email, name):
    response = client.post(
        "/api/admin/users", headers=admin,
        json={"email": email, "full_name": name, "password": "studentpass123"},
    )
    assert response.status_code == 201, response.text
    return response.json(), auth_headers(client, email, "studentpass123")


def test_professor_student_newsletter_and_replies(client, admin, user):
    me = client.get("/api/auth/me", headers=user).json()
    created = client.post("/api/newsletters", headers=admin, json={
        "subject": "Exam preparation",
        "body": "Please review chapters 4 and 5.",
        "recipient_user_id": me["id"],
    })
    assert created.status_code == 201, created.text
    thread = created.json()
    assert thread["recipient"]["email"] == "jane@test.io"
    assert thread["messages"][0]["body"] == "Please review chapters 4 and 5."

    listed = client.get("/api/newsletters", headers=user)
    assert [item["id"] for item in listed.json()] == [thread["id"]]
    reply = client.post(
        f"/api/newsletters/{thread['id']}/messages", headers=user,
        json={"body": "I have finished both chapters."},
    )
    assert reply.status_code == 201
    assert [message["author"]["email"] for message in reply.json()["messages"]] == [
        "admin@test.io", "jane@test.io"
    ]


def test_group_newsletter_is_only_visible_to_members(client, admin, user):
    bob, bob_headers = create_user(client, admin, "bob@test.io", "Bob")
    jane_id = client.get("/api/auth/me", headers=user).json()["id"]
    group = client.post("/api/admin/groups", headers=admin, json={
        "name": "Group A", "member_ids": [jane_id]
    }).json()
    created = client.post("/api/newsletters", headers=admin, json={
        "subject": "Room change", "body": "Tomorrow we meet in room 204.", "group_id": group["id"]
    })
    assert created.status_code == 201
    thread_id = created.json()["id"]

    assert client.get(f"/api/newsletters/{thread_id}", headers=user).status_code == 200
    assert client.get(f"/api/newsletters/{thread_id}", headers=bob_headers).status_code == 404
    assert client.post(
        f"/api/newsletters/{thread_id}/messages", headers=bob_headers, json={"body": "Not allowed"}
    ).status_code == 404

    reply = client.post(
        f"/api/newsletters/{thread_id}/messages", headers=user, json={"body": "Thank you!"}
    )
    assert reply.status_code == 201 and len(reply.json()["messages"]) == 2


def test_student_can_contact_professor_but_not_another_student(client, admin, user):
    bob, _ = create_user(client, admin, "bob@test.io", "Bob")
    recipients = client.get("/api/newsletters/recipients", headers=user).json()
    professor_id = recipients["users"][0]["id"]
    assert recipients["users"][0]["email"] == "admin@test.io"
    assert client.post("/api/newsletters", headers=user, json={
        "subject": "Question", "body": "Could you clarify the assignment?",
        "recipient_user_id": professor_id,
    }).status_code == 201
    assert client.post("/api/newsletters", headers=user, json={
        "subject": "Wrong", "body": "Student to student is not a newsletter channel.",
        "recipient_user_id": bob["id"],
    }).status_code == 403
