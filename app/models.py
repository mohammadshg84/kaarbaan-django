from django.db import models
from django.contrib.auth.models import User
from ckeditor_uploader.fields import RichTextUploadingField # برای CKEditor

# 1. مدل گروه کاربران (UserGroup)
class UserGroup(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام گروه")
    description = models.TextField(blank=True, verbose_name="توضیحات گروه")
    members = models.ManyToManyField(User, related_name="user_groups", verbose_name="اعضا")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "گروه کاربران"
        verbose_name_plural = "گروه‌های کاربران"


# 2. مدل پروژه (Project / Category)
class Project(models.Model):
    STATUS_CHOICES = (
        ('pending', 'در حال انجام'),
        ('completed', 'انجام شده'),
        ('finished', 'تمام شده'),
    )
    name = models.CharField(max_length=200, verbose_name="نام پروژه")
    description = RichTextUploadingField(blank=True, verbose_name="توضیحات پروژه") # CKEditor
    deadline = models.DateField(verbose_name="مهلت انجام پروژه")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    assigned_to_groups = models.ManyToManyField(UserGroup, blank=True, related_name="projects", verbose_name="اختصاص به گروه‌ها")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_projects", verbose_name="ایجاد کننده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "پروژه"
        verbose_name_plural = "پروژه‌ها"


# 3. مدل وظیفه (Task)
class Task(models.Model):
    STATUS_CHOICES = (
        ('pending', 'در انتظار'),
        ('in_progress', 'در حال انجام'),
        ('needs_review', 'نیاز به بررسی'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
        ('completed', 'تکمیل شده'),
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks", verbose_name="پروژه")
    parent_task = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name="subtasks", verbose_name="وظیفه والد")
    title = models.CharField(max_length=255, verbose_name="عنوان وظیفه")
    description = RichTextUploadingField(blank=True, verbose_name="توضیحات وظیفه") # CKEditor
    assigned_to = models.ManyToManyField(User, related_name="assigned_tasks", verbose_name="اختصاص یافته به")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_tasks", verbose_name="ایجاد کننده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    deadline = models.DateField(null=True, blank=True, verbose_name="مهلت انجام وظیفه")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    is_approved = models.BooleanField(default=False, verbose_name="تایید شده توسط مدیر")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_tasks", verbose_name="تایید کننده")
    approval_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ تایید/رد")
    rejection_reason = models.TextField(blank=True, verbose_name="دلیل رد شدن") # اینجا CKEditor لازم نیست

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "وظیفه"
        verbose_name_plural = "وظایف"


# 4. مدل گزارش کار (WorkReport)
class WorkReport(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="work_reports", verbose_name="وظیفه")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reported_work", verbose_name="گزارش دهنده")
    report_date = models.DateField(verbose_name="تاریخ گزارش")
    description = RichTextUploadingField(verbose_name="شرح فعالیت") # CKEditor
    start_time = models.TimeField(null=True, blank=True, verbose_name="ساعت شروع")
    end_time = models.TimeField(null=True, blank=True, verbose_name="ساعت پایان")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ و زمان ثبت گزارش")

    def __str__(self):
        return f"گزارش کار {self.reporter.username} در {self.report_date} برای {self.task.title}"

    class Meta:
        verbose_name = "گزارش کار"
        verbose_name_plural = "گزارش‌های کار"
        ordering = ['-report_date', '-created_at']


# 5. مدل فایل پیوست (WorkReportAttachment)
class WorkReportAttachment(models.Model):
    work_report = models.ForeignKey(WorkReport, on_delete=models.CASCADE, related_name="attachments", verbose_name="گزارش کار")
    file = models.FileField(upload_to='work_report_attachments/', verbose_name="فایل")
    file_type = models.CharField(max_length=50, blank=True, verbose_name="نوع فایل")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")

    def __str__(self):
        return f"پیوست برای گزارش {self.work_report.id}"

    class Meta:
        verbose_name = "پیوست گزارش کار"
        verbose_name_plural = "پیوست‌های گزارش کار"


# 6. مدل لینک گیت‌هاب (GithubCommitLink)
class GithubCommitLink(models.Model):
    work_report = models.ForeignKey(WorkReport, on_delete=models.CASCADE, related_name="github_links", verbose_name="گزارش کار")
    commit_url = models.URLField(verbose_name="لینک Commit گیت‌هاب")
    description = models.TextField(blank=True, verbose_name="توضیحات لینک")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ افزودن")

    def __str__(self):
        return self.commit_url

    class Meta:
        verbose_name = "لینک گیت‌هاب"
        verbose_name_plural = "لینک‌های گیت‌هاب"


# 7. مدل هزینه‌ها (Expense)
class Expense(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="expenses", verbose_name="وظیفه")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reported_expenses", verbose_name="ثبت کننده هزینه")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مبلغ")
    description = models.TextField(blank=True, verbose_name="شرح هزینه") # اینجا CKEditor لازم نیست
    expense_date = models.DateField(verbose_name="تاریخ هزینه")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    def __str__(self):
        return f"{self.amount} برای {self.task.title} توسط {self.user.username}"

    class Meta:
        verbose_name = "هزینه"
        verbose_name_plural = "هزینه‌ها"


# 8. مدل ایده (FutureNote)
class FutureNote(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="future_notes", verbose_name="وظیفه")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_future_notes", verbose_name="ثبت کننده ایده")
    note = RichTextUploadingField(verbose_name="متن ایده") # CKEditor
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    def __str__(self):
        return f"ایده برای {self.task.title} توسط {self.user.username}"

    class Meta:
        verbose_name = "ایده"
        verbose_name_plural = "ایده‌ها"


# 9. مدل بازخورد مدیر (ManagerFeedback)
class ManagerFeedback(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="feedbacks", verbose_name="وظیفه")
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_feedbacks", verbose_name="مدیر")
    feedback = RichTextUploadingField(verbose_name="بازخورد") # CKEditor
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    def __str__(self):
        return f"بازخورد برای {self.task.title} توسط {self.manager.username}"

    class Meta:
        verbose_name = "بازخورد مدیر"
        verbose_name_plural = "بازخوردهای مدیر"


# 10. مدل درخواست کمک (HelpRequest)
class HelpRequest(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="help_requests", verbose_name="وظیفه")
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submitted_help_requests", verbose_name="درخواست کننده")
    problem_description = RichTextUploadingField(verbose_name="شرح مشکل") # CKEditor
    is_resolved = models.BooleanField(default=False, verbose_name="برطرف شده")
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_help_requests", verbose_name="حل کننده")
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ درخواست")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ حل مشکل")

    def __str__(self):
        return f"درخواست کمک برای {self.task.title} توسط {self.requester.username}"

    class Meta:
        verbose_name = "درخواست کمک"
        verbose_name_plural = "درخواست‌های کمک"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="کاربر")
    total_points = models.IntegerField(default=0, verbose_name="امتیاز کل")
    # می‌توانید فیلدهای دیگری مانند سطح، تعداد جوایز و غیره را اینجا اضافه کنید.

    def __str__(self):
        return f"پروفایل {self.user.username}"

    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل‌های کاربران"

