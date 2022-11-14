from django.utils import timezone


def year(request):
    dt = timezone.localtime().year
    return {'year': dt}
