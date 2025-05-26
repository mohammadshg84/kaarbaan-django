# my_app/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm


class CustomAuthenticationForm(AuthenticationForm):
    # You can add more fields or change the appearance of existing fields.
    # For example, you can change the label of the username field:
    username = forms.CharField(label='نام کاربری')
    password = forms.CharField(label='رمز عبور', widget=forms.PasswordInput)


# your_app_name/forms.py
from django import forms
from django.db.models import Q  # Import Q object for complex queries
from django.contrib.auth.models import User  # Import User model for TaskForm queryset
from .models import WorkReport, Project, Task, WorkTimeSpan, \
    UserGroup  # Ensure UserGroup is imported if used in ProjectForm
from ckeditor_uploader.widgets import CKEditorUploadingWidget  # For CKEditor in forms
from django.forms import inlineformset_factory

# Import Jalali Date fields and widgets
from jalali_date.fields import JalaliDateField
# Using AdminJalaliDateWidget for a more integrated date picker UI
from jalali_date.widgets import AdminJalaliDateWidget, AdminSplitJalaliDateTime


# 1. Form for Project model (for creating a new project)
class ProjectForm(forms.ModelForm):
    # Use JalaliDateField for deadline, with AdminJalaliDateWidget
    deadline = JalaliDateField(label='مهلت انجام پروژه', widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}))

    class Meta:
        model = Project
        fields = ['name', 'description', 'deadline', 'status', 'assigned_to_groups']
        widgets = {
            'description': CKEditorUploadingWidget(),
            # 'deadline' is now defined above, so no need here
        }
        labels = {
            'name': 'نام پروژه',
            'description': 'توضیحات پروژه',
            'status': 'وضعیت',
            'assigned_to_groups': 'اختصاص به گروه‌ها',
        }


# 2. Form for WorkReport model
class WorkReportForm(forms.ModelForm):
    # Use JalaliDateField for report_date, with AdminJalaliDateWidget
    report_date = JalaliDateField(label='تاریخ گزارش', widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}))

    class Meta:
        model = WorkReport
        fields = ['task', 'report_date', 'description']
        widgets = {
            'description': CKEditorUploadingWidget(),
            # 'report_date' is now defined above, so no need here
        }
        labels = {
            'task': 'وظیفه',
            'description': 'شرح فعالیت',
        }

    # Filter tasks based on the logged-in user and selected project
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Display tasks assigned to the user or created by the user
            self.fields['task'].queryset = Task.objects.filter(
                Q(assigned_to=user) | Q(created_by=user)
            ).distinct().order_by('title')
            # If you want to display only incomplete tasks:
            # self.fields['task'].queryset = Task.objects.filter(
            #     Q(assigned_to=user) | Q(created_by=user),
            #     status__in=['pending', 'in_progress', 'needs_review']
            # ).distinct().order_by('title')


# 3. Form for WorkTimeSpan model (for recording time ranges)
class WorkTimeSpanForm(forms.ModelForm):
    class Meta:
        model = WorkTimeSpan
        fields = ['start_time', 'end_time']  # Removed 'notes' field
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }
        labels = {
            'start_time': 'ساعت شروع',
            'end_time': 'ساعت پایان',
            # 'notes' label removed
        }


# Inline Formset for WorkTimeSpan
WorkTimeSpanFormSet = inlineformset_factory(
    WorkReport,  # Parent model
    WorkTimeSpan,  # Child model
    form=WorkTimeSpanForm,
    extra=1,  # At least one empty form to add
    can_delete=True,  # Allow deleting existing time ranges
    labels={
        'start_time': 'ساعت شروع',
        'end_time': 'ساعت پایان',
        # 'notes' label removed
        'DELETE': 'حذف',
    }
)


