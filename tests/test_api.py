"""
Comprehensive API tests for Mergington High School Activities API.
Uses AAA (Arrange-Act-Assert) pattern for test organization.
"""

import copy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src.app import app, activities as activities_data


@pytest.fixture(autouse=True)
def reset_activities():
    """Restore the in-memory activity state after each test."""
    original_state = copy.deepcopy(activities_data)
    yield
    activities_data.clear()
    activities_data.update(original_state)


@pytest.fixture
def client():
    """Provide a test client for API requests."""
    return TestClient(app)


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_redirects_to_static_index(self, client):
        # Arrange
        expected_redirect_url = "/static/index.html"

        # Act
        response = client.get("/", allow_redirects=False)

        # Assert
        assert response.status_code in {301, 307}
        assert expected_redirect_url in response.headers["location"]


class TestGetActivitiesEndpoint:
    """Tests for GET /activities endpoint."""

    def test_get_activities_returns_all_activities(self, client):
        # Arrange
        required_fields = {"description", "schedule", "max_participants", "participants"}

        # Act
        response = client.get("/activities")
        activities = response.json()

        # Assert
        assert response.status_code == 200
        assert isinstance(activities, dict)
        assert activities.keys() == activities_data.keys()
        for activity_data in activities.values():
            assert required_fields.issubset(activity_data.keys())

    def test_get_activities_includes_participants_list(self, client):
        # Arrange
        # Act
        response = client.get("/activities")
        activities = response.json()

        # Assert
        assert response.status_code == 200
        for activity_data in activities.values():
            assert isinstance(activity_data["participants"], list)

    def test_get_activities_has_valid_participant_counts(self, client):
        # Arrange
        # Act
        response = client.get("/activities")
        activities = response.json()

        # Assert
        for activity_data in activities.values():
            assert len(activity_data["participants"]) <= activity_data["max_participants"]


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint."""

    def test_signup_new_participant_success(self, client):
        # Arrange
        activity_name = "Chess Club"
        test_email = "newstudent@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{quote(activity_name)}/signup",
            params={"email": test_email},
        )

        # Assert
        assert response.status_code == 200
        assert test_email in response.json()["message"]

    def test_signup_participant_appears_in_activity(self, client):
        # Arrange
        activity_name = "Chess Club"
        test_email = "newstudent@mergington.edu"

        # Act
        client.post(
            f"/activities/{quote(activity_name)}/signup",
            params={"email": test_email},
        )
        response = client.get("/activities")
        participants = response.json()[activity_name]["participants"]

        # Assert
        assert test_email in participants

    def test_signup_duplicate_participant_fails(self, client):
        # Arrange
        activity_name = "Chess Club"
        existing_email = "michael@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{quote(activity_name)}/signup",
            params={"email": existing_email},
        )

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_nonexistent_activity_fails(self, client):
        # Arrange
        activity_name = "Nonexistent Club"
        test_email = "student@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{quote(activity_name)}/signup",
            params={"email": test_email},
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_decreases_available_spots(self, client):
        # Arrange
        activity_name = "Programming Class"
        test_email = "newstudent@mergington.edu"
        response_before = client.get("/activities")
        initial_spots = (
            response_before.json()[activity_name]["max_participants"]
            - len(response_before.json()[activity_name]["participants"])
        )

        # Act
        client.post(
            f"/activities/{quote(activity_name)}/signup",
            params={"email": test_email},
        )
        response_after = client.get("/activities")
        final_spots = (
            response_after.json()[activity_name]["max_participants"]
            - len(response_after.json()[activity_name]["participants"])
        )

        # Assert
        assert final_spots == initial_spots - 1

    def test_signup_with_url_encoded_email(self, client):
        # Arrange
        activity_name = "Art Studio"
        test_email = "test+alias@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{quote(activity_name)}/signup",
            params={"email": test_email},
        )

        # Assert
        assert response.status_code == 200
        assert test_email in response.json()["message"]


class TestUnregisterEndpoint:
    """Tests for POST /activities/{activity_name}/unregister endpoint."""

    def test_unregister_existing_participant_success(self, client):
        # Arrange
        activity_name = "Chess Club"
        participant_email = "michael@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{quote(activity_name)}/unregister",
            params={"email": participant_email},
        )

        # Assert
        assert response.status_code == 200
        assert participant_email in response.json()["message"]

    def test_unregister_participant_removed_from_activity(self, client):
        # Arrange
        activity_name = "Chess Club"
        participant_email = "michael@mergington.edu"

        # Act
        client.post(
            f"/activities/{quote(activity_name)}/unregister",
            params={"email": participant_email},
        )
        response = client.get("/activities")
        participants = response.json()[activity_name]["participants"]

        # Assert
        assert participant_email not in participants

    def test_unregister_nonexistent_participant_fails(self, client):
        # Arrange
        activity_name = "Chess Club"
        nonexistent_email = "nonexistent@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{quote(activity_name)}/unregister",
            params={"email": nonexistent_email},
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Participant not found in this activity"

    def test_unregister_nonexistent_activity_fails(self, client):
        # Arrange
        activity_name = "Nonexistent Club"
        test_email = "student@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{quote(activity_name)}/unregister",
            params={"email": test_email},
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_increases_available_spots(self, client):
        # Arrange
        activity_name = "Chess Club"
        participant_email = "michael@mergington.edu"
        response_before = client.get("/activities")
        initial_spots = (
            response_before.json()[activity_name]["max_participants"]
            - len(response_before.json()[activity_name]["participants"])
        )

        # Act
        client.post(
            f"/activities/{quote(activity_name)}/unregister",
            params={"email": participant_email},
        )
        response_after = client.get("/activities")
        final_spots = (
            response_after.json()[activity_name]["max_participants"]
            - len(response_after.json()[activity_name]["participants"])
        )

        # Assert
        assert final_spots == initial_spots + 1

    def test_unregister_then_signup_same_participant(self, client):
        # Arrange
        activity_name = "Chess Club"
        participant_email = "michael@mergington.edu"

        # Act
        client.post(
            f"/activities/{quote(activity_name)}/unregister",
            params={"email": participant_email},
        )
        response = client.post(
            f"/activities/{quote(activity_name)}/signup",
            params={"email": participant_email},
        )

        # Assert
        assert response.status_code == 200
        activities = client.get("/activities").json()
        assert participant_email in activities[activity_name]["participants"]
