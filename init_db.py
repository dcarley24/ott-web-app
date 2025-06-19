import sqlite3
import subprocess
import os

DB_PATH = 'database.db'  # adjust if needed

def get_duration(file_path):
    """Return video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries',
             'format=duration', '-of',
             'default=noprint_wrappers=1:nokey=1', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        output = result.stdout.decode().strip()
        return int(float(output))
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return None

def update_durations():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Ensure the duration column exists
    try:
        c.execute("ALTER TABLE videos ADD COLUMN duration INTEGER")
        print("ℹ️  'duration' column added to 'videos' table.")
    except sqlite3.OperationalError:
        print("✅ 'duration' column already exists.")

    # Get videos without duration
    c.execute("SELECT id, file_path FROM videos WHERE duration IS NULL OR duration = 0")
    videos = c.fetchall()

    for vid_id, file_path in videos:
        if not file_path or not os.path.isfile(file_path):
            print(f"⚠️  Skipping missing file: {file_path}")
            continue

        duration = get_duration(file_path)
        if duration:
            print(f"🕒 {file_path} → {duration}s")
            c.execute("UPDATE videos SET duration = ? WHERE id = ?", (duration, vid_id))
        else:
            print(f"❌ Failed to get duration for {file_path}")

    conn.commit()
    conn.close()
    print("✅ All durations updated.")

if __name__ == "__main__":
    update_durations()
