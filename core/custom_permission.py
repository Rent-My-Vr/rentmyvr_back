from rest_framework.permissions import IsAuthenticated


class IsAuthenticatedOrCreate(IsAuthenticated):
    
  def has_permission(self, request, view):
    if request.method == 'POST':
      return True
    return super(IsAuthenticatedOrCreate, self).has_permission(request, view)

