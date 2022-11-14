from django.conf import settings
from django.core.paginator import Paginator


def pagination(request, post_list):
    paginator = Paginator(post_list, settings.POSTS_PER_PAGE)
    return paginator.get_page(request.GET.get('page'))
