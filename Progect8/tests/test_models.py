import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.models import Tournament, Team


def test_tournament_schema_removed_fields():
    # after the recent refactor we no longer store rules or date fields on tournaments
    for field in ('rules', 'start_at', 'registration_start', 'registration_end'):
        assert not hasattr(Tournament, field), f"Tournament should not have {field}"


def test_team_captain_and_members_relationship():
    # Team should have captain_id field and members relationship
    assert hasattr(Team, 'captain_id')
    assert hasattr(Team, 'captain')
    assert hasattr(Team, 'members')
    # members should be a relationship property
    prop = Team.members.property
    assert prop.secondary is not None
