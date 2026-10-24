from django.db import models


class PendingAction(models.Model):
    """UI-facing approval queue for reshuffles, bookings, and drafted emails."""

    class ActionType(models.TextChoices):
        BOOK_MEETING = "book_meeting", "Book meeting"
        RESCHEDULE = "reschedule", "Reschedule"
        SEND_EMAIL = "send_email", "Send email"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXECUTED = "executed", "Executed"
        FAILED = "failed", "Failed"

    action_type = models.CharField(max_length=32, choices=ActionType.choices)
    title = models.CharField(max_length=255)
    summary = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    result = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action_type}:{self.title} ({self.status})"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "title": self.title,
            "summary": self.summary,
            "payload": self.payload,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
