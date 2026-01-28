from django.core.management.base import BaseCommand
from django.db import transaction
from music.models.genre import Genre

class Command(BaseCommand):
    help = 'Seeds the database with 15-20 popular genres'

    @transaction.atomic
    def handle(self, *args, **options):
        genres = [
            "Pop",
            "Rock",
            "Hip Hop",
            "R&B",
            "Electronic",
            "Jazz",
            "Classical",
            "Country",
            "Folk",
            "Blues",
            "Reggae",
            "Metal",
            "Punk",
            "Indie",
            "Soul",
            "Funk",
            "Latin",
            "World Music",
            "Bollywood",
            "EDM",
        ]

        created_count = 0
        skipped_count = 0
        
        for name in genres:
            genre, created = Genre.objects.get_or_create(name=name)
            if created:
                created_count += 1
            else:
                skipped_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {len(genres)} genres. '
                f'Created: {created_count}, Already exists: {skipped_count}'
            )
        )
