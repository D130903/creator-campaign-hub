def static_demo(request):
    """True when export_static renders the read-only GitHub Pages copy."""
    return {"static_demo": getattr(request, "static_demo", False)}
