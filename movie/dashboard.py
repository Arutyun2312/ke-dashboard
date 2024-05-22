import streamlit as st
import pandas as pd
import util
import altair as alt
import movie.model as model

def run():
    movies_df, ratings_df, users_df = model.read_df()

    movie_list = [None] + movies_df['Title'].tolist()
    genre_list = [None] + sorted(set(util.flat_map(lambda x : x, movies_df['Genres'].tolist())))
    with st.sidebar:
        st.title('Filters')
        selected_movie = st.selectbox('Select a Movie:', movie_list)
        if selected_movie is None:
            selected_genre = st.selectbox('Select a Genre:', genre_list)
        else:
            selected_genre = None

    if selected_movie is None:
        st.title('Movie Ratings Dashboard')
        col1, col2 = st.columns(2)
        with col1:
            model.gender_demo(selected_genre, selected_movie)
            model.popular_movies(selected_genre)
        with col2:
            model.movie_count()
            model.movie_genres()
    else:
        model.gender_demo(selected_genre, selected_movie)
        model.movie_inspection(selected_movie)