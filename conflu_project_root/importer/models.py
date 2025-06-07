from django.db import models
import uuid
from pages.models import PageVersion

class FallbackMacro(models.Model):
    page_version = models.ForeignKey(
        PageVersion,
        on_delete=models.CASCADE,
        related_name='fallback_macros'
    )
    macro_name = models.CharField(max_length=100)
    raw_macro_content = models.TextField()
    import_notes = models.TextField(blank=True, null=True)
    placeholder_id_in_content = models.UUIDField(null=True, blank=True, help_text="Client-side generated UUID for ProseMirror node", default=uuid.uuid4)

    def __str__(self):
        return f"Fallback for {self.macro_name} in {self.page_version.page.title} v{self.page_version.version_number}"

    class Meta:
        verbose_name = "Fallback Macro"
        verbose_name_plural = "Fallback Macros"
