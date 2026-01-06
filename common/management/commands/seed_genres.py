from django.core.management.base import BaseCommand
from django.db import transaction
from music.models.genre import Genre

class Command(BaseCommand):
    help = 'Seeds the database with a comprehensive list of genres'

    @transaction.atomic
    def handle(self, *args, **options):
        genres = [
            # Popular / Mainstream
            "Pop",
            "Rock",
            "Hip Hop",
            "Rap",
            "R&B",
            "Electronic",
            "Dance",
            "Indie",

            # Rock Subgenres
            "Classic Rock",
            "Alternative Rock",
            "Indie Rock",
            "Hard Rock",
            "Punk Rock",
            "Metal",
            "Heavy Metal",
            "Death Metal",
            "Black Metal",
            "Progressive Rock",
            "Psychedelic Rock",
            "Grunge",

            # Hip Hop / Rap Subgenres
            "Old School Hip Hop",
            "Trap",
            "Drill",
            "Boom Bap",
            "Gangsta Rap",
            "Conscious Hip Hop",
            "Lo-fi Hip Hop",

            # Electronic / EDM
            "EDM",
            "House",
            "Deep House",
            "Techno",
            "Trance",
            "Dubstep",
            "Drum and Bass",
            "Electro",
            "Ambient",
            "Synthwave",

            # R&B / Soul / Funk
            "Soul",
            "Neo Soul",
            "Funk",
            "Contemporary R&B",
            "Motown",

            # Jazz & Blues
            "Jazz",
            "Smooth Jazz",
            "Bebop",
            "Swing",
            "Fusion",
            "Blues",
            "Delta Blues",

            # Classical & Instrumental
            "Classical",
            "Baroque",
            "Romantic",
            "Opera",
            "Symphony",
            "Chamber Music",
            "Instrumental",
            "Piano",
            "Violin",

            # Country / Folk
            "Country",
            "Folk",
            "Bluegrass",
            "Americana",

            # World / Regional
            "World Music",
            "Latin",
            "Salsa",
            "Reggaeton",
            "Bachata",
            "Flamenco",
            "Afrobeat",
            "K-Pop",
            "J-Pop",
            "Bollywood",
            "Celtic",

            # Reggae & Related
            "Reggae",
            "Dub",
            "Ska",

            # Chill / Mood
            "Chill",
            "Chillhop",
            "Lo-fi",
            "Study Beats",
            "Sleep",
            "Meditation",
            "Acoustic",
            "Relaxing",

            # Other / Media
            "Soundtrack",
            "Film Score",
            "Game Music",
            "Gospel",
            "Christian",
            "Emo",
            "Punk",
            "Experimental",
        ]

        created_count = 0
        for name in genres:
            genre, created = Genre.objects.get_or_create(name=name)
            if created:
                created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully processed genres. Created {created_count} new entries.'))
