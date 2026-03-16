from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from common.constants import MAX_PAGE_SIZE, PAGE_SIZE

class DefaultPagination(PageNumberPagination):
    """
    Custom pagination response used across the API.
    """
    page_size = PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = MAX_PAGE_SIZE

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link() if self.page.has_next() else None,
                "previous": self.get_previous_link() if self.page.has_previous() else None,
                "data": data,
            }   
        )

