"""
Test suite for Mergington High School API

Tests cover all main endpoints: GET /activities, POST /signup, and DELETE /participants.
Tests also validate error cases and email format validation.
"""

import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to original state before and after each test"""
    original_activities = copy.deepcopy(activities)
    yield
    # Restore activities after test
    activities.clear()
    activities.update(original_activities)


@pytest.fixture
def activity_client(client, reset_activities):
    """Combine client and activity reset for convenience"""
    return client


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, activity_client):
        """Test that GET /activities returns the list of all activities"""
        response = activity_client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify we get the expected activities
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Verify activity structure
        activity = data["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_with_valid_email(self, activity_client):
        """Test signing up a student with valid email format"""
        response = activity_client.post(
            "/activities/Chess Club/signup",
            params={"email": "student@example.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "student@example.com" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify participant was added
        activities_response = activity_client.get("/activities")
        chess_activity = activities_response.json()["Chess Club"]
        assert "student@example.com" in chess_activity["participants"]

    def test_signup_with_invalid_email_format(self, activity_client):
        """Test that signup rejects invalid email format (missing @)"""
        response = activity_client.post(
            "/activities/Chess Club/signup",
            params={"email": "invalidemailformat"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid email format" in data["detail"]

    def test_signup_with_missing_at_symbol(self, activity_client):
        """Test that signup rejects email without @ symbol"""
        response = activity_client.post(
            "/activities/Programming Class/signup",
            params={"email": "studentexample.com"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid email format" in data["detail"]

    def test_signup_for_nonexistent_activity(self, activity_client):
        """Test that signup returns 404 for non-existent activity"""
        response = activity_client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@example.com"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]

    def test_signup_multiple_students(self, activity_client):
        """Test signing up multiple students to same activity"""
        # Sign up first student
        response1 = activity_client.post(
            "/activities/Debate Team/signup",
            params={"email": "student1@example.com"}
        )
        assert response1.status_code == 200
        
        # Sign up second student
        response2 = activity_client.post(
            "/activities/Debate Team/signup",
            params={"email": "student2@example.com"}
        )
        assert response2.status_code == 200
        
        # Verify both are in participants
        activities_response = activity_client.get("/activities")
        debate_activity = activities_response.json()["Debate Team"]
        assert "student1@example.com" in debate_activity["participants"]
        assert "student2@example.com" in debate_activity["participants"]


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""

    def test_remove_existing_participant(self, activity_client):
        """Test removing an existing participant from an activity"""
        # First add a participant
        activity_client.post(
            "/activities/Tennis Club/signup",
            params={"email": "student@example.com"}
        )
        
        # Then remove them
        response = activity_client.delete(
            "/activities/Tennis Club/participants/student@example.com"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "student@example.com" in data["message"]
        assert "Tennis Club" in data["message"]
        
        # Verify participant was removed
        activities_response = activity_client.get("/activities")
        tennis_activity = activities_response.json()["Tennis Club"]
        assert "student@example.com" not in tennis_activity["participants"]

    def test_remove_nonexistent_participant(self, activity_client):
        """Test that deleting non-existent participant returns 404"""
        response = activity_client.delete(
            "/activities/Chess Club/participants/nonexistent@example.com"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Participant not found" in data["detail"]

    def test_remove_from_nonexistent_activity(self, activity_client):
        """Test that deleting from non-existent activity returns 404"""
        response = activity_client.delete(
            "/activities/Nonexistent Club/participants/student@example.com"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]

    def test_remove_original_participant(self, activity_client):
        """Test removing one of the original participants from an activity"""
        # Get initial participants for Chess Club
        activities_response = activity_client.get("/activities")
        original_participants = activities_response.json()["Chess Club"]["participants"]
        initial_count = len(original_participants)
        
        # Remove the first original participant
        first_participant = original_participants[0]
        response = activity_client.delete(
            f"/activities/Chess Club/participants/{first_participant}"
        )
        
        assert response.status_code == 200
        
        # Verify count decreased
        activities_response = activity_client.get("/activities")
        new_count = len(activities_response.json()["Chess Club"]["participants"])
        assert new_count == initial_count - 1


class TestRootRedirect:
    """Tests for root endpoint"""

    def test_root_redirect(self, activity_client):
        """Test that root endpoint redirects to static index.html"""
        response = activity_client.get("/", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"
