from django.contrib import admin
from django.http import HttpResponse
from .excel import generate_applications_excel
from .models import (
    Application,
    AuditLog,
    Category,
    Participant,
    Project,
    ProjectFile,
    TelegramAdmin,
    TelegramSubscriber,
)


class FileInline(admin.TabularInline):
    model = ProjectFile
    extra = 0
    fields = ("kind", "file", "original_name", "file_size", "uploaded_at")
    readonly_fields = ("original_name", "file_size", "uploaded_at")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "icon")
    list_editable = ("order", "icon")


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("full_name", "group", "phone", "telegram_username", "study_direction", "created_at")
    search_fields = ("first_name", "last_name", "middle_name", "phone", "group", "telegram_username")
    list_filter = ("group", "study_direction")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "participant", "category", "link")
    list_filter = ("category",)
    search_fields = ("title", "summary", "participant__last_name", "participant__first_name")
    inlines = [FileInline]


@admin.action(description="Tanlangan arizalarni Excel (.xlsx) ga eksport qilish")
def export_selected_to_excel(modeladmin, request, queryset):
    excel_io = generate_applications_excel(queryset)
    response = HttpResponse(
        excel_io.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Tanlangan_Startup_Arizalar_2026.xlsx"'
    return response


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("number", "get_participant_name", "get_project_title", "get_category", "status", "score", "created_at")
    list_filter = ("status", "participant__project__category", "created_at")
    search_fields = (
        "number",
        "participant__last_name",
        "participant__first_name",
        "participant__phone",
        "participant__group",
        "participant__project__title"
    )
    actions = [export_selected_to_excel]
    readonly_fields = ("number", "created_at", "updated_at")

    @admin.display(description="Ishtirokchi")
    def get_participant_name(self, obj):
        return obj.participant.full_name()

    @admin.display(description="Loyiha")
    def get_project_title(self, obj):
        return getattr(obj.participant, "project", None)

    @admin.display(description="Yo'nalish")
    def get_category(self, obj):
        pr = getattr(obj.participant, "project", None)
        return pr.category.name if pr and pr.category else "-"


@admin.register(TelegramAdmin)
class TelegramAdminAdmin(admin.ModelAdmin):
    list_display = ("chat_id", "username", "full_name", "notify_on_application", "is_active", "created_at")
    list_editable = ("notify_on_application", "is_active")
    search_fields = ("username", "full_name", "chat_id")


@admin.register(TelegramSubscriber)
class TelegramSubscriberAdmin(admin.ModelAdmin):
    list_display = ("chat_id", "username", "first_name", "created_at")
    search_fields = ("username", "first_name", "chat_id")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "target", "ip", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("target", "details", "ip")
    readonly_fields = ("user", "action", "target", "details", "ip", "created_at")
