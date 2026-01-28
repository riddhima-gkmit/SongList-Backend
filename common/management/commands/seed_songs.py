import random
from django.core.management.base import BaseCommand
from django.db import transaction
from music.models.song import Song
from music.models.genre import Genre
from users.models import User
from common.enums import UserRole, SongVisibility
from common.constants import MIN_RELEASE_YEAR
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seeds the database with 50 Bollywood songs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of songs to create (default: 50)',
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        count = kwargs.get('count', 50)
        
        # Get users (prefer admins, fallback to listeners)
        users = User.objects.filter(role=UserRole.SUPER_ADMIN)
        
        genres = list(Genre.objects.all())

        if not users:
            self.stdout.write(self.style.ERROR('No users found. Please run seed_users or seed_admins first.'))
            return

        if not genres:
            self.stdout.write(self.style.ERROR('No genres found. Please run seed_genres first.'))
            return

        sample_songs = [
            {"title": "Chaiyya Chaiyya", "artist": "Sukhwinder Singh, Sapna Awasthi", "album": "Dil Se..", "year": 1998, "duration": 375},
            {"title": "Kal Ho Naa Ho", "artist": "Sonu Nigam", "album": "Kal Ho Naa Ho", "year": 2003, "duration": 321},
            {"title": "Tum Hi Ho", "artist": "Arijit Singh", "album": "Aashiqui 2", "year": 2013, "duration": 262},
            {"title": "Kabira", "artist": "Tochi Raina, Rekha Bhardwaj", "album": "Yeh Jawaani Hai Deewani", "year": 2013, "duration": 223},
            {"title": "Pee Loon", "artist": "Mohit Chauhan", "album": "Once Upon a Time in Mumbaai", "year": 2010, "duration": 288},
            {"title": "Jai Ho", "artist": "A.R. Rahman", "album": "Slumdog Millionaire", "year": 2008, "duration": 319},
            {"title": "Senorita", "artist": "Farhan Akhtar, Hrithik Roshan, Abhay Deol", "album": "Zindagi Na Milegi Dobara", "year": 2011, "duration": 231},
            {"title": "Tujh Mein Rab Dikhta Hai", "artist": "Roop Kumar Rathod", "album": "Rab Ne Bana Di Jodi", "year": 2008, "duration": 281},
            {"title": "Tere Bina", "artist": "A.R. Rahman, Chinmayi", "album": "Guru", "year": 2007, "duration": 305},
            {"title": "Agar Tum Saath Ho", "artist": "Alka Yagnik, Arijit Singh", "album": "Tamasha", "year": 2015, "duration": 341},
            {"title": "Raabta", "artist": "Arijit Singh", "album": "Agent Vinod", "year": 2012, "duration": 243},
            {"title": "Kun Faya Kun", "artist": "A.R. Rahman, Javed Ali, Mohit Chauhan", "album": "Rockstar", "year": 2011, "duration": 473},
            {"title": "Dil Chahta Hai", "artist": "Shankar Mahadevan", "album": "Dil Chahta Hai", "year": 2001, "duration": 310},
            {"title": "Koi Kahe Kehta Rahe", "artist": "Shankar Mahadevan, Shaan, KK", "album": "Dil Chahta Hai", "year": 2001, "duration": 344},
            {"title": "Zara Sa", "artist": "KK", "album": "Jannat", "year": 2008, "duration": 300},
            {"title": "Tadap Tadap", "artist": "KK", "album": "Hum Dil De Chuke Sanam", "year": 1999, "duration": 396},
            {"title": "Mitwa", "artist": "Shafqat Amanat Ali", "album": "Kabhi Alvida Naa Kehna", "year": 2006, "duration": 381},
            {"title": "Channa Mereya", "artist": "Arijit Singh", "album": "Ae Dil Hai Mushkil", "year": 2016, "duration": 289},
            {"title": "Ae Dil Hai Mushkil", "artist": "Arijit Singh", "album": "Ae Dil Hai Mushkil", "year": 2016, "duration": 268},
            {"title": "Tera Ban Jaunga", "artist": "Akhil Sachdeva, Tulsi Kumar", "album": "Kabir Singh", "year": 2019, "duration": 236},
            {"title": "Bekhayali", "artist": "Sachet Tandon", "album": "Kabir Singh", "year": 2019, "duration": 371},
            {"title": "Ghungroo", "artist": "Arijit Singh, Shilpa Rao", "album": "War", "year": 2019, "duration": 302},
            {"title": "Nashe Si Chadh Gayi", "artist": "Arijit Singh", "album": "Befikre", "year": 2016, "duration": 234},
            {"title": "Kala Chashma", "artist": "Amar Arshi, Badshah, Neha Kakkar", "album": "Baar Baar Dekho", "year": 2016, "duration": 187},
            {"title": "London Thumakda", "artist": "Labh Janjua, Sonu Kakkar, Neha Kakkar", "album": "Queen", "year": 2014, "duration": 240},
            {"title": "Galliyan", "artist": "Ankit Tiwari", "album": "Ek Villain", "year": 2014, "duration": 340},
            {"title": "Samjhawan", "artist": "Arijit Singh, Shreya Ghoshal", "album": "Humpty Sharma Ki Dulhania", "year": 2014, "duration": 269},
            {"title": "Gerua", "artist": "Arijit Singh, Antara Mitra", "album": "Dilwale", "year": 2015, "duration": 345},
            {"title": "Janam Janam", "artist": "Arijit Singh, Antara Mitra", "album": "Dilwale", "year": 2015, "duration": 237},
            {"title": "Deewani Mastani", "artist": "Shreya Ghoshal", "album": "Bajirao Mastani", "year": 2015, "duration": 340},
            {"title": "Malhari", "artist": "Vishal Dadlani", "album": "Bajirao Mastani", "year": 2015, "duration": 244},
            {"title": "Kar Gayi Chull", "artist": "Badshah, Fazilpuria, Sukriti Kakar, Neha Kakkar", "album": "Kapoor & Sons", "year": 2016, "duration": 187},
            {"title": "Bolna", "artist": "Arijit Singh, Asees Kaur", "album": "Kapoor & Sons", "year": 2016, "duration": 213},
            {"title": "Iktara", "artist": "Kavita Seth", "album": "Wake Up Sid", "year": 2009, "duration": 253},
            {"title": "Give Me Some Sunshine", "artist": "Suraj Jagan, Sharman Joshi", "album": "3 Idiots", "year": 2009, "duration": 247},
            {"title": "Zoobi Doobi", "artist": "Sonu Nigam, Shreya Ghoshal", "album": "3 Idiots", "year": 2009, "duration": 248},
            {"title": "Beintihaan", "artist": "Atif Aslam, Sunidhi Chauhan", "album": "Race 2", "year": 2013, "duration": 290},
            {"title": "Tera Hone Laga Hoon", "artist": "Atif Aslam, Alisha Chinai", "album": "Ajab Prem Ki Ghazab Kahani", "year": 2009, "duration": 300},
            {"title": "Tu Jaane Na", "artist": "Atif Aslam", "album": "Ajab Prem Ki Ghazab Kahani", "year": 2009, "duration": 337},
            {"title": "Pehli Nazar Mein", "artist": "Atif Aslam", "album": "Race", "year": 2008, "duration": 312},
            {"title": "Kuch Kuch Hota Hai", "artist": "Udit Narayan, Alka Yagnik", "album": "Kuch Kuch Hota Hai", "year": 1998, "duration": 296},
            {"title": "Tujhe Dekha To", "artist": "Kumar Sanu, Lata Mangeshkar", "album": "Dilwale Dulhania Le Jayenge", "year": 1995, "duration": 302},
            {"title": "Mehndi Laga Ke Rakhna", "artist": "Udit Narayan, Lata Mangeshkar", "album": "Dilwale Dulhania Le Jayenge", "year": 1995, "duration": 290},
            {"title": "Chhalka Chhalka Re", "artist": "Richa Sharma", "album": "Saathiya", "year": 2002, "duration": 367},
            {"title": "O Humdum Suniyo Re", "artist": "KK, Shaan, Kunal Ganjawala", "album": "Saathiya", "year": 2002, "duration": 237},
            {"title": "Roobaroo", "artist": "A.R. Rahman, Naresh Iyer", "album": "Rang De Basanti", "year": 2006, "duration": 283},
            {"title": "Masti Ki Paathshaala", "artist": "Naresh Iyer, Mohammed Aslam", "album": "Rang De Basanti", "year": 2006, "duration": 220},
            {"title": "Yunhi Chala Chal", "artist": "Udit Narayan, Hariharan, Kailash Kher", "album": "Swades", "year": 2004, "duration": 448},
            {"title": "Yeh Jo Des Hai Tera", "artist": "A.R. Rahman", "album": "Swades", "year": 2004, "duration": 388},
            {"title": "Desi Girl", "artist": "Shankar Mahadevan, Sunidhi Chauhan, Vishal Dadlani", "album": "Dostana", "year": 2008, "duration": 306},
            {"title": "Maa Da Laadla", "artist": "Saleem", "album": "Dostana", "year": 2008, "duration": 245},
        ]

        created_count = 0
        skipped_count = 0

        self.stdout.write(f'Creating {len(sample_songs)} songs...')
        
        for song_data in sample_songs:
            # Check if song already exists
            if Song.objects.filter(title__iexact=song_data["title"], artist__iexact=song_data["artist"]).exists():
                skipped_count += 1
                continue
            
            # Pick random user and genre
            user = random.choice(users)
            genre = random.choice(genres)
            
            # Create only GLOBAL songs (no tenant required)
            tenant = None
            visibility = SongVisibility.GLOBAL

            try:
                Song.objects.create(
                    user=user,
                    genre=genre,
                    title=song_data["title"],
                    artist=song_data["artist"],
                    album=song_data["album"],
                    release_year=song_data["year"],
                    duration=song_data["duration"],
                    tenant=tenant,
                    visibility=visibility,
                )
                created_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating song "{song_data["title"]}": {str(e)}'))
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully processed {count} songs.'))
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
