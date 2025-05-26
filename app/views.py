# my_app/views.py
from django.contrib.auth.views import LoginView
from .forms import CustomAuthenticationForm
from django.contrib.auth.models import User

class MyLoginView(LoginView):
    template_name = 'login.html'  # مسیر تمپلیت لاگین شما
    authentication_form = CustomAuthenticationForm # استفاده از فرم سفارشی
    # success_url = '/dashboard/'  # آدرس ریدایرکت پس از لاگین موفق (اختیاری)
                                 # اگر تعریف نشود، به تنظیمات LOGIN_REDIRECT_URL در settings.py نگاه می‌کند.


# your_app_name/views.py
# your_app_name/views.py
from django.shortcuts import render
from django.db.models import Q
from datetime import timedelta, datetime, time # مطمئن شوید datetime و time هم ایمپورت شده‌اند
from .models import WorkReport, Project, Task, WorkTimeSpan
from .forms import WorkReportFilterForm
from jalali_date import date2jalali, datetime2jalali

def work_report_list(request):
    reports_queryset = WorkReport.objects.all().order_by('-report_date', '-created_at')

    form = WorkReportFilterForm(request.GET)

    # ... (متغیرهای selected_project, selected_task, etc. بدون تغییر) ...

    if form.is_valid():
        selected_project = form.cleaned_data.get('project')
        selected_task = form.cleaned_data.get('task')
        start_date_filter = form.cleaned_data.get('start_date')
        end_date_filter = form.cleaned_data.get('end_date')
        search_query = form.cleaned_data.get('search')

        if selected_project:
            reports_queryset = reports_queryset.filter(task__project_id=selected_project.id)
        if selected_task:
            reports_queryset = reports_queryset.filter(task_id=selected_task.id)
        if start_date_filter:
            reports_queryset = reports_queryset.filter(report_date__gte=start_date_filter)
        if end_date_filter:
            reports_queryset = reports_queryset.filter(report_date__lte=end_date_filter)
        if search_query:
            reports_queryset = reports_queryset.filter(
                Q(description__icontains=search_query) |
                Q(task__title__icontains=search_query) |
                Q(task__project__name__icontains=search_query)
            )

    reports = reports_queryset

    # --- محاسبه گزارش‌های جمع‌آوری شده ---
    total_hours_worked = timedelta(0)
    project_hours = {}

    for report in reports:
        for time_span in report.time_spans.all():
            if time_span.start_time and time_span.end_time:
                # تبدیل date به datetime با یک زمان پیش‌فرض (مثلاً 00:00:00)
                # و سپس استفاده از replace برای جایگزینی ساعت و دقیقه
                # استفاده از datetime.combine برای ترکیب date با time
                start_datetime_obj = datetime.combine(report.report_date, time_span.start_time)
                end_datetime_obj = datetime.combine(report.report_date, time_span.end_time)

                # اگر ساعت پایان قبل از ساعت شروع بود (مثلاً از ۲۳:۰۰ تا ۰۱:۰۰)، فرض می‌کنیم روز بعد است
                if end_datetime_obj < start_datetime_obj:
                    end_datetime_obj += timedelta(days=1)

                duration = end_datetime_obj - start_datetime_obj
                total_hours_worked += duration

                project_id = report.task.project.id
                project_name = report.task.project.name
                if project_id not in project_hours:
                    project_hours[project_id] = {'name': project_name, 'total_duration': timedelta(0)}
                project_hours[project_id]['total_duration'] += duration

    # ... (ادامه کد محاسبه و ارسال به کانتکست) ...

    total_hours_float = total_hours_worked.total_seconds() / 3600

    aggregated_project_hours = []
    for proj_id, data in project_hours.items():
        aggregated_project_hours.append({
            'name': data['name'],
            'hours': data['total_duration'].total_seconds() / 3600
        })
    aggregated_project_hours = sorted(aggregated_project_hours, key=lambda x: x['hours'], reverse=True)

    context = {
        'reports': reports,
        'form': form,
        'total_hours_worked': total_hours_float,
        'aggregated_project_hours': aggregated_project_hours,
        'num_reports': reports.count(),
        'num_projects_involved': len(aggregated_project_hours),
        'avg_hours_per_report': total_hours_float / reports.count() if reports.count() > 0 else 0,
    }
    return render(request, 'work_report_list.html', context)


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import inlineformset_factory
from django.http import JsonResponse
import json

