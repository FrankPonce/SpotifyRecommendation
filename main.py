import warnings
warnings.filterwarnings("ignore")  # Suppress all warnings

import os
os.environ['PYTHONWARNINGS'] = 'ignore'  # Suppress warnings via environment variable

import streamlit as st
st.set_option('deprecation.showPyplotGlobalUse', False)

st.set_page_config(
    page_title="Spotify Playlist Analyzer",
    page_icon="favicon.png",
    layout="wide"
)

# Initialize session state for token_info
if 'token_info' not in st.session_state:
    st.session_state['token_info'] = None

# Load environment variables
from dotenv import load_dotenv
load_dotenv()  # Load variables from a .env file

import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
import pandas as pd
from collections import Counter
from PIL import Image, ImageOps, ImageDraw, ImageFilter
import folium
from streamlit_folium import st_folium
import googlemaps
import musicbrainzngs

# Initialize Google Maps and MusicBrainz clients
gmaps_api_key = os.getenv('GMAPS_API_KEY')
gmaps = googlemaps.Client(key=gmaps_api_key)
musicbrainzngs.set_useragent("SpotifyAnalyzer", "0.1", "your_email@example.com")

@st.cache_data
def get_recommendations(_client_id, _client_secret, _redirect_uri, _scope, seed_tracks, num_tracks):
    oauth = SpotifyOAuth(
        client_id=_client_id,
        client_secret=_client_secret,
        redirect_uri=_redirect_uri,
        scope=_scope,
        show_dialog=True
    )
    sp = spotipy.Spotify(auth_manager=oauth)
    recommendations = sp.recommendations(seed_tracks=seed_tracks, limit=num_tracks)
    return [track['name'] + ' - ' + track['artists'][0]['name'] for track in recommendations['tracks']]

@st.cache_data
def get_playlists(_sp):
    return _sp.current_user_playlists(limit=50)

@st.cache_data
def get_playlist_tracks(_sp, playlist_id):
    return _sp.playlist_tracks(playlist_id)

@st.cache_data
def get_audio_features(_sp, track_ids):
    return _sp.audio_features(track_ids)

@st.cache_data
def get_artist_data(_sp, artist_ids):
    return [_sp.artist(artist_id) for artist_id in artist_ids]

