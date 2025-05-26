# your_app_name/admin.py
from django.contrib import admin
from jalali_date.admin import ModelAdminJalaliMixin
from django.utils import timezone # For using timezone.now() in actions (already there)

from .models import (
    UserGroup, Project, Task, WorkReport, WorkReportAttachment,
    GithubCommitLink, Expense, FutureNote, ManagerFeedback, HelpRequest,
    UserProfile, Achievement, UserAchievement, UserPerformanceMetrics, Notification,
    HelpRequestMessage,
    WorkTimeSpan # مدل جدید را اینجا import کنید
)

# --- INLINE DEFINITIONS ---
# All inline classes should be defined here, BEFORE any @admin.register() classes use them.

class WorkReportAttachmentInline(admin.TabularInline):
    model = WorkReportAttachment
    extra = 1

class GithubCommitLinkInline(admin.TabularInline):
    model = GithubCommitLink
    extra = 1

class ExpenseInline(admin.TabularInline):
    model = Expense
    extra = 1

class FutureNoteInline(admin.TabularInline):
    model = FutureNote
    extra = 0

class ManagerFeedbackInline(admin.TabularInline):
    model = ManagerFeedback
    extra = 0

class HelpRequestMessageInline(admin.TabularInline):
    model = HelpRequestMessage
    extra = 1
    readonly_fields = ('sender', 'sent_at')

# CORRECTED: Define WorkTimeSpanInline here
class WorkTimeSpanInline(admin.TabularInline):
    model = WorkTimeSpan
    extra = 1 # تعداد فیلدهای خالی برای افزودن جدید
    fields = ('start_time', 'end_time', 'notes')

class TaskInline(admin.TabularInline):
    model = Task
    fk_name = 'parent_task' # برای نمایش زیروظیفه‌ها (subtasks) در Task والد
    extra = 1
    fields = ('title', 'status', 'assigned_to', 'deadline')
    raw_id_fields = ('assigned_to',)


# --- ADMIN MODEL REGISTRATIONS ---

# 1. UserGroup Admin
@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'get_member_count')
    search_fields = ('name', 'description')
    filter_horizontal = ('members',)

    def get_member_count(self, obj):
        return obj.members.count()
    get_member_count.short_description = "تعداد اعضا"


# 2. Project Admin
@admin.register(Project)
class ProjectAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('name', 'deadline', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'created_at', 'assigned_to_groups')
    search_fields = ('name', 'description')
    raw_id_fields = ('created_by',)
    filter_horizontal = ('assigned_to_groups',)
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'status', 'deadline')
        }),
        ('اختصاص و ایجاد', {
            'fields': ('assigned_to_groups', 'created_by')
        }),
    )


# 3. Task Admin
@admin.register(Task)
class TaskAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('title', 'project', 'parent_task', 'status', 'deadline', 'created_by', 'is_approved')
    list_filter = ('status', 'project', 'created_at', 'is_approved')
    search_fields = ('title', 'description')
    raw_id_fields = ('project', 'parent_task', 'created_by', 'approved_by')
    filter_horizontal = ('assigned_to',)
    inlines = [TaskInline]

    actions = ['mark_as_approved', 'mark_as_rejected']

    def mark_as_approved(self, request, queryset):
        queryset.update(is_approved=True, status='approved', approved_by=request.user, approval_date=timezone.now())
        self.message_user(request, "وظایف انتخاب شده تایید شدند.")
    mark_as_approved.short_description = "تایید وظایف انتخاب شده"

    def mark_as_rejected(self, request, queryset):
        queryset.update(is_approved=False, status='rejected', approved_by=request.user, approval_date=timezone.now())
        self.message_user(request, "وظایف انتخاب شده رد شدند.")
    mark_as_rejected.short_description = "رد وظایف انتخاب شده"