from .models import WorkReport, Project, Task, WorkTimeSpan, UserGroup # مطمئن شوید همه مدل‌ها را import کرده‌اید
from .forms import WorkReportForm, WorkTimeSpanFormSet, ProjectForm, TaskForm

@login_required
def create_new_report(request):
    report_form = WorkReportForm(user=request.user) # ارسال کاربر برای فیلتر وظایف
    time_span_formset = WorkTimeSpanFormSet()
    project_form = ProjectForm()
    task_form = TaskForm()

    if request.method == 'POST':
        # بررسی اینکه کدام فرم ارسال شده است (از طریق نام دکمه یا فیلد پنهان)
        if 'submit_report' in request.POST:
            report_form = WorkReportForm(request.POST, user=request.user)
            time_span_formset = WorkTimeSpanFormSet(request.POST, instance=WorkReport()) # instance خالی برای فرمست جدید

            if report_form.is_valid() and time_span_formset.is_valid():
                work_report = report_form.save(commit=False)
                work_report.reporter = request.user
                work_report.save()

                time_span_formset.instance = work_report
                time_span_formset.save()

                # messages.success(request, 'گزارش کار با موفقیت ثبت شد.')
                return redirect('work_report_list')
            else:
                # messages.error(request, 'خطا در ثبت گزارش کار. لطفا اطلاعات را بررسی کنید.')
                pass # خطاها در قالب نمایش داده می شوند

        elif 'submit_new_project' in request.POST:
            project_form = ProjectForm(request.POST)
            if project_form.is_valid():
                project = project_form.save(commit=False)
                project.created_by = request.user
                project.save()
                # اگر گروه‌ها انتخاب شده‌اند، آن‌ها را ذخیره کن
                project_form.save_m2m() # برای فیلدهای ManyToMany

                # messages.success(request, f'پروژه "{project.name}" با موفقیت ثبت شد.')
                # پس از ثبت پروژه، ممکن است بخواهید صفحه را رفرش کنید یا کاربر را به صفحه لیست پروژه ها بفرستید
                return redirect('create_new_report') # رفرش صفحه برای استفاده از پروژه جدید
            else:
                # messages.error(request, 'خطا در ثبت پروژه جدید. لطفا اطلاعات را بررسی کنید.')
                pass

        elif 'submit_new_task' in request.POST:
            task_form = TaskForm(request.POST)
            if task_form.is_valid():
                task = task_form.save(commit=False)
                task.created_by = request.user
                task.save()
                task_form.save_m2m() # برای assigned_to
                # messages.success(request, f'وظیفه "{task.title}" با موفقیت ثبت شد.')
                return redirect('create_new_report') # رفرش صفحه برای استفاده از وظیفه جدید
            else:
                # messages.error(request, 'خطا در ثبت وظیفه جدید. لطفا اطلاعات را بررسی کنید.')
                pass

    context = {
        'report_form': report_form,
        'time_span_formset': time_span_formset,
        'project_form': project_form,
        'task_form': task_form,
        'all_projects': Project.objects.all().order_by('name'), # برای دراپ داون پروژه در فرم وظیفه
        'all_users': User.objects.filter(is_active=True).order_by('username'), # برای اختصاص وظیفه
        'user_groups': UserGroup.objects.all().order_by('name'), # برای اختصاص پروژه به گروه
    }
    return render(request, 'create_work_report.html', context)


# ویو AJAX برای دریافت وظایف بر اساس پروژه انتخاب شده (اختیاری)
def load_tasks(request):
    project_id = request.GET.get('project_id')
    tasks = Task.objects.filter(project_id=project_id).order_by('title')
    task_list = [{'id': task.id, 'title': task.title} for task in tasks]
    return JsonResponse(task_list, safe=False)

