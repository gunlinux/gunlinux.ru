"""Unit tests for the authentication adapter."""


def test_non_user(admin_app, client_admin):
    """Test that admin views are accessible to authenticated users."""
    # Access the admin page - it should be accessible to authenticated users
    rv = client_admin.get("/admin/")
    assert rv.status_code == 404

    rv = client_admin.get("/login")
    assert rv.status_code == 200

    links = (
        "admin_user",
        "admin_post",
        "admin_category",
        "admin_tag",
        "admin_icon",
    )

    for link in links:
        url = f"/admin/{link}/"
        rv = client_admin.get(url)
        assert rv.status_code == 403

        url = f"/admin/{link}/new/"
        rv = client_admin.get(url)
        assert rv.status_code == 403
    rv = client_admin.get("/admin/myfileadmin/")
    assert rv.status_code == 403