# 4. WorkReport Admin
@admin.register(WorkReport)
class WorkReportAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('task', 'reporter', 'report_date', 'get_total_duration', 'created_at')
    list_filter = ('report_date', 'reporter', 'task__project')
    search_fields = ('description',)
    raw_id_fields = ('task', 'reporter')
    # Use WorkTimeSpanInline here now that it's defined above
    inlines = [WorkTimeSpanInline, WorkReportAttachmentInline, GithubCommitLinkInline]

    def get_total_duration(self, obj):
        total_seconds = 0
        for ts in obj.time_spans.all():
            if ts.start_time and ts.end_time:
                start_dt = timezone.datetime(2000, 1, 1, ts.start_time.hour, ts.start_time.minute, ts.start_time.second)
                end_dt = timezone.datetime(2000, 1, 1, ts.end_time.hour, ts.end_time.minute, ts.end_time.second)

                if end_dt < start_dt:
                    end_dt += timezone.timedelta(days=1)

                duration = end_dt - start_dt
                total_seconds += duration.total_seconds()

        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    get_total_duration.short_description = "مدت زمان کل"


# 7. Expense Admin
@admin.register(Expense)
class ExpenseAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('task', 'user', 'amount', 'expense_date', 'created_at')
    list_filter = ('expense_date', 'user', 'task__project')
    search_fields = ('description',)
    raw_id_fields = ('task', 'user')


# 8. FutureNote Admin
@admin.register(FutureNote)
class FutureNoteAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'created_at')
    list_filter = ('user', 'created_at', 'task__project')
    search_fields = ('note',)
    raw_id_fields = ('task', 'user')


# 9. ManagerFeedback Admin
@admin.register(ManagerFeedback)
class ManagerFeedbackAdmin(admin.ModelAdmin):
    list_display = ('task', 'manager', 'created_at')
    list_filter = ('manager', 'created_at', 'task__project')
    search_fields = ('feedback',)
    raw_id_fields = ('task', 'manager')


# 10. HelpRequest Admin
@admin.register(HelpRequest)
class HelpRequestAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('task', 'requester', 'is_resolved', 'requested_at', 'resolved_by', 'resolved_at')
    list_filter = ('is_resolved', 'requester', 'requested_at', 'task__project')
    search_fields = ('problem_description',)
    raw_id_fields = ('task', 'requester', 'resolved_by')
    inlines = [HelpRequestMessageInline]


# 12. UserProfile Admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'پروفایل کاربر'

admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = BaseUserAdmin.list_display + ('get_total_points',)

    def get_total_points(self, obj):
        return obj.userprofile.total_points if hasattr(obj, 'userprofile') else 0
    get_total_points.short_description = 'امتیاز کل'


# 13. Achievement Admin
@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_awarded')
    search_fields = ('name', 'description')


# 14. UserAchievement Admin
@admin.register(UserAchievement)
class UserAchievementAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('user', 'achievement', 'earned_at')
    list_filter = ('user', 'achievement', 'earned_at')
    raw_id_fields = ('user', 'achievement')


# 15. UserPerformanceMetrics Admin
@admin.register(UserPerformanceMetrics)
class UserPerformanceMetricsAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('user', 'total_tasks_completed', 'on_time_completion_rate', 'avg_report_frequency', 'total_ideas_submitted', 'total_expenses_reported', 'last_updated')
    list_filter = ('last_updated',)
    raw_id_fields = ('user',)
    readonly_fields = ('user', 'total_tasks_completed', 'on_time_completion_rate',
                       'avg_report_frequency', 'total_ideas_submitted', 'total_expenses_reported', 'last_updated')


# 16. Notification Admin
@admin.register(Notification)
class NotificationAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'is_read', 'created_at', 'link')
    list_filter = ('is_read', 'notification_type', 'recipient', 'created_at')
    search_fields = ('message',)
    raw_id_fields = ('recipient',)
    readonly_fields = ('created_at',)
    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, "اعلانات انتخاب شده به عنوان خوانده شده علامت‌گذاری شدند.")
    mark_as_read.short_description = "علامت‌گذاری به عنوان خوانده شده"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, "اعلانات انتخاب شده به عنوان خوانده نشده علامت‌گذاری شدند.")
    mark_as_unread.short_description = "علامت‌گذاری به عنوان خوانده نشده"