@st.cache_data
def get_artist_city(artist_name):
    try:
        result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        if result['artist-list']:
            artist = result['artist-list'][0]
            if 'begin-area' in artist:
                return artist['begin-area'].get('name')
        return None
    except musicbrainzngs.WebServiceError as e:
        print(f"MusicBrainz error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

@st.cache_data
def geocode_city(_gmaps, city_name):
    try:
        geocode_result = _gmaps.geocode(city_name)
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return (location['lat'], location['lng'])
        else:
            print(f"No results for {city_name}")  # Debugging output
    except Exception as e:
        print(f"Error geocoding {city_name}: {e}")
    return (None, None)  # Ensure two values are always returned

def make_vinyl_image(img):
    # Resize the image to a square
    min_dim = min(img.size)
    try:
        resample_method = Image.Resampling.LANCZOS  # For Pillow >=9.1.0
    except AttributeError:
        resample_method = Image.LANCZOS  # For older versions

    img = img.resize((min_dim, min_dim), resample=resample_method)

    # Create circular mask
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + img.size, fill=255)

    # Apply mask to create a circular image
    circular_img = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
    circular_img.putalpha(mask)

    # Create a black background (vinyl record)
    background = Image.new('RGBA', img.size, (0, 0, 0, 255))

    # Draw grooves on the vinyl record
    draw = ImageDraw.Draw(background)
    center = (img.size[0] // 2, img.size[1] // 2)
    max_radius = img.size[0] // 2
    for r in range(max_radius, 0, -10):
        draw.ellipse([
            center[0] - r, center[1] - r,
            center[0] + r, center[1] + r
        ], outline=(40, 40, 40, 255))

    # Paste the circular image onto the vinyl background
    background.paste(circular_img, (0, 0), circular_img)

    return background

def create_artist_map(artists_data, _gmaps):
    artist_map = folium.Map(location=[20, 0], zoom_start=2)
    for artist in artists_data:
        artist_city = get_artist_city(artist['name'])
        if artist_city:
            lat, lon = geocode_city(_gmaps, artist_city)
            if lat and lon:
                folium.Marker([lat, lon], popup=f"{artist['name']}<br>{artist_city}").add_to(artist_map)
            else:
                print(f"Geocoding failed for {artist_city}")
        else:
            print(f"City not found for {artist['name']}")
    return artist_map

def main():
    # Define the scope and Spotify OAuth inside the main function
    scope = 'user-library-read playlist-read-private'

    client_id = os.getenv('SPOTIPY_CLIENT_ID')
    client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')  # Should be set to your deployed app's URL

    oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        show_dialog=True
        # Removed cache_path to prevent shared token storage
    )

    # Handle authentication
    if not st.session_state['token_info']:
        url = st.experimental_get_query_params()
        if 'code' not in st.session_state:
            if 'code' in url:
                st.session_state['code'] = url['code'][0]  # Save code to session state to prevent reuse issues

        if 'code' in st.session_state:
            try:
                token_info = oauth.get_access_token(st.session_state['code'])
                st.session_state['token_info'] = token_info  # Store token_info in session state
                st.experimental_set_query_params()  # Clear URL parameters after handling
                st.success('Logged in successfully!')
                del st.session_state['code']  # Clear code from session state after successful authentication
            except SpotifyOauthError as e:
                st.error(f"Failed to authenticate: {e}")
                del st.session_state['code']  # Also clear code if failed to ensure fresh attempt
                return
        else:
            auth_url = oauth.get_authorize_url()
            st.title("Spotify Playlist Analyzer")
            st.info("To test this app, you can login with the login and password: spotifyrectest@gmail.com")
            # Updated login button that opens in a new tab/window
            st.markdown(
                f'''
                <a href="{auth_url}" target="_blank">
                    <button style="
                        font-size:16px; 
                        padding:10px 20px; 
                        color:white; 
                        background-color:#1DB954; 
                        border:none; 
                        border-radius:25px; 
                        cursor:pointer;">
                        Login with Spotify
                    </button>
                </a>
                ''',
                unsafe_allow_html=True
            )
            st.stop()

    # If token_info is present, proceed with the app
    if st.session_state['token_info']:
        try:
            sp = spotipy.Spotify(auth=st.session_state['token_info']['access_token'])
        except spotipy.exceptions.SpotifyException as e:
            st.error(f"Spotify error: {e}")
            st.session_state['token_info'] = None  # Reset token_info
            st.stop()

        st.success('Logged in with Spotify')

        if st.button('Logout'):
            st.session_state['token_info'] = None  # Clear token_info from session state
            st.success('Logged out successfully. Please refresh the page to log in again.')
            st.stop()

        # Fetch playlists once
        try:
            playlists = get_playlists(_sp=sp)
        except spotipy.exceptions.SpotifyException as e:
            st.error(f"Failed to fetch playlists: {e}")
            st.stop()

        playlist_names = [playlist['name'] for playlist in playlists['items']]
        playlist_ids = [playlist['id'] for playlist in playlists['items']]
        playlist_selection = st.selectbox('Select a Playlist', playlist_names, key='playlist_select')

        # Get the selected playlist ID and fetch tracks
        selected_playlist_id = playlist_ids[playlist_names.index(playlist_selection)]
        tracks = get_playlist_tracks(_sp=sp, playlist_id=selected_playlist_id)
        track_ids = [item['track']['id'] for item in tracks['items'] if item['track']['id']]
        artist_ids = {item['track']['artists'][0]['id'] for item in tracks['items'] if item['track']['artists']}
        artists_data = get_artist_data(_sp=sp, artist_ids=artist_ids)
        audio_features_list = get_audio_features(_sp=sp, track_ids=track_ids)

        # Display tracks in the playlist
        with st.sidebar:
            col1, col2 = st.columns(2)
            with col2:
                st.markdown(":green[Powered by:]")
            st.image('logo.png', use_column_width=True)
            st.subheader(f"Tracks in {playlist_selection}:")
            for i, item in enumerate(tracks['items']):
                track = item['track']
                st.write(f"{i + 1}. {track['name']} - {track['artists'][0]['name']}")

        tab1, tab2, tab3 = st.tabs(["📊 Statistics", "ℹ️ Artist Info", "⭐ Recommendation"])

        with tab1:
            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    # BPM graph
                    st.write("Beats Per Minute (BPM):")
                    tempo_data = {item['track']['name']: feature['tempo'] for item, feature in
                                  zip(tracks['items'], audio_features_list) if feature}
                    if tempo_data:
                        st.bar_chart(data=tempo_data)
                    else:
                        st.warning("No tempo data available for the selected tracks.")

                with col2:
                    # Genre graph
                    st.write("Songs By Genre:")
                    genre_counts = Counter(genre for artist in artists_data for genre in artist['genres'])
                    if genre_counts:
                        st.bar_chart(data=genre_counts)
                    else:
                        st.warning("No genre data available for the artists in the selected playlist.")

            # Audio feature trends chart
            st.write("Song Features:")
            feature_options = ['valence', 'energy', 'danceability', 'loudness', 'tempo']
            selected_features = st.multiselect('Select features to plot', feature_options, default=['valence', 'energy', 'danceability'])
            features_data = {feature: [] for feature in selected_features}
            track_names = [item['track']['name'] for item in tracks['items']]
            for features in audio_features_list:
                for feature in selected_features:
                    if features:
                        features_data[feature].append(features[feature])
                    else:
                        features_data[feature].append(None)
            df_features = pd.DataFrame(features_data, index=track_names)
            if not df_features.empty:
                st.line_chart(df_features)
            else:
                st.warning("No audio feature data available for the selected tracks.")

            # Interactive data table
            if st.checkbox("Show advanced track statistics"):
                data = {
                    'Track Name': [item['track']['name'] for item in tracks['items']],
                    'Artist(s)': [', '.join(artist['name'] for artist in item['track']['artists']) for item in tracks['items']],
                    'Album': [item['track']['album']['name'] for item in tracks['items']],
                    'Release Date': [item['track']['album']['release_date'] for item in tracks['items']],
                    'Duration (min)': [
                        (item['track']['duration_ms'] // 60000) + ((item['track']['duration_ms'] % 60000) / 1000.0) / 60.0 for
                        item in tracks['items']],
                    'Popularity': [item['track']['popularity'] for item in tracks['items']],
                    'Danceability': [features['danceability'] for features in audio_features_list],
                    'Energy': [features['energy'] for features in audio_features_list],
                    'Valence': [features['valence'] for features in audio_features_list],
                    'Tempo (BPM)': [features['tempo'] for features in audio_features_list],
                    'Loudness (dB)': [features['loudness'] for features in audio_features_list]
                }
                track_dataframe = pd.DataFrame(data)
                st.write("Comprehensive Track Data:")
                st.dataframe(track_dataframe)

        with tab2:
            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    # Artists and their genres
                    artist_genre_data = {
                        'Artist Name': [artist['name'] for artist in artists_data],
                        'Genres': [', '.join(artist['genres']) for artist in artists_data]
                    }
                    artist_genres_dataframe = pd.DataFrame(artist_genre_data)
                    st.write("Artists and Their Genres:")
                    st.dataframe(artist_genres_dataframe, height=400)

                with col2:
                    # Map display
                    st.write("Artist Locations Map:")
                    with st.spinner('Loading artist map...'):
                        artist_map = create_artist_map(artists_data, _gmaps=gmaps)
                    if artist_map:
                        st_folium(artist_map, height=400)  # Show the map
                    else:
                        st.error("Failed to create a map to display.")  # Error message if the map wasn't created

        with tab3:
            # Recommendation feature
            col1, col2 = st.columns(2)
            with col1:
                with st.container():
                    st.subheader("Generate Song Recommendations Based on Playlist")
                    playlist_name = st.text_input("Enter Playlist Name:")
                    playlist_image = st.file_uploader("Upload Playlist Image", type=['jpg', 'png'])
                    num_songs = st.slider("Select number of songs:", 1, 25, 5)

                    if st.button('Create Playlist'):
                        if not playlist_name:
                            st.error("Please enter a playlist name.")
                        elif not playlist_image:
                            st.error("Please upload an image for the playlist.")
                        else:
                            seed_tracks = [track['id'] for track in track_ids][:5]  # Use first 5 tracks as seeds
                            recommended_songs = get_recommendations(
                                _client_id=client_id,
                                _client_secret=client_secret,
                                _redirect_uri=redirect_uri,
                                _scope=scope,
                                seed_tracks=seed_tracks,
                                num_tracks=num_songs
                            )

                            with col2:
                                with st.container():
                                    image = Image.open(playlist_image)
                                    vinyl_image = make_vinyl_image(image)
                                    st.image(vinyl_image)
                                    st.subheader(playlist_name)
                                    st.write("Recommended Songs:")

                                    for i, song in enumerate(recommended_songs):
                                        st.write(f"{i + 1}. {song}")

if __name__ == "__main__":
    main()
