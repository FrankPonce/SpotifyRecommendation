# Spotify Recommendation Web App

*Spotify Analyzer* is a web application in which users can log into their Spotify account and select a playlist to visualize. The website provides interesting statistics and graphics on various features such as the genres, BPM, artist information, and general trends of the playlist, providing a general overview of the playlist for the user. 

## Try it yourself

https://spotifyrec.streamlit.app/

## Features

The application includes the following features:

- [x] Spotify log-in 
  - The user can log in with an existing Spotify account.
  - Users can select from any Spotify log in system, including Google, Apple ID, and writing in the account and password.
  - Users can then select any playlist in their Spotify account
- [x] Streamlit and Folium data visualization 
  - Colorful bar graphs, line graphs, and tables display relevant information in an easy-to-understand way.
  - An interactive map shows the location of origin of each artist in the playlist.
  - 
- [x] AI-powered playlist generator
  - Users can generate a new playlist based on the songs in their selected playlist.
  - The user can select the name, an image, and the total number of songs for their new playlist.
  - The new playlist will be displayed on the screen.
  - The new playlist will also be sent to the user's Spotify account, where it will be ready to play.
- [x] User can log out via a button:
  - The Log Out button allows a user to log out from their account.
  - The user will be logged out of their account and return to the log in page.

## Video Walkthrough

</img src='./misc/login.gif'>

</img src='./misc/map.gif'>

</img src='./misc/playlist.gif'>

## License

    Copyright 2024 Cecilia Montoril de Campos and Frank Mediavilla

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
