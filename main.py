import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
import pandas as pd
from collections import Counter
from PIL import Image
import folium
from streamlit_folium import st_folium, folium_static
import googlemaps
import musicbrainzngs

st.set_page_config(
    page_title="Spotify Analyzer",
    page_icon="favicon.png",
    layout="wide"
)

# Define the scope and Spotify OAuth
scope = 'user-library-read playlist-read-private'
oauth = SpotifyOAuth(client_id='be97c21b03a447c182d57288acf12856',
                     client_secret='f04382d3507a42559b4e3d556cc9091d',
                     redirect_uri='http://localhost:8501',
                     scope=scope,
                     show_dialog=True,
                     cache_path='token.txt')

gmaps = googlemaps.Client(key='AIzaSyBWQDKHu7qGqy35uvNlbR8rjHHpsejIXo4')
musicbrainzngs.set_useragent("SpotfyAnalyzer", "0.1", "fmedi027@fiu.edu")

def get_recommendations(seed_tracks, num_tracks):
    sp = spotipy.Spotify(auth_manager=oauth)
    recommendations = sp.recommendations(seed_tracks=seed_tracks, limit=num_tracks)
    return [track['name'] + ' - ' + track['artists'][0]['name'] for track in recommendations['tracks']]



def main():

    st.title("Spotify Playlist Analyzer")

    # Handle authentication
    token_info = oauth.get_cached_token()
    if not token_info:
        url = st.query_params
        if 'code' not in st.session_state:
            url = st.experimental_get_query_params()
            if 'code' in url:
                st.session_state['code'] = url['code'][0]  # Save code to session state to prevent reuse issues

        if 'code' in st.session_state:
            try:
                token_info = oauth.get_access_token(st.session_state['code'])
                st.experimental_set_query_params()  # Clear URL parameters after handling
                st.success('Logged in successfully!')
                del st.session_state['code']  # Clear code from session state after successful authentication
            except SpotifyOauthError as e:
                st.error(f"Failed to authenticate: {e}")
                del st.session_state['code']  # Also clear code if failed to ensure fresh attempt
                return
        else:
            auth_url = oauth.get_authorize_url()
            if st.button('Login with Spotify'):
                st.markdown(f'Please log in [here]({auth_url}).', unsafe_allow_html=True)
                st.write('After logging in, please press "Rerun" or refresh the page.')

    if token_info:

        sp = spotipy.Spotify(auth=token_info['access_token'])
        st.success('Logged in with Spotify')

        # Fetch and display user's playlists in a select box
        playlists = sp.current_user_playlists(limit=50)
        playlist_names = [playlist['name'] for playlist in playlists['items']]
        playlist_ids = [playlist['id'] for playlist in playlists['items']]
        playlist_selection = st.selectbox('Select a Playlist', playlist_names, key='playlist_select')

        # Get the selected playlist ID and fetch tracks
        selected_playlist_id = playlist_ids[playlist_names.index(playlist_selection)]
        tracks = sp.playlist_tracks(selected_playlist_id)

        # Display tracks in the playlist
        with st.sidebar:
            col1, col2= st.columns(2)
            with col2:
                st.markdown(":green[Powered by:]")

            st.image('logo.png', use_column_width=True)
            st.subheader(f"Tracks in {playlist_selection}:")
            for i, item in enumerate(tracks['items']):
                track = item['track']
                st.write(f"{i + 1}. {track['name']} - {track['artists'][0]['name']}")



        tab1, tab2, tab3 = st.tabs(["📊 Statistics", "ℹ️ Artist Info", "⭐ Recommendation"])
        with tab1:


            with st.container(border=True):
                col1, col2 = st.columns(2)
                with col1:
                    # bpm graph
                    st.write("Beats Per Minute (BPM):")
                    track_ids = [item['track']['id'] for item in tracks['items'] if item['track']['id']]
                    audio_features_list = sp.audio_features(track_ids)
                    tempo_data = {item['track']['name']: feature['tempo'] for item, feature in
                                  zip(tracks['items'], audio_features_list) if feature}
                    if tempo_data:
                        st.bar_chart(data=tempo_data)
                    else:
                        st.warning("No tempo data available for the selected tracks.")

                with col2:
                    # genre graph
                    st.write("Songs By Genre:")
                    artist_ids = {item['track']['artists'][0]['id'] for item in tracks['items'] if item['track']['artists']}
                    artists_data = [sp.artist(artist_id) for artist_id in artist_ids]
                    genre_counts = Counter(genre for artist in artists_data for genre in artist['genres'])
                    if genre_counts:
                        st.bar_chart(data=genre_counts)
                    else:
                        st.warning("No genre data available for the artists in the selected playlist.")

            # Audio feature trends chart
            st.write("Song Features:")
            feature_options = ['valence', 'energy', 'danceability', 'loudness', 'tempo']
            selected_features = st.multiselect('Select features to plot', feature_options, default=['valence', 'energy','danceability'])
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

            # interactive data table

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
            with st.container(border=True):
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
                    playlists = sp.current_user_playlists(limit=50)
                    playlist_names = [playlist['name'] for playlist in playlists['items']]
                    playlist_ids = [playlist['id'] for playlist in playlists['items']]
                    #playlist_selection = st.selectbox('Select a Playlist', playlist_names)
                    selected_playlist_id = playlist_ids[playlist_names.index(playlist_selection)]
                    tracks = sp.playlist_tracks(selected_playlist_id)
                    artist_ids = {item['track']['artists'][0]['id'] for item in tracks['items'] if item['track']['artists']}
                    artists_data = [sp.artist(artist_id) for artist_id in artist_ids]

                    # Map display
                    st.write("Artist Locations Map:")
                    artist_map = create_artist_map(artists_data)
                    if artist_map:
                        st_folium(artist_map, height=400)  # Show the map
                    else:
                        st.error("Failed to create a map to display.")  # Error message if the map wasn't created

        with tab3:
            # Recommendation feature

            col1, col2= st.columns(2)
            with col1:
                with st.container(border=True, height= 570):
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
                            seed_tracks = [track['track']['id'] for track in tracks['items']][
                                          :5]  # Use first 5 tracks as seeds
                            recommended_songs = get_recommendations(seed_tracks, num_songs)


                            with col2:
                                with st.container(border=True, height=570):
                                    image = Image.open(playlist_image)
                                    st.image(image)
                                    st.subheader(playlist_name)
                                    st.write("Recommended Songs:")

                                    for i, song in enumerate(recommended_songs):
                                        st.write(f"{i + 1}. {song}")

                                    # for song in recommended_songs:
                                    #     st.write(song)


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


def create_artist_map(artist_data):
    artist_map = folium.Map(location=[20, 0], zoom_start=2)
    for artist in artist_data:
        artist_city = get_artist_city(artist['name'])
        if artist_city:
            lat, lon = geocode_city(artist_city)
            if lat and lon:
                folium.Marker([lat, lon], popup=f"{artist['name']}<br>{artist_city}").add_to(artist_map)
            else:
                print(f"Geocoding failed for {artist_city}")
        else:
            print(f"City not found for {artist['name']}")
    return artist_map


def geocode_city(city_name):
    try:
        geocode_result = gmaps.geocode(city_name)
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return (location['lat'], location['lng'])
        else:
            print(f"No results for {city_name}")  # Debugging output
    except Exception as e:
        print(f"Error geocoding {city_name}: {e}")
    return (None, None)  # Ensure two values are always returned



if __name__ == "__main__":
    main()
