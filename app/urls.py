from django.urls import path
from . import views
from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView # این خط را اضافه کنید

urlpatterns = [
    path('login/', views.MyLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'), # آدرس ریدایرکت پس از خروج
    path('reports/', views.work_report_list, name='work_report_list'),
    # مسیرهای placeholder برای دکمه‌های دیگر (بعداً باید ایجاد شوند)
    path('reports/new/', views.create_new_report, name='create_new_report'), # شما باید این ویو را ایجاد کنید
    path('reports/<int:report_id>/edit/', views.edit_report, name='edit_report'), # شما باید این ویو را ایجاد کنید
    path('expenses/task/<int:task_id>/new/', views.register_expense, name='register_expense'), # مسیر جدید
    path('future_notes/task/<int:task_id>/new/', views.register_future_note, name='register_future_note'), # مسیر اصلاح شده
    path('help_requests/task/<int:task_id>/new/', views.submit_help_request, name='submit_help_request'),
    # مسیر اصلاح شده

    path('help_requests/<int:help_request_id>/chat/', views.help_request_chat, name='help_request_chat'),
    # برای صفحه چت
    path('adm/reports/', views.admin_report_view, name='admin_report_view'),

    # path('help_requests/<int:report_id>/new/', views.submit_help_request, name='submit_help_request'), # این خط قدیمی است و باید حذف شود
    path('reports/new/', views.create_new_report, name='create_new_report'),
    path('ajax/load_tasks/', views.load_tasks, name='load_tasks'), # برای فیلتر وظایف در فرم گزارش
    path('ajax/load_parent_tasks/', views.load_parent_tasks, name='load_parent_tasks'), # برای فیلتر وظایف والد در فرم وظیفه

    path('adm/help_requests/', views.admin_help_requests_chat_list, name='admin_help_requests_chat_list'),
    path('adm/help_requests/<int:help_request_id>/', views.admin_help_request_chat_detail, name='admin_help_request_chat_detail'),
    path('adm/help_requests/<int:help_request_id>/resolve/', views.mark_help_request_resolved, name='mark_help_request_resolved'),
    path('adm/help_requests/<int:help_request_id>/unresolve/', views.mark_help_request_unresolved, name='mark_help_request_unresolved'),
    path('', RedirectView.as_view(url='/reports/', permanent=False), name='home_redirect'),
    path('dashboard/', RedirectView.as_view(url='/reports/', permanent=False), name='home_redirect'),

]