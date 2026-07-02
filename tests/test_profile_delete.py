"""Profile soft-delete repository check."""

from core.db.repositories.profiles import create_profile, delete_profile as deactivate_profile, get_all_profiles


def test_deactivate_profile_hides_from_active_list(fresh_db):
    p = create_profile("Temp")
    assert deactivate_profile(p.id)
    active = get_all_profiles(active_only=True)
    assert not any(x.id == p.id for x in active)
    all_profiles = get_all_profiles(active_only=False)
    assert any(x.id == p.id and not x.is_active for x in all_profiles)