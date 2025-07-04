from django.conf import settings
from rest_framework import pagination
from rest_framework.response import Response


class MyPaginationMixin(object):

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination 
        is disabled.
        """
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(
            queryset, self.request, view=self)

    def get_paginated_response(self, data):
        """
        Return a paginated style `Response` object for the given 
        output data.
        """
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)
     
     
class MyPagination(pagination.PageNumberPagination):
    page_size = 100
    max_page_size = 500

    def get_paginated_response(self, data):
        return Response({
            'links': {
               'next': self.get_next_link(),
               'previous': self.get_previous_link()
            },
            'page_size': self.page_size,
            'current_page': self.page.number,
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'data': data
        })