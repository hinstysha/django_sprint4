from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage


def paginate_queryset(queryset, request, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    return page_obj
