from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from common.models import SoftDeleteModel
from common.enums import SongVisibility
from common.managers import SoftDeleteManager
from common.constants import MIN_RELEASE_YEAR
from users.models import User
from .genre_models import Genre



class Song(SoftDeleteModel):
    """Song model."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="songs")
    
    visibility = models.CharField(
        max_length=20,
        choices=SongVisibility.choices,
        default=SongVisibility.GLOBAL
    )
    
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='songs',
        null=True,
        blank=True
    )
    
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT, related_name="songs")

    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    album = models.CharField(max_length=255, blank=True)
    duration = models.PositiveSmallIntegerField()
    release_year = models.PositiveSmallIntegerField()

    objects = SoftDeleteManager()

    class Meta:
        db_table = "songs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['tenant', 'visibility']),
        ]
    
    def clean(self):
        """Validate release year."""
        current_year = timezone.now().year
        
        if self.release_year > current_year:
            raise ValidationError(
                f"Release year cannot be in the future. (Current year: {current_year})"
            )
        if self.release_year < MIN_RELEASE_YEAR:
            raise ValidationError(
                f"Release year cannot be less than {MIN_RELEASE_YEAR}. (Current year: {current_year})"
            )
    
    def save(self, *args, **kwargs):
        """Save with validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} by {self.artist}"
