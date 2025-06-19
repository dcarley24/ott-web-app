# OTT Web App: A VOD and Virtual FAST Channel Platform

## Overview

`ott-web-app` is a functional prototype of a modern Over-the-Top (OTT) media service built with Python and Flask. This application serves as a comprehensive demonstration of core concepts in the video streaming industry, including a robust Video-on-Demand (VOD) library and a sophisticated engine for creating dynamic, rule-based "Virtual" FAST (Free Ad-supported Streaming TV) channels.

The entire system is managed through a clean, dark-themed administrative back-end, showcasing a full-stack approach to content management and delivery.

## Core Features

* **VOD Library Management**: Upload, manage, and tag a library of video content, complete with titles, descriptions, and posters.
* **Virtual FAST Channel Engine**: The standout feature. Instead of manually scheduling content, administrators can create endless, 24/7 linear-style channels based on simple rules (e.g., "play all videos with the 'comedy' tag"). The backend automatically calculates the playlist and the current playing position to create a seamless "lean-back" TV experience.
* **Live Player with Debug Panel**: The channel player includes a real-time debug panel that displays the dynamically generated playlist, the total duration, and highlights the currently playing video, offering transparent insight into the scheduling logic.
* **Comprehensive Admin Panel**: A secure, behind-the-scenes interface for:
    * Managing the video and poster library.
    * Creating, editing, and deleting content tags.
    * Building and managing both manual and virtual channels.
* **Content Seeding**: Includes a `bulk_insert.py` script to quickly populate the database with sample content for demonstration purposes.

## Tech Stack

* **Backend**: Python 3
* **Web Framework**: Flask
* **Database ORM**: SQLAlchemy
* **Frontend**: HTML5, CSS3, Bootstrap 5
* **Database**: SQLite (for development)

## Setup and Installation

To get the project running locally, follow these steps:

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/dcarley24/ott-web-app.git](https://github.com/dcarley24/ott-web-app.git)
    cd ott-web-app
    ```

2.  **Create and Activate a Virtual Environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    *(Note: A `requirements.txt` file should be created from your environment. For now, key dependencies are listed below.)*
    ```bash
    pip install Flask Flask-SQLAlchemy
    ```

4.  **Prepare Media Assets**
    * Place a sample video file (e.g., `BigBuckBunny_320x180.mp4`) inside the `/uploads/videos/` directory.
    * Place a sample poster image (e.g., `BigBuckBunny_320x180.jpg`) inside the `/uploads/posters/` directory.
    *(The `bulk_insert.py` script requires these source files to exist.)*

5.  **Populate the Database**
    * Run the bulk insert script to create and populate the database with sample videos and tags.
    ```bash
    python bulk_insert.py
    ```

6.  **Run the Application**
    ```bash
    python app.py
    ```
    The application will be running at `http://127.0.0.1:5016`.

## Key Architectural Concepts

This project was designed to showcase an understanding of modern OTT service architecture.

### Virtual FAST Channel Logic

The core of the application is the `play_virtual_channel` function in `app.py`. It demonstrates a scalable approach to content programming by:
1.  Querying all videos that match a channel's predefined rule (e.g., a specific tag).
2.  Calculating the total duration of the resulting playlist.
3.  Using the current time of day (UTC) modulo the total duration to determine the exact position within the 24/7 loop.
4.  Iterating through the playlist to find which video should be "on air" and calculating the `seek_offset` for the player to start from.

This mimics the automated, scalable scheduling used by major FAST providers.

### API-Ready Architecture

The application has been intentionally structured to be "headless-ready." While it currently renders HTML templates for a web-based frontend, the backend logic is decoupled. The next stage of development involves creating a dedicated `/api` layer using Flask Blueprints to serve all data in JSON format. This would enable the development of native client applications for platforms like:
* Roku (using BrightScript)
* Samsung Tizen / LG webOS (using JavaScript)
* iOS / Android