# 4. Form for Task model (for creating a new task)
class TaskForm(forms.ModelForm):
    # Use JalaliDateField for deadline, with AdminJalaliDateWidget
    deadline = JalaliDateField(label='مهلت انجام وظیفه', widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
                               required=False)  # required=False as it's null=True in model

    # Project as a separate field for selection in this form
    project = forms.ModelChoiceField(queryset=Project.objects.all().order_by('name'), label="پروژه مرتبط",
                                     widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Task
        fields = ['project', 'title', 'description', 'parent_task', 'assigned_to', 'deadline', 'status']
        widgets = {
            'description': CKEditorUploadingWidget(),
            # 'deadline' is now defined above, so no need here
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_task': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.SelectMultiple(attrs={'class': 'form-control'}),  # Use SelectMultiple for ManyToMany
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'عنوان وظیفه',
            'description': 'توضیحات وظیفه',
            'parent_task': 'وظیفه والد',
            'assigned_to': 'اختصاص یافته به',
            'status': 'وضعیت',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Get the user from kwargs
        super().__init__(*args, **kwargs)

        # Initialize parent_task queryset to an empty set by default
        self.fields['parent_task'].queryset = Task.objects.none()

        # If editing an existing task and it has a project
        # Check if self.instance is a saved object (has a primary key)
        if self.instance and self.instance.pk:
            # Safely check if 'project' attribute exists on the instance
            if hasattr(self.instance, 'project'):
                current_project = self.instance.project
                if current_project:  # Check if the project itself is not None
                    # Exclude the current task itself from parent_task options
                    self.fields['parent_task'].queryset = Task.objects.filter(project=current_project).exclude(
                        id=self.instance.id).order_by('title')

        # If the form is submitted (POST) and a project is selected in the form data
        # This takes precedence for new tasks or when project is changed
        elif self.data.get('project'):
            try:
                project_id = int(self.data.get('project'))
                self.fields['parent_task'].queryset = Task.objects.filter(project_id=project_id).order_by('title')
            except (ValueError, TypeError):
                # If project_id is invalid, keep queryset as none
                pass

        # Admin/User Task Creation Logic
        if user and not user.is_superuser:
            # For non-admin users, assigned_to should be automatically the current user
            # and the field should be hidden or set to readonly.
            self.fields['assigned_to'].queryset = User.objects.filter(id=user.id)
            self.fields['assigned_to'].initial = [user.id]  # Pre-select the current user
            self.fields['assigned_to'].widget = forms.HiddenInput()  # Hide the field
            self.fields['assigned_to'].required = False  # Not required if hidden and auto-set
            # You might also want to remove it from the form fields entirely if it's always auto-set
            # del self.fields['assigned_to']
        else:
            # For admin users, display all active users for assignment
            self.fields['assigned_to'].queryset = User.objects.filter(is_active=True).order_by('username')
# your_app_name/forms.py
# your_app_name/forms.py
from django import forms
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
from .models import Expense, Task

class ExpenseForm(forms.ModelForm):
    expense_date = JalaliDateField(label='تاریخ هزینه', widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}))

    class Meta:
        model = Expense
        fields = ['task', 'amount', 'description', 'expense_date']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'task': forms.HiddenInput(), # فیلد وظیفه رو مخفی می‌کنیم
        }
        labels = {
            'task': 'وظیفه مرتبط',
            'amount': 'مبلغ',
            'description': 'شرح هزینه',
            'expense_date': 'تاریخ هزینه',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # در این حالت، فیلد task رو فیلتر نمی‌کنیم چون مقدارش از initial پر میشه.
        # اما اگر می‌خواهید مطمئن بشید که task_id معتبره، اینجا می‌تونید بررسی کنید.
        # self.fields['task'].queryset = Task.objects.filter(assigned_to=user).distinct() # اگر نیاز به اعتبارسنجی باشه

# your_app_name/forms.py
from django import forms
from .models import FutureNote, Task
from ckeditor_uploader.widgets import CKEditorUploadingWidget

# ... (سایر فرم‌های شما) ...

# 6. فرم برای مدل FutureNote (ثبت ایده)
class FutureNoteForm(forms.ModelForm):
    class Meta:
        model = FutureNote
        fields = ['task', 'note']
        widgets = {
            'note': CKEditorUploadingWidget(), # استفاده از CKEditor
            'task': forms.HiddenInput(), # فیلد وظیفه رو مخفی می‌کنیم
        }
        labels = {
            'task': 'وظیفه مرتبط',
            'note': 'متن ایده',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # در این حالت، فیلد task رو فیلتر نمی‌کنیم چون مقدارش از initial پر میشه.
        # اما اگر می‌خواهید مطمئن بشید که task_id معتبره و کاربر به اون وظیفه دسترسی داره،
        # می‌تونید اینجا یک منطق اعتبارسنجی اضافه کنید.

# your_app_name/forms.py
from django import forms
from django.contrib.auth.models import User
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from .models import HelpRequest, HelpRequestMessage, Task # مطمئن شوید این مدل‌ها ایمپورت شده‌اند

# ... (سایر فرم‌های شما) ...
class HelpRequestForm(forms.ModelForm):
    class Meta:
        model = HelpRequest
        fields = ['task', 'problem_description']
        widgets = {
            'problem_description': CKEditorUploadingWidget(config_name='default'), # مطمئن شوید config_name='default' است
            'task': forms.HiddenInput(), # فیلد وظیفه را مخفی می‌کنیم
        }
        labels = {
            'task': 'وظیفه مرتبط',
            'problem_description': 'شرح مشکل',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # در این حالت، فیلد task را فیلتر نمی‌کنیم چون مقدارش از initial پر می‌شود.
        # می‌توانید منطق اعتبارسنجی را اینجا اضافه کنید اگر لازم است.
# 8. فرم برای مدل HelpRequestMessage (ارسال پیام در چت)
class HelpRequestMessageForm(forms.ModelForm):
    class Meta:
        model = HelpRequestMessage
        fields = ['message']
        widgets = {
            'message': CKEditorUploadingWidget(config_name='awesome_ckeditor'), # این بخش بدون تغییر باقی می‌ماند
        }
        labels = {
            'message': 'پیام شما',
        }


# your_app_name/forms.py
from django import forms
from django.contrib.auth.models import User # برای فیلتر کردن بر اساس کاربر
from .models import Project # برای فیلتر کردن بر اساس پروژه
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget

# ... (سایر فرم‌های شما) ...

# 9. فرم فیلتر گزارش‌ها برای مدیران
class ReportFilterForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('username'),
        required=False,
        label="کاربر",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.all().order_by('name'),
        required=False,
        label="پروژه",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    # تاریخ شروع و پایان برای فیلتر کردن در بازه زمانی
    start_date = JalaliDateField(
        label='از تاریخ',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        required=False
    )
    end_date = JalaliDateField(
        label='تا تاریخ',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        required=False
    )

    # می‌توانید فیلترهای بیشتری مانند وضعیت گزارش یا وظیفه اضافه کنید
    # status = forms.ChoiceField(
    #     choices=WorkReport.STATUS_CHOICES, # باید از مدل WorkReport یا Task وارد شود
    #     required=False,
    #     label="وضعیت",
    #     widget=forms.Select(attrs={'class': 'form-control'})
    # )

# your_app_name/forms.py
# your_app_name/forms.py
from django import forms
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
from .models import Project, Task # مطمئن شوید این مدل‌ها ایمپورت شده‌اند

class WorkReportFilterForm(forms.Form):
    project = forms.ChoiceField(
        choices=[],  # پر می شود در __init__
        required=False,
        label="پروژه",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    task = forms.ChoiceField(
        choices=[],  # پر می شود در __init__
        required=False,
        label="وظیفه",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    # تغییر: به جای report_date، از start_date و end_date استفاده می‌کنیم
    start_date = JalaliDateField(
        label='از تاریخ',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        required=False
    )
    end_date = JalaliDateField(
        label='تا تاریخ',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        required=False
    )
    search = forms.CharField(
        max_length=255,
        required=False,
        label="جستجو",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'جستجو در گزارش‌ها'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # پر کردن choices ها به صورت داینامیک
        # از all_projects و all_tasks به جای مستقیم مدل‌ها استفاده می‌کنیم
        # اینها باید از ویو به فرم پاس داده شوند اگر می‌خواهید کوئری‌ست‌های فیلتر شده را استفاده کنید
        # در غیر این صورت، این بخش را مستقیماً از مدل‌ها پر کنید:
        self.fields['project'].choices = [('', 'انتخاب پروژه...')] + [(p.id, p.name) for p in Project.objects.all().order_by('name')]
        self.fields['task'].choices = [('', 'انتخاب وظیفه...')] + [(t.id, f"{t.title} (پروژه: {t.project.name})") for t in Task.objects.all().order_by('title')]