# your_app_name/context_processors.py

def user_is_manager(request):
    # تابع is_manager که قبلاً در views.py تعریف کرده بودید یا مستقیماً اینجا پیاده‌سازی کنید
    def _is_manager(user):
        if user.is_authenticated:
            # مطمئن شوید مدل UserGroup ایمپورت شده باشد اگر مستقیماً از آن استفاده می‌کنید
            # from .models import UserGroup
            return user.is_staff or user.groups.filter(name='مدیران').exists()
        return False

    return {
        'is_manager_context': _is_manager(request.user)
    }