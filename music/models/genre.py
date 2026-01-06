from django.db import models
from common.models import BaseModel


class Genre(BaseModel):
    """
    Represents a song genre.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "genres"
        ordering = ["name"]

    def __str__(self):
        return self.name
