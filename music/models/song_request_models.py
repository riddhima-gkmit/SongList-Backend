"""SongRequest model."""
from django.db import models
from django.core.validators import URLValidator
from django.utils import timezone
from common.models import SoftDeleteModel
from common.managers import SoftDeleteManager
from common.enums import RequestStatus


class SongRequest(SoftDeleteModel):
    """Users request songs."""
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='song_requests'
    )
    
    requester = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='song_requests'
    )
    
    song_title = models.CharField(max_length=255)
    artist_name = models.CharField(max_length=255)
    album_name = models.CharField(max_length=255, blank=True)
    additional_notes = models.TextField(blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING
    )
    
    reviewed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_song_requests'
    )
    
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    fulfilled_song = models.ForeignKey(
        'music.Song',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fulfilled_requests'
    )
    
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        db_table = 'song_requests'
        verbose_name = 'Song Request'
        verbose_name_plural = 'Song Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['tenant', 'created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['song_title', 'tenant'],
                name='unique_song_request_per_user_tenant'
            ),
        ]
    
    def __str__(self):
        return f"{self.song_title} by {self.artist_name} ({self.get_status_display()})"
    
    def approve(self, admin_user):
        """Approve request."""
        self.status = RequestStatus.APPROVED
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.rejection_reason = ""
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason'])
    
    def reject(self, admin_user, reason):
        """Reject request."""
        self.status = RequestStatus.REJECTED
        self.reviewed_by = admin_user
        self.rejection_reason = reason
        self.reviewed_at = timezone.now()
        self.save(update_fields=['status', 'reviewed_by', 'rejection_reason', 'reviewed_at'])
    
    def fulfill(self, song):
        """Fulfill request."""
        self.status = RequestStatus.FULFILLED
        self.fulfilled_song = song
        self.fulfilled_at = timezone.now()
        self.save(update_fields=['status', 'fulfilled_song', 'fulfilled_at'])
