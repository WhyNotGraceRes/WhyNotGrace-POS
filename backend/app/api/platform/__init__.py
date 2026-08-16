"""Platform-staff-only API surface, mounted at /api/v1/platform. Every route
in this package requires app.core.platform_dependencies.get_current_platform_user
— never app.core.dependencies.get_current_user, and never business_id from a
JWT claim (a platform token carries none). See app.models.platform_user for
why this is a structurally separate principal from a business's own staff.
"""