# ویو AJAX برای دریافت وظایف والد بر اساس پروژه انتخاب شده (اختیاری)
def load_parent_tasks(request):
    project_id = request.GET.get('project_id')
    # فیلتر وظایف والد از همان پروژه
    tasks = Task.objects.filter(project_id=project_id).order_by('title')
    task_list = [{'id': task.id, 'title': task.title} for task in tasks]
    return JsonResponse(task_list, safe=False)
# your_app_name/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction # For atomic operations with formsets
from .forms import WorkReportForm, WorkTimeSpanFormSet
from .models import WorkReport, WorkTimeSpan # Make sure to import your models

@login_required
def edit_report(request, report_id):
    # Retrieve the WorkReport instance to be edited
    report = get_object_or_404(WorkReport, id=report_id)

    # Optional: Add permission check (e.g., only owner or admin can edit)
    # if report.created_by != request.user and not request.user.is_superuser:
    #     # You can raise a 403 error or redirect to an unauthorized page
    #     from django.core.exceptions import PermissionDenied
    #     raise PermissionDenied("You don't have permission to edit this report.")
        # Or simply redirect:
        # return redirect('some_unauthorized_page')


    if request.method == 'POST':
        # Bind the form and formset with POST data and the existing instance
        report_form = WorkReportForm(request.POST, request.FILES, instance=report, user=request.user)
        time_span_formset = WorkTimeSpanFormSet(request.POST, request.FILES, instance=report)

        if report_form.is_valid() and time_span_formset.is_valid():
            with transaction.atomic(): # Ensures both form and formset are saved or none are
                report_form.save()
                time_span_formset.save() # Saves new, updates existing, and deletes marked items

            # You might want to add a success message here
            # from django.contrib import messages
            # messages.success(request, 'گزارش با موفقیت ویرایش شد.')

            return redirect('work_report_list') # Redirect to a relevant page, e.g., dashboard or report detail
    else:
        # For GET request, initialize the form and formset with the existing instance data
        report_form = WorkReportForm(instance=report, user=request.user)
        time_span_formset = WorkTimeSpanFormSet(instance=report)

    context = {
        'report_form': report_form,
        'time_span_formset': time_span_formset,
        'report': report, # Pass the report object to the template, useful for displaying its ID/title
        'is_edit_mode': True, # A flag to indicate we are in edit mode in the template
    }
    return render(request, 'edit_report.html', context)
# your_app_name/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import ExpenseForm # فرم ExpenseForm را ایمپورت کنید
from .models import Expense, Task # مدل‌های لازم را ایمپورت کنید

# ... (سایر ویوهای شما در این فایل) ...
# your_app_name/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import ExpenseForm
from .models import Task, Expense # مطمئن بشید Task و Expense ایمپورت شدن

@login_required
def register_expense(request, task_id): # task_id رو از URL دریافت می‌کنیم
    task = get_object_or_404(Task, id=task_id)

    if request.method == 'POST':
        # هنگام ایجاد فرم، task رو به عنوان instance بهش نمی‌دیم، چون این فرم مربوط به Expense جدیده
        form = ExpenseForm(request.POST, user=request.user, initial={'task': task})
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.task = task # وظیفه رو از URL به Expense اضافه می‌کنیم
            expense.save()
            #messages.success(request, 'هزینه با موفقیت ثبت شد.')
            return redirect('work_report_list') # یا هر صفحه‌ای که مناسبه
    else:
        # برای درخواست GET، فرم رو با مقدار اولیه task ایجاد می‌کنیم
        form = ExpenseForm(user=request.user, initial={'task': task})

    context = {
        'form': form,
        'task': task, # وظیفه رو هم به کانتکست می‌فرستیم تا در HTML استفاده بشه
    }
    return render(request, 'register_expense.html', context)
# your_app_name/views.py

# your_app_name/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import FutureNoteForm # فرم FutureNoteForm را ایمپورت کنید
from .models import FutureNote, Task # مدل‌های لازم را ایمپورت کنید

