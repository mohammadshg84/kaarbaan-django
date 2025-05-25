# your_app_name/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Count, Sum, Avg, F
from django.utils import timezone
from .models import (
    WorkReport, Task, FutureNote, Expense, UserProfile, UserPerformanceMetrics,
    ManagerFeedback  # برای محاسبه avg_feedback_score اگر چنین فیلدی اضافه شود
)
from django.contrib.auth.models import User


# سیگنال برای ایجاد UserProfile و UserPerformanceMetrics هنگام ایجاد کاربر جدید
@receiver(post_save, sender=User)
def create_user_related_models(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        UserPerformanceMetrics.objects.get_or_create(user=instance)


# سیگنال برای به‌روزرسانی متریک‌ها هنگام ذخیره یا حذف WorkReport
@receiver(post_save, sender=WorkReport)
@receiver(post_delete, sender=WorkReport)
def update_performance_metrics_on_report_change(sender, instance, **kwargs):
    user_performance, created = UserPerformanceMetrics.objects.get_or_create(user=instance.reporter)

    # محاسبه تعداد وظایف تکمیل شده
    # فرض می‌کنیم 'completed' بودن یک Task از طریق وضعیت Task مشخص می‌شود
    # و نه صرفاً با ثبت WorkReport. WorkReport صرفاً فعالیت را نشان می‌دهد.
    # برای این فیلد، ما روی Task ها تمرکز می‌کنیم.

    # میانگین تناوب گزارش (Avg_report_frequency):
    # این متریک کمی پیچیده است و نیاز به تعریف "تناوب" دارد.
    # مثلاً، تعداد گزارش‌های ثبت شده در یک بازه زمانی مشخص (مثل 30 روز گذشته) تقسیم بر تعداد روزهای فعال.
    # برای سادگی، می‌توانیم فعلاً تعداد کل گزارش‌ها را در نظر بگیریم
    # یا آن را در یک Cron Job جداگانه محاسبه کنیم که به صورت دوره‌ای اجرا شود.

    # فعلاً برای 'total_tasks_completed' و 'total_ideas_submitted' و 'total_expenses_reported'
    # ما باید روی تغییرات WorkReport و سایر مدل‌ها تمرکز کنیم.
    # این سیگنال بیشتر روی گزارش‌ها تمرکز دارد.

    # محاسبه مجدد total_tasks_completed و on_time_completion_rate
    # اینها باید بر اساس تغییرات در مدل Task محاسبه شوند، نه WorkReport.
    # ما این بخش را به سیگنال 'Task' منتقل می‌کنیم.

    # محاسبه میانگین تناوب گزارش بر اساس تعداد گزارشات و روزهای فعال
    # این می‌تواند یک محاسبه پیچیده باشد که بهتر است در یک Cron Job انجام شود.
    # در اینجا صرفاً برای نمونه، تعداد گزارش‌ها را می‌شماریم.
    user_performance.avg_report_frequency = WorkReport.objects.filter(
        reporter=instance.reporter).count()  # این یک میانگین نیست، بلکه تعداد کل است. نیاز به منطق دقیق‌تر.

    user_performance.last_updated = timezone.now()
    user_performance.save()


# سیگنال برای به‌روزرسانی متریک‌ها هنگام ذخیره یا حذف Task
@receiver(post_save, sender=Task)
@receiver(post_delete, sender=Task)
def update_performance_metrics_on_task_change(sender, instance, **kwargs):
    # این سیگنال برای هر کاربری که assigned_to این تسک بوده است، باید اجرا شود.
    # همچنین برای created_by.

    users_to_update = set(instance.assigned_to.all())
    if instance.created_by:
        users_to_update.add(instance.created_by)

    for user in users_to_update:
        user_performance, created = UserPerformanceMetrics.objects.get_or_create(user=user)

        # محاسبه total_tasks_completed
        completed_tasks_count = Task.objects.filter(assigned_to=user, status='completed').count()
        user_performance.total_tasks_completed = completed_tasks_count

        # محاسبه on_time_completion_rate
        # این نیاز به مقایسه deadline با تاریخ تکمیل واقعی دارد.
        # فرض می‌کنیم تاریخ تکمیل واقعی همان updated_at است اگر status='completed' باشد.
        total_assigned_tasks = Task.objects.filter(assigned_to=user).count()
        if total_assigned_tasks > 0:
            on_time_tasks = Task.objects.filter(
                assigned_to=user,
                status='completed',
                updated_at__lte=F('deadline')  # اینجا فرض می‌کنیم updated_at همان تاریخ تکمیل است
            ).count()
            user_performance.on_time_completion_rate = (on_time_tasks / total_assigned_tasks) * 100
        else:
            user_performance.on_time_completion_rate = 0.0

        user_performance.last_updated = timezone.now()
        user_performance.save()


# سیگنال برای به‌روزرسانی متریک‌ها هنگام ذخیره یا حذف FutureNote (ایده)
@receiver(post_save, sender=FutureNote)
@receiver(post_delete, sender=FutureNote)
def update_performance_metrics_on_future_note_change(sender, instance, **kwargs):
    user_performance, created = UserPerformanceMetrics.objects.get_or_create(user=instance.user)
    user_performance.total_ideas_submitted = FutureNote.objects.filter(user=instance.user).count()
    user_performance.last_updated = timezone.now()
    user_performance.save()


# سیگنال برای به‌روزرسانی متریک‌ها هنگام ذخیره یا حذف Expense (هزینه)
@receiver(post_save, sender=Expense)
@receiver(post_delete, sender=Expense)
def update_performance_metrics_on_expense_change(sender, instance, **kwargs):
    user_performance, created = UserPerformanceMetrics.objects.get_or_create(user=instance.user)
    total_expenses = Expense.objects.filter(user=instance.user).aggregate(Sum('amount'))['amount__sum'] or 0
    user_performance.total_expenses_reported = total_expenses
    user_performance.last_updated = timezone.now()
    user_performance.save()

# اگر بخواهید avg_feedback_score را به UserPerformanceMetrics اضافه کنید:
# نیاز به یک سیستم امتیازدهی در ManagerFeedback دارید
# @receiver(post_save, sender=ManagerFeedback)
# @receiver(post_delete, sender=ManagerFeedback)
# def update_performance_metrics_on_feedback_change(sender, instance, **kwargs):
#     # فرض می‌کنیم ManagerFeedback یک فیلد rating دارد
#     user_performance, created = UserPerformanceMetrics.objects.get_or_create(user=instance.task.assigned_to.first()) # یا همه assigned_to ها
#     feedbacks = ManagerFeedback.objects.filter(task__assigned_to=user_performance.user)
#     if feedbacks.exists():
#         user_performance.avg_feedback_score = feedbacks.aggregate(Avg('rating'))['rating__avg']
#     else:
#         user_performance.avg_feedback_score = 0.0
#     user_performance.last_updated = timezone.now()
#     user_performance.save()