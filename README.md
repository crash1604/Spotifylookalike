# SpotifyLookalike

Welcome to SpotifyLookalike, a small music streaming app built with Django and Django Rest Framework. This project aims to provide basic functionalities similar to Spotify, including managing albums, artists, user authentication, music tracks, and playlists.

## Modules

### 1. **Album Module**
   - CRUD operations for albums.
   - Endpoints specified in `album/urls.py`.
   - **Endpoints:**
   - - `/album/`: Get all albums
   - - `/album/add/`: Add a new album
   - - `/album/tracklist/<str:artist_name>/<str:album_name>/`: Get tracks by album name and artist
   - - `/album/<str:artist_name>/<str:album_name>/`: Get album by artist and name
   - - `/album/<str:artist_name>/`: Get albums by artist

   Note: Album settings are intentionally not modifiable for simplicity.

### 2. **Artist Module**
   - CRUD operations for artists.
   - One artist can have multiple albums.
   - Endpoints specified in `artist/urls.py`.
   - **Endpoints:**
    - `/artist/`: Get all artists
    - `/artist/add/`: Add a new artist
    - `/artist/<str:artist_name>/delete/`: Delete artist by name
    - `/artist/<str:artist_name>/modify/`: Modify artist by name
    - `/artist/<str:artist_name>/`: Get artist by name

### 3. **Authentication Module**
   - Token-based authentication for securing all views.
   - Implemented for ensuring secure access to the entire application.
   - Endpoints specified in `authentication/urls.py`.
   - **Endpoints:**
    - `/auth/login/`: User login
    - `/auth/register/`: User registration
    - `/auth/tokentest/`: Token test
    - `/auth/logout/`: User logout

### 4. **Music Module**
   - Core module facilitating CRUD operations for music files.
   - Many-to-many relationship with playlists.
   - One-to-many relationship with albums and artists.
   - Data can be stored locally or scaled using external storage (e.g., AWS S3).
   - Endpoints specified in `music/urls.py`.
   - **Endpoints:**
    - `/music/`: Get all tracks
    - `/music/add/`: Add a new track
    - `/music/<str:track_name>/delete/`: Delete track by name
    - `/music/<str:track_name>/update/`: Update track by name
    - `/music/<str:track_name>/`: Get tracks by name

### 5. **Playlist Module**
   - CRUD operations for playlists.
   - Add or remove tracks to/from playlists.
   - Many-to-many relationship with music files.
   - Endpoints specified in `playlist/urls.py`.
   - **Endpoints:**
    - `/playlist/`: Get all playlists
    - `/playlist/addTo/<str:playlist_name>/`: Add tracks to a playlist
    - `/playlist/removeFrom/<str:playlist_name>/`: Remove tracks from a playlist
    - `/playlist/new/`: Create a new playlist
    - `/playlist/delete/<str:playlist_name>/`: Delete playlist by name
    - `/playlist/<str:playlist_name>/`: Get playlist by name

## Running Locally
1. Clone the repository: `git clone https://github.com/crash1604/SpotifyLookalike.git`
2. Navigate to the project directory: `cd SpotifyLookalike`
3. Create a virtual environment: `python -m venv venv`
4. Activate the virtual environment:
    - On Windows: `venv\Scripts\activate`
    - On macOS/Linux: `source venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Apply migrations: `python manage.py migrate`
7. Run the development server: `python manage.py runserver`

## Manual Testing with Pre-Written API Test Calls

To facilitate manual testing of SpotifyLookalike, you can use the following pre-written API test calls. These calls are formatted in a `.rest` file, and you can use tools like [REST Client for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) to execute them.

### Prerequisites
- Ensure that the project is running locally. If not, follow the "Running Locally" instructions mentioned in the README.

### API_TEST.REST File
- Locate the file name `API_TEST.rest` for a comprehensive testing cases
- Works well with REST client for Visual Studio code

Feel free to customize the test calls based on your specific scenarios and data. Execute these calls using your favorite REST client, and enjoy testing your SpotifyLookalike application! 🚀

Feel free to explore and enhance the functionality according to your needs! Enjoy your SpotifyLookalike experience! 🎶 
