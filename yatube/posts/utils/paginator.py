from django.core.paginator import Paginator

POSTS_PER_PAGE = 10


def get_page_obj(request, queryset):
    paginator = Paginator(queryset, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
