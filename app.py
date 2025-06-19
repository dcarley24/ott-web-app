import os
import random
import uuid
from datetime import datetime, timedelta

from flask import (Flask, abort, flash, jsonify, redirect,
                   render_template, request, send_from_directory,
                   url_for)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc

app = Flask(__name__)

# --- Configuration ---
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['POSTER_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'posters')
app.config['VIDEO_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'videos')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ott_platform.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

# --- Ensure directories exist ---
os.makedirs(app.config['POSTER_FOLDER'], exist_ok=True)
os.makedirs(app.config['VIDEO_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# --- Database Models ---

video_tags = db.Table('video_tags',
    db.Column('video_id', db.Integer, db.ForeignKey('videos.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

class Video(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(300), nullable=False)
    poster_path = db.Column(db.String(300), nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True, default=0)
    content_type = db.Column(db.String(50), default='movie')
    tags = db.relationship('Tag', secondary=video_tags, backref=db.backref('videos', lazy='dynamic'))

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Channel(db.Model):
    __tablename__ = 'channels'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    logo_path = db.Column(db.String(300), nullable=True)
    channel_type = db.Column(db.String(50), nullable=False, default='manual')
    rule_tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), nullable=True)
    rule_tag = db.relationship('Tag', foreign_keys=[rule_tag_id])

class ChannelSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=True)
    ad_id = db.Column(db.Integer, db.ForeignKey('ads.id'), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    channel = db.relationship('Channel', backref=db.backref('schedule_entries', lazy=True, cascade="all, delete-orphan"))
    video = db.relationship('Video')

class Ad(db.Model):
    __tablename__ = 'ads'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=False, default=15)

# --- Helper Functions ---
def get_current_schedule(channel_id):
    now = datetime.utcnow()
    schedule_entry = ChannelSchedule.query.filter(
        ChannelSchedule.channel_id == channel_id,
        ChannelSchedule.start_time <= now,
        ChannelSchedule.end_time >= now
    ).first()
    return schedule_entry

# --- Frontend Routes ---
@app.route('/')
def index():
    featured_tag = Tag.query.filter_by(name='featured').first()
    featured_videos = []
    if featured_tag:
        featured_videos = featured_tag.videos.order_by(desc(Video.id)).limit(6).all()
    channels = Channel.query.all()
    sections = []
    tags_for_sections = ['action', 'comedy', 'drama']
    for tag_name in tags_for_sections:
        tag = Tag.query.filter_by(name=tag_name).first()
        if tag:
            videos_in_section = tag.videos.order_by(desc(Video.id)).limit(6).all()
            if videos_in_section:
                sections.append({'tag': tag.name.title(), 'videos': videos_in_section})
    return render_template('index.html', featured=featured_videos, channels=channels, sections=sections)

@app.route('/watch/<int:video_id>')
def watch(video_id):
    video = Video.query.get_or_404(video_id)
    tags = [tag.name for tag in video.tags]
    return render_template('watch.html', video=video, tags=tags)

@app.route('/uploads/posters/<filename>')
def uploaded_poster_file(filename):
    return send_from_directory(app.config['POSTER_FOLDER'], filename)

@app.route('/uploads/videos/<filename>')
def uploaded_video_file(filename):
    return send_from_directory(app.config['VIDEO_FOLDER'], filename)

@app.route('/channel/play/<int:channel_id>')
def play_channel(channel_id):
    channel = Channel.query.get_or_404(channel_id)
    if channel.channel_type == 'virtual':
        return play_virtual_channel(channel)
    else:
        return play_manual_channel(channel)

def play_manual_channel(channel):
    schedule = get_current_schedule(channel.id)
    if not schedule:
        return render_template('channel_offline.html', channel_name=channel.name)
    now = datetime.utcnow()
    seek_offset = (now - schedule.start_time).total_seconds()
    video_filename = schedule.video.file_path.split('/')[-1]
    return render_template('channel_vod.html',
        title=channel.name,
        label="Live",
        video_filename=video_filename,
        offset=seek_offset
    )

def play_virtual_channel(channel):
    if not channel.rule_tag_id:
        return render_template('channel_offline.html', channel_name=channel.name)
    videos_with_rule_tag = Video.query.join(video_tags).join(Tag).filter(Tag.id == channel.rule_tag_id).all()
    if not videos_with_rule_tag:
        return render_template('channel_offline.html', channel_name=channel.name)
    total_duration_seconds = sum(video.duration_seconds for video in videos_with_rule_tag if video.duration_seconds)
    if total_duration_seconds == 0:
        return render_template('channel_offline.html', channel_name=channel.name)
    now_utc = datetime.utcnow()
    seconds_into_day = (now_utc - now_utc.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    current_loop_position = seconds_into_day % total_duration_seconds
    seek_offset = 0
    current_video = None
    time_accumulator = 0
    sorted_videos = sorted(videos_with_rule_tag, key=lambda v: v.id)
    for video in sorted_videos:
        video_duration = video.duration_seconds
        if time_accumulator + video_duration > current_loop_position:
            current_video = video
            seek_offset = current_loop_position - time_accumulator
            break
        time_accumulator += video_duration
    if not current_video:
        current_video = sorted_videos[0]
        seek_offset = 0
    video_filename = current_video.file_path.split('/')[-1]
    return render_template('channel_vod.html',
        title=channel.name,
        label=f"Playing '{channel.rule_tag.name}'",
        video_filename=video_filename,
        offset=seek_offset,
        playlist=sorted_videos,
        current_video_id=current_video.id,
        total_duration_seconds=total_duration_seconds
    )

# --- Admin Routes ---
@app.route('/admin/videos')
def admin_videos():
    videos = Video.query.all()
    return render_template('admin_videos.html', videos=videos)

@app.route('/admin/videos/add', methods=['GET', 'POST'])
def add_video():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        content_type = request.form.get('content_type', 'movie')
        video_file = request.files['video']
        poster_file = request.files['poster']
        duration_seconds = int(request.form.get('duration', 1)) * 60
        video_filename = str(uuid.uuid4()) + "_" + video_file.filename
        poster_filename = str(uuid.uuid4()) + "_" + poster_file.filename
        video_path = os.path.join(app.config['VIDEO_FOLDER'], video_filename)
        poster_path = os.path.join(app.config['POSTER_FOLDER'], poster_filename)
        video_file.save(video_path)
        poster_file.save(poster_path)
        new_video = Video(
            title=title,
            description=description,
            file_path=os.path.join('videos', video_filename),
            poster_path=os.path.join('posters', poster_filename),
            duration_seconds=duration_seconds,
            content_type=content_type
        )
        tag_ids = request.form.getlist('tags')
        for tag_id in tag_ids:
            tag = Tag.query.get(tag_id)
            if tag:
                new_video.tags.append(tag)
        db.session.add(new_video)
        db.session.commit()
        flash('Video added successfully!', 'success')
        return redirect(url_for('admin_videos'))
    tags = Tag.query.all()
    return render_template('video_form.html', tags=tags, video=None)

@app.route('/admin/tags', methods=['GET', 'POST'])
def manage_tags():
    if request.method == 'POST':
        tag_name = request.form['name']
        if tag_name:
            existing_tag = Tag.query.filter_by(name=tag_name).first()
            if not existing_tag:
                new_tag = Tag(name=tag_name)
                db.session.add(new_tag)
                db.session.commit()
                flash('Tag added successfully!', 'success')
            else:
                flash('Tag already exists.', 'warning')
        return redirect(url_for('manage_tags'))
    tags = Tag.query.all()
    return render_template('tags.html', tags=tags)

# --- NEW: Route to edit a tag ---
@app.route('/admin/tags/edit/<int:tag_id>', methods=['GET', 'POST'])
def edit_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    if request.method == 'POST':
        new_name = request.form['name']
        if new_name and new_name != tag.name:
            # Check if new name already exists
            existing_tag = Tag.query.filter_by(name=new_name).first()
            if existing_tag:
                flash('A tag with this name already exists.', 'warning')
            else:
                tag.name = new_name
                db.session.commit()
                flash('Tag updated successfully!', 'success')
        return redirect(url_for('manage_tags'))

    return render_template('edit_tag.html', tag=tag)

# --- NEW: Route to delete a tag ---
@app.route('/admin/tags/delete/<int:tag_id>', methods=['POST'])
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    # Safety check: prevent deleting a tag that is in use
    if tag.videos.first():
        flash(f"Cannot delete tag '{tag.name}' because it is currently assigned to one or more videos.", 'danger')
    else:
        db.session.delete(tag)
        db.session.commit()
        flash(f"Tag '{tag.name}' has been deleted.", 'success')
    return redirect(url_for('manage_tags'))


@app.route('/admin/channels')
def admin_channels():
    channels_with_tags = db.session.query(Channel).options(db.joinedload(Channel.rule_tag)).all()
    return render_template('admin_channels.html', channels=channels_with_tags)

@app.route('/admin/channels/add', methods=['GET', 'POST'])
def add_channel():
    if request.method == 'POST':
        name = request.form['name']
        channel_type = request.form['channel_type']
        new_channel = Channel(name=name, channel_type=channel_type)
        if channel_type == 'virtual':
            rule_tag_id = request.form.get('rule_tag_id')
            if rule_tag_id:
                new_channel.rule_tag_id = int(rule_tag_id)
        db.session.add(new_channel)
        db.session.commit()
        flash('Channel created successfully!', 'success')
        return redirect(url_for('admin_channels'))
    tags = Tag.query.all()
    return render_template('channel_form.html', tags=tags)

@app.route('/admin/channels/delete/<int:channel_id>', methods=['POST'])
def delete_channel(channel_id):
    channel = Channel.query.get_or_404(channel_id)
    db.session.delete(channel)
    db.session.commit()
    flash('Channel deleted successfully!', 'success')
    return redirect(url_for('admin_channels'))

@app.route('/admin/channels/schedule/<int:channel_id>')
def channel_schedule(channel_id):
    channel = Channel.query.get_or_404(channel_id)
    if channel.channel_type == 'virtual':
        flash("Virtual channels do not have a manual schedule.", "warning")
        return redirect(url_for('admin_channels'))
    videos = Video.query.all()
    schedule_entries = ChannelSchedule.query.filter_by(channel_id=channel_id).order_by(ChannelSchedule.start_time).all()
    return render_template('channel_schedule.html', channel=channel, videos=videos, schedule_entries=schedule_entries)

@app.route('/admin/channels/schedule/add', methods=['POST'])
def add_schedule_entry():
    channel_id = request.form['channel_id']
    video_id = request.form['video_id']
    start_time_str = request.form['start_time']
    video = Video.query.get(video_id)
    start_time = datetime.fromisoformat(start_time_str)
    end_time = start_time + timedelta(seconds=video.duration_seconds)
    new_entry = ChannelSchedule(
        channel_id=channel_id,
        video_id=video_id,
        start_time=start_time,
        end_time=end_time
    )
    db.session.add(new_entry)
    db.session.commit()
    return redirect(url_for('channel_schedule', channel_id=channel_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5016, debug=True)