# ... (سایر ویوهای شما در این فایل) ...

@login_required
def register_future_note(request, task_id): # task_id رو از URL دریافت می‌کنیم
    task = get_object_or_404(Task, id=task_id)

    if request.method == 'POST':
        # هنگام ایجاد فرم، task رو به عنوان initial بهش می‌دیم
        form = FutureNoteForm(request.POST, user=request.user, initial={'task': task})
        if form.is_valid():
            future_note = form.save(commit=False)
            future_note.user = request.user # کاربر لاگین شده را به عنوان ثبت کننده ایده تنظیم می‌کنیم
            future_note.task = task # وظیفه رو از URL به FutureNote اضافه می‌کنیم
            future_note.save()
            # می‌توانید یک پیام موفقیت اضافه کنید:
            # from django.contrib import messages
            # messages.success(request, 'ایده با موفقیت ثبت شد.')
            return redirect('work_report_list') # به صفحه لیست گزارش‌ها یا هر صفحه مناسب دیگر ریدایرکت کنید
    else:
        # برای درخواست GET، فرم را با مقدار اولیه task و user ایجاد می‌کنیم
        form = FutureNoteForm(user=request.user, initial={'task': task})

    context = {
        'form': form,
        'task': task, # وظیفه رو هم به کانتکست می‌فرستیم تا در HTML استفاده بشه
    }
    return render(request, 'register_future_note.html', context)

# your_app_name/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction # برای اطمینان از صحت عملیات ذخیره
from django.http import JsonResponse # برای درخواست‌های AJAX در آینده (اگر پیاده‌سازی شود)

from .forms import HelpRequestForm, HelpRequestMessageForm # فرم‌های جدید
from .models import HelpRequest, HelpRequestMessage, Task # مدل‌های لازم

# ... (سایر ویوهای شما) ...
# your_app_name/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q # برای فیلتر کردن
from .forms import HelpRequestForm
from .models import HelpRequest, Task

# ... (سایر ویوهای شما) ...

