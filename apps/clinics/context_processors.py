def subscription_context(request):
    """Makes clinic subscription info available in all templates for logged-in clinic staff."""
    ctx = {'subscription': None, 'days_remaining': 0}
    if request.user.is_authenticated and request.user.clinic_id:
        clinic = request.user.clinic
        ctx['subscription']   = clinic
        ctx['days_remaining'] = clinic.days_remaining
    return ctx