class Achievement(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام دستاورد")
    description = RichTextUploadingField(verbose_name="توضیحات دستاورد") # CKEditor
    badge_image = models.ImageField(upload_to='badges/', null=True, blank=True, verbose_name="تصویر نشان")
    points_awarded = models.IntegerField(default=0, verbose_name="امتیاز")
    # می‌توانید فیلدهایی برای تعریف شرط کسب دستاورد اضافه کنید (مثلاً: ثبت 100 گزارش کار، اتمام 5 پروژه)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "دستاورد"
        verbose_name_plural = "دستاوردها"

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="کاربر")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, verbose_name="دستاورد")
    earned_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ کسب")

    class Meta:
        unique_together = ('user', 'achievement') # هر کاربر فقط یک بار هر دستاورد را کسب کند
        verbose_name = "دستاورد کاربر"
        verbose_name_plural = "دستاورد‌های کاربر"

class UserPerformanceMetrics(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="کاربر")
    total_tasks_completed = models.IntegerField(default=0, verbose_name="کل وظایف تکمیل شده")
    on_time_completion_rate = models.FloatField(default=0.0, verbose_name="درصد تکمیل به موقع") # (تعداد وظایف به موقع / کل وظایف تکمیل شده)
    avg_report_frequency = models.FloatField(default=0.0, verbose_name="میانگین تناوب گزارش") # مثلاً: 1.5 گزارش در روز
    total_ideas_submitted = models.IntegerField(default=0, verbose_name="کل ایده‌های ثبت شده")
    total_expenses_reported = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name="کل هزینه‌های گزارش شده")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    def __str__(self):
        return f"عملکرد {self.user.username}"

    class Meta:
        verbose_name = "متریک عملکرد کاربر"
        verbose_name_plural = "متریک‌های عملکرد کاربران"


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications", verbose_name="گیرنده")
    message = RichTextUploadingField(verbose_name="متن پیام")  # CKEditor
    link = models.URLField(blank=True, null=True, verbose_name="لینک مربوطه")  # لینک به Task یا WorkReport
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    NOTIFICATION_TYPES = (
        ('task_deadline', 'مهلت وظیفه'),
        ('report_due', 'زمان گزارش کار'),
        ('task_approved', 'وظیفه تایید شد'),
        ('task_rejected', 'وظیفه رد شد'),
        ('new_feedback', 'بازخورد جدید'),
        ('new_help_request', 'درخواست کمک جدید'),
        ('new_achievement', 'دستاورد جدید'),  # اضافه شده برای گیمیفیکیشن
        # ... انواع دیگر
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, verbose_name="نوع اعلان")

    def __str__(self):
        return f"اعلان برای {self.recipient.username}: {self.message[:50]}..."

    class Meta:
        ordering = ['-created_at']
        verbose_name = "اعلان"
        verbose_name_plural = "اعلانات"

# ... سایر مدل‌ها ...

# 11. مدل پیام‌های درخواست کمک (HelpRequestMessage)
class HelpRequestMessage(models.Model):
    help_request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name="messages", verbose_name="درخواست کمک")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="فرستنده")
    message = RichTextUploadingField(verbose_name="متن پیام") # CKEditor برای پیام‌های چت
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ و زمان ارسال")

    def __str__(self):
        return f"پیام از {self.sender.username} برای درخواست {self.help_request.id}"

    class Meta:
        verbose_name = "پیام درخواست کمک"
        verbose_name_plural = "پیام‌های درخواست‌های کمک"
        ordering = ['sent_at'] # مرتب سازی بر اساس زمان برای نمایش چت