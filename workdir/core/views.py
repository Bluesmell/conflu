from django.http import HttpResponse

def sentry_test_view(request):
    1 / 0  # This will raise a ZeroDivisionError, Sentry should capture it.
    return HttpResponse("This should not be reached.") # Should not happen
