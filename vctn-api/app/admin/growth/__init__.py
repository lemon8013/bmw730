"""app.admin.growth — administrator-facing growth, point, level and task surface.

The platform ``growth`` / ``points`` / ``tasks`` modules are all ``/me``-shaped:
they resolve identity from the signed-in **business user**. The console signs in
as an operator, so it cannot reach them. This module re-exposes the same data
addressed by explicit ``user_id`` and adds the catalog CRUD that the frozen
permission matrix already reserves codes for.
"""