@login_required
def submit_help_request(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if request.method == 'POST':
        form = HelpRequestForm(request.POST, user=request.user, initial={'task': task})
        if form.is_valid():
            help_request = form.save(commit=False)
            help_request.requester = request.user
            help_request.task = task
            help_request.save()
            # messages.success(request, 'درخواست کمک با موفقیت ثبت شد. به زودی با شما تماس گرفته می‌شود.')
            return redirect('help_request_chat', help_request_id=help_request.id)
    else:
        form = HelpRequestForm(user=request.user, initial={'task': task})

    # لیست درخواست‌های کمک قبلی را دریافت می‌کنیم
    # اگر کاربر ادمین باشد، همه درخواست‌ها را می‌بیند. در غیر این صورت، فقط درخواست‌های خودش را.
    if request.user.is_superuser:
        previous_help_requests = HelpRequest.objects.all().order_by('-requested_at')
    else:
        previous_help_requests = HelpRequest.objects.filter(requester=request.user).order_by('-requested_at')

    context = {
        'form': form,
        'task': task,
        'previous_help_requests': previous_help_requests, # اضافه کردن لیست درخواست‌های قبلی به کانتکست
    }
    return render(request, 'submit_help_request.html', context)

# ... (ویو help_request_chat بدون تغییر) ...
@login_required
def help_request_chat(request, help_request_id):
    help_request = get_object_or_404(HelpRequest, id=help_request_id)

    # بررسی دسترسی: فقط درخواست‌کننده یا مدیر می‌تواند چت را ببیند
    if help_request.requester != request.user and not request.user.is_superuser:
        # اگر کاربر دسترسی ندارد، می‌توانید او را به صفحه دیگری هدایت کنید یا خطای 403 دهید
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("شما اجازه دسترسی به این درخواست کمک را ندارید.")

    messages = help_request.messages.all() # پیام‌های مربوط به این درخواست کمک

    if request.method == 'POST':
        message_form = HelpRequestMessageForm(request.POST)
        if message_form.is_valid():
            message = message_form.save(commit=False)
            message.help_request = help_request
            message.sender = request.user
            message.save()
            # پس از ارسال پیام، فرم را خالی کرده و دوباره صفحه را بارگذاری می‌کنیم (یا با AJAX)
            return redirect('help_request_chat', help_request_id=help_request.id)
    else:
        message_form = HelpRequestMessageForm()

    context = {
        'help_request': help_request,
        'messages': messages,
        'message_form': message_form,
    }
    return render(request, 'help_request_chat.html', context)

# your_app_name/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test # برای بررسی ادمین بودن
from django.db.models import Q # برای کوئری‌های پیچیده‌تر
from .models import WorkReport # مدل گزارش کار
from .forms import ReportFilterForm # فرم فیلتر

# ... (سایر ویوهای شما) ...

# تابع کمکی برای بررسی اینکه کاربر ادمین است
def is_admin(user):
    return user.is_superuser # یا user.is_staff اگر کاربران استاف هم دسترسی دارند
# your_app_name/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from datetime import timedelta, datetime, time # مطمئن شوید datetime و time هم ایمپورت شده‌اند
from .models import WorkReport, Project, Task, WorkTimeSpan # مطمئن شوید WorkTimeSpan هم ایمپورت شده
from .forms import ReportFilterForm # فرم فیلتر

# تابع کمکی برای بررسی اینکه کاربر ادمین است
def is_admin(user):
    return user.is_superuser # یا user.is_staff اگر کاربران استاف هم دسترسی دارند

@user_passes_test(is_admin) # فقط ادمین‌ها می‌توانند به این ویو دسترسی داشته باشند
def admin_report_view(request):
    reports_queryset = WorkReport.objects.all().order_by('-report_date', '-created_at') # همه گزارش‌ها به صورت پیش‌فرض

    form = ReportFilterForm(request.GET) # از request.GET برای فیلتر کردن استفاده می‌کنیم

    if form.is_valid():
        user = form.cleaned_data.get('user')
        project = form.cleaned_data.get('project')
        start_date_filter = form.cleaned_data.get('start_date')
        end_date_filter = form.cleaned_data.get('end_date')

        if user:
            reports_queryset = reports_queryset.filter(reporter=user)
        if project:
            # گزارش‌ها را بر اساس وظایف مرتبط با پروژه فیلتر می‌کنیم
            reports_queryset = reports_queryset.filter(task__project=project)
        if start_date_filter:
            reports_queryset = reports_queryset.filter(report_date__gte=start_date_filter) # Greater than or equal
        if end_date_filter:
            reports_queryset = reports_queryset.filter(report_date__lte=end_date_filter)

    reports = reports_queryset # گزارش‌های فیلتر شده

    # --- محاسبه گزارش‌های جمع‌آوری شده ---
    total_hours_worked = timedelta(0)
    project_hours = {} # {project_id: {'name': 'Project Name', 'total_duration': timedelta}}

    for report in reports:
        for time_span in report.time_spans.all():
            if time_span.start_time and time_span.end_time:
                # تبدیل date به datetime با یک زمان پیش‌فرض (مثلاً 00:00:00)
                # استفاده از datetime.combine برای ترکیب date با time
                start_datetime_obj = datetime.combine(report.report_date, time_span.start_time)
                end_datetime_obj = datetime.combine(report.report_date, time_span.end_time)

                # اگر ساعت پایان قبل از ساعت شروع بود (مثلاً از ۲۳:۰۰ تا ۰۱:۰۰)، فرض می‌کنیم روز بعد است
                if end_datetime_obj < start_datetime_obj:
                    end_datetime_obj += timedelta(days=1)

                duration = end_datetime_obj - start_datetime_obj
                total_hours_worked += duration

                project_id = report.task.project.id
                project_name = report.task.project.name
                if project_id not in project_hours:
                    project_hours[project_id] = {'name': project_name, 'total_duration': timedelta(0)}
                project_hours[project_id]['total_duration'] += duration

    # تبدیل timedelta به ساعت
    total_hours_float = total_hours_worked.total_seconds() / 3600

    aggregated_project_hours = []
    for proj_id, data in project_hours.items():
        aggregated_project_hours.append({
            'name': data['name'],
            'hours': data['total_duration'].total_seconds() / 3600
        })
    # مرتب‌سازی پروژه‌ها بر اساس میزان ساعت کار
    aggregated_project_hours = sorted(aggregated_project_hours, key=lambda x: x['hours'], reverse=True)


    context = {
        'form': form,
        'reports': reports,
        'is_admin_view': True,
        'total_hours_worked': total_hours_float, # برای نمایش در خلاصه
        'aggregated_project_hours': aggregated_project_hours, # برای نمایش در خلاصه
        'num_reports': reports.count(), # تعداد گزارش‌های فیلتر شده
        'num_projects_involved': len(aggregated_project_hours), # تعداد پروژه‌هایی که در این بازه زمانی گزارش داشتند
        'avg_hours_per_report': total_hours_float / reports.count() if reports.count() > 0 else 0, # میانگین ساعت کار در هر گزارش
    }
    return render(request, 'admin_report_view.html', context) # نام تمپلیت را به app/templates/your_app_name/admin_report_view.html تغییر دادم





from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import When,Subquery, Case, F, OuterRef # اصلاح: ایمپورت مستقیم Subquery, Case, F و OuterRef
from django.utils import timezone # برای استفاده از timezone.now() و توابع زمان
from django.urls import reverse # این خط را اضافه کنید

# حتماً مدل‌های زیر را از models.py خود import کنید:
from .models import HelpRequest, HelpRequestMessage, Task, Notification
# و فرم مربوطه را از forms.py:
from .forms import HelpRequestMessageForm

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Subquery, Case, F, OuterRef, When, DateTimeField # اصلاح: اضافه کردن DateTimeField
from django.urls import reverse
from django.utils import timezone # این برای timezone.now() لازم است، نه DateTimeField


# حتماً مدل‌های زیر را از models.py خود import کنید:
from .models import HelpRequest, HelpRequestMessage, Task, Notification
# و فرم مربوطه را از forms.py:
from .forms import HelpRequestMessageForm

# یک تابع کمکی برای بررسی اینکه کاربر مدیر است
def is_manager(user):
    # این تابع را با منطق واقعی گروه های کاربری خود جایگزین کنید.
    # به عنوان مثال، اگر کاربر is_staff باشد یا عضو گروه "مدیران" باشد.
    if user.is_authenticated: # اطمینان حاصل کنید که کاربر لاگین کرده است
        return user.is_staff or user.groups.filter(name='مدیران').exists()
    return False # اگر کاربر لاگین نکرده، مدیر نیست



@login_required
@user_passes_test(is_manager) # اطمینان از اینکه فقط مدیران به این صفحه دسترسی دارند
def admin_help_requests_chat_list(request):
    """
    نمایش لیست درخواست‌های کمک برای مدیران، مرتب شده بر اساس آخرین فعالیت.
    امکان فیلتر کردن بر اساس وضعیت (حل شده / حل نشده) نیز وجود دارد.
    """
    help_requests = HelpRequest.objects.annotate(
        last_message_time=Subquery( # استفاده از Subquery ایمپورت شده
            HelpRequestMessage.objects.filter(help_request=OuterRef('pk')) # استفاده از OuterRef ایمپورت شده
            .order_by('-sent_at')
            .values('sent_at')[:1]
        )
    ).order_by(
        Case( # استفاده از Case ایمپورت شده
            When(last_message_time__isnull=True, then=F('requested_at')), # استفاده از F ایمپورت شده
            default=F('last_message_time'), # استفاده از F ایمپورت شده
            output_field=DateTimeField() # اصلاح: استفاده از DateTimeField ایمپورت شده (بدون timezone.)
        )
    ).reverse() # برای نمایش جدیدترین ها ابتدا

    # فیلتر کردن بر اساس وضعیت
    status_filter = request.GET.get('status')
    if status_filter == 'resolved':
        help_requests = help_requests.filter(is_resolved=True)
    elif status_filter == 'unresolved':
        help_requests = help_requests.filter(is_resolved=False)

    return render(request, 'admin_panel/admin_help_requests_chat_list.html', {
        'help_requests': help_requests,
        'status_filter': status_filter
    })

# ... (ادامه توابع admin_help_request_chat_detail, mark_help_request_resolved, mark_help_request_unresolved که قبلا صحیح بودند)
@login_required
@user_passes_test(is_manager)
def admin_help_request_chat_detail(request, help_request_id):
    """
    نمایش جزئیات یک درخواست کمک و پیام‌های چت آن.
    مدیر می‌تواند به درخواست پاسخ دهد و وضعیت آن را تغییر دهد.
    """
    help_request = get_object_or_404(HelpRequest, id=help_request_id)
    messages = help_request.messages.all().order_by('sent_at')

    if request.method == 'POST':
        form = HelpRequestMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.help_request = help_request
            message.sender = request.user # مدیر پاسخ دهنده است
            message.save()

            # اگر مدیری به یک درخواست "حل شده" پاسخ دهد، وضعیت آن به "حل نشده" تغییر کند
            if help_request.is_resolved:
                help_request.is_resolved = False
                help_request.resolved_by = None
                help_request.resolved_at = None
                help_request.save()

            # ایجاد یک اعلان برای درخواست‌کننده اصلی
            Notification.objects.create(
                recipient=help_request.requester,
                message=f"پاسخی به درخواست کمک شما در وظیفه '{help_request.task.title}' داده شد.",
                link=reverse('help_request_chat', args=[help_request.id]),
                notification_type='new_help_request' # می‌توانید نوع اعلان جدیدی برای پاسخ ایجاد کنید
            )

            return redirect('admin_help_request_chat_detail', help_request_id=help_request.id)
    else:
        form = HelpRequestMessageForm()

    return render(request, 'admin_panel/admin_help_request_chat_detail.html', {
        'help_request': help_request,
        'messages': messages,
        'form': form
    })

@login_required
@user_passes_test(is_manager)
def mark_help_request_resolved(request, help_request_id):
    """
    یک درخواست کمک را به عنوان 'حل شده' علامت‌گذاری می‌کند.
    """
    help_request = get_object_or_404(HelpRequest, id=help_request_id)
    if request.method == 'POST':
        help_request.is_resolved = True
        help_request.resolved_by = request.user
        help_request.resolved_at = timezone.now()
        help_request.save()

        # ایجاد اعلان برای درخواست‌کننده که مشکلش حل شده است
        Notification.objects.create(
            recipient=help_request.requester,
            message=f"درخواست کمک شما در وظیفه '{help_request.task.title}' حل شد.",
            link=reverse('help_request_chat', args=[help_request.id]),
            notification_type='help_request_resolved'
        )

        return redirect('admin_help_requests_chat_list')
    return redirect('admin_help_request_chat_detail', help_request_id=help_request.id)

@login_required
@user_passes_test(is_manager)
def mark_help_request_unresolved(request, help_request_id):
    """
    یک درخواست کمک را به عنوان 'حل نشده' (باز کردن مجدد) علامت‌گذاری می‌کند.
    """
    help_request = get_object_or_404(HelpRequest, id=help_request_id)
    if request.method == 'POST':
        help_request.is_resolved = False
        help_request.resolved_by = None
        help_request.resolved_at = None
        help_request.save()

        # ایجاد اعلان برای درخواست‌کننده در صورت نیاز
        Notification.objects.create(
            recipient=help_request.requester,
            message=f"درخواست کمک شما در وظیفه '{help_request.task.title}' به وضعیت 'در حال بررسی' تغییر یافت.",
            link=reverse('help_request_chat', args=[help_request.id]),
            notification_type='help_request_unresolved'
        )

        return redirect('admin_help_requests_chat_list')
    return redirect('admin_help_request_chat_detail', help_request_id=help_request.id)