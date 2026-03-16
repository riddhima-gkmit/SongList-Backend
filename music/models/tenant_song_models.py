"""TenantSong model."""
from django.db import models
from common.models import SoftDeleteModel
from common.managers import SoftDeleteManager


class TenantSong(SoftDeleteModel):
    """Links songs to tenants."""
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='tenant_songs'
    )
    
    song = models.ForeignKey(
        'music.Song',
        on_delete=models.CASCADE,
        related_name='tenant_links'
    )
    
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager()
    
    class Meta:
        db_table = 'tenant_songs'
        verbose_name = 'Tenant Song Link'
        verbose_name_plural = 'Tenant Song Links'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'song'],
                name='unique_song_per_tenant'
            )
        ]
        indexes = [
            models.Index(fields=['tenant', 'song']),
            models.Index(fields=['tenant', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.song.title} → {self.tenant.name}"
