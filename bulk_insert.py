import os
import shutil
import uuid
# MODIFICATION: Import 'video_tags' to fix the NameError
from app import app, db, Video, Tag, video_tags

# --- Configuration ---
VIDEO_SOURCE_FILE = "BigBuckBunny_320x180.mp4"
POSTER_SOURCE_FILE = "BigBuckBunny_320x180.jpg"

VIDEO_SOURCE_PATH = os.path.join('uploads', 'videos', VIDEO_SOURCE_FILE)
POSTER_SOURCE_PATH = os.path.join('uploads', 'posters', POSTER_SOURCE_FILE)

VIDEO_FOLDER = os.path.join('uploads', 'videos')
POSTER_FOLDER = os.path.join('uploads', 'posters')

TITLE_BASE = "Big Buck Bunny Clone"
DESCRIPTION = "Cloned for testing UI layouts and tag filtering."
VIDEO_DURATION_MINUTES = 5

def create_initial_tags():
    """Ensures the necessary tags exist in the database."""
    print("Checking for initial tags...")
    required_tags = ["action", "comedy", "drama", "sci-fi", "featured", "movie", "series", "special"]
    for tag_name in required_tags:
        existing_tag = Tag.query.filter_by(name=tag_name).first()
        if not existing_tag:
            new_tag = Tag(name=tag_name)
            db.session.add(new_tag)
            print(f"Creating tag: {tag_name}")
    db.session.commit()
    print("Tags are set up.")

def main():
    """Main function to clear and repopulate the database."""
    with app.app_context():
        print("Clearing existing video and tag data...")
        # This now works because video_tags is imported
        db.session.query(video_tags).delete()
        db.session.query(Video).delete()
        db.session.query(Tag).delete()
        db.session.commit()

        create_initial_tags()

        tag_map = {tag.name: tag for tag in Tag.query.all()}

        if not os.path.exists(VIDEO_SOURCE_PATH):
            print(f"ERROR: Source video not found at {VIDEO_SOURCE_PATH}")
            return
        if not os.path.exists(POSTER_SOURCE_PATH):
            print(f"ERROR: Source poster not found at {POSTER_SOURCE_PATH}")
            return

        print("Inserting 15 new videos...")
        for i in range(15):
            video_filename = f"{uuid.uuid4().hex}_{VIDEO_SOURCE_FILE}"
            poster_filename = f"{uuid.uuid4().hex}_{POSTER_SOURCE_FILE}"

            video_dest = os.path.join(VIDEO_FOLDER, video_filename)
            poster_dest = os.path.join(POSTER_FOLDER, poster_filename)

            shutil.copyfile(VIDEO_SOURCE_PATH, video_dest)
            shutil.copyfile(POSTER_SOURCE_PATH, poster_dest)

            new_video = Video(
                title=f"{TITLE_BASE} #{i+1}",
                description=DESCRIPTION,
                file_path=os.path.join('videos', video_filename),
                poster_path=os.path.join('posters', poster_filename),
                duration_seconds=VIDEO_DURATION_MINUTES * 60,
                content_type='movie' if i % 2 == 0 else 'series'
            )

            if i < 5:
                new_video.tags.append(tag_map["action"])
                new_video.tags.append(tag_map["featured"])
            elif i < 10:
                new_video.tags.append(tag_map["comedy"])
            else:
                new_video.tags.append(tag_map["drama"])

            db.session.add(new_video)

        db.session.commit()
        print("✅ Inserted 15 videos successfully.")

if __name__ == "__main__":
    main()
