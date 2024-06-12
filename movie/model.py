import pandas as pd
import streamlit as st
import altair as alt
import util

@st.cache_data
def read_df():
    if util.isDev():
        data_dir = 'data/ml-1m/'
        movies_df = data_dir + 'movies.dat'
        ratings_df = data_dir + 'ratings.dat'
        users_df = data_dir + 'users.dat'
    else:
        movies_df = util.get_csv('https://firebasestorage.googleapis.com/v0/b/friendly-8b1c0.appspot.com/o/movies.dat?alt=media&token=d072d9af-bf42-412d-94b1-1754de96e465')
        ratings_df = util.get_csv('https://firebasestorage.googleapis.com/v0/b/friendly-8b1c0.appspot.com/o/ratings.dat?alt=media&token=92e061cd-7208-4c88-813c-3072d2567c3b')
        users_df = util.get_csv('https://firebasestorage.googleapis.com/v0/b/friendly-8b1c0.appspot.com/o/users.dat?alt=media&token=7c1ef0fd-d6ad-42fe-885d-2a90393a8340')

    movies_df = pd.read_csv(movies_df, sep='::', header=None, names=['MovieID', 'Title', 'Genres'], engine='python', encoding='latin1')
    movies_df['Genres'] = movies_df['Genres'].str.split('|')

    ratings_df = pd.read_csv(ratings_df, sep='::', header=None, names=['UserID', 'MovieID', 'Rating', 'Timestamp'], engine='python', encoding='latin1')
    users_df = pd.read_csv(users_df, sep='::', header=None, names=['UserID', 'Gender', 'Age', 'Occupation', 'Zip-code'], engine='python', encoding='latin1')

    return movies_df, ratings_df, users_df

def movie_inspection(selected_movie):
    if selected_movie is None:
        return
    movies_df, ratings_df, users_df = read_df()
    selected_movie_id = movies_df[movies_df['Title'] == selected_movie]['MovieID'].iloc[0]
    filtered_ratings = ratings_df[ratings_df['MovieID'] == selected_movie_id]

    st.title('Movie Inspection')
    st.dataframe(pd.DataFrame(
      [[filtered_ratings['Rating'].mean(), filtered_ratings.size]],
      columns=['Average rating', 'Number of Ratings']
    ).round(2), hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        movie_ratings()
    with col2:
        daily_watches(selected_movie_id)

def movie_ratings():
    movies_df, ratings_df, users_df = read_df()

    rating_counts = ratings_df['Rating'].value_counts().sort_index().reset_index()
    rating_counts.columns = ['Rating', 'Count']

    # Create the bar chart using Altair
    chart = alt.Chart(rating_counts).mark_bar().encode(
        x=alt.X('Rating:N', title='Rating'),
        y=alt.Y('Count:Q', title='Number of Ratings'),
        color=alt.Color('Rating:N', scale=alt.Scale(scheme='tableau20'), legend=None),  # Using a colorful scheme
        tooltip=[alt.Tooltip('Rating:N', title='Rating'), alt.Tooltip('Count:Q', title='Number of Ratings')]
    )

    st.subheader("Ratings Distribution")
    st.altair_chart(chart, use_container_width=True)

def daily_watches(selected_movie_id):
    movies_df, ratings_df, users_df = read_df()

    ratings_df['Timestamp'] = pd.to_datetime(ratings_df['Timestamp'], unit='s')
    specific_movie_ratings = ratings_df[ratings_df['MovieID'] == selected_movie_id]
    views_per_day = specific_movie_ratings.groupby(specific_movie_ratings['Timestamp'].dt.date).size()
    date_range = pd.date_range(start=views_per_day.index.min(), end=views_per_day.index.max())
    views_per_day = views_per_day.reindex(date_range, fill_value=0)

    st.subheader('Daily number of watches')
    st.line_chart(views_per_day)

def gender_demo(selected_genre, selected_movie):
    movies_df, ratings_df, users_df = read_df()

    if selected_movie is not None:
        selected_movie_id = movies_df[movies_df['Title'] == selected_movie]['MovieID'].iloc[0]
        ratings = ratings_df[ratings_df['MovieID'] == selected_movie_id]
        users_df = users_df[users_df['UserID'].isin(ratings['UserID'].unique())]

    if selected_genre is not None:
        movies = movies_df[movies_df['Genres'].astype(str).str.contains(selected_genre)]['MovieID'].values
        ratings = ratings_df[ratings_df['MovieID'].isin(movies)]
        users_df = users_df[users_df['UserID'].isin(ratings['UserID'].unique())]

    # Count the occurrence of each gender
    gender_counts = users_df['Gender'].value_counts().reset_index()
    gender_counts.columns = ['Gender', 'Count']

    # Create a pie chart using Altair
    pie_chart = alt.Chart(gender_counts).mark_arc().encode(
        theta=alt.Theta(field="Count", type="quantitative"),
        color=alt.Color(field="Gender", type="nominal", legend=alt.Legend(title="User Genders")),
        tooltip=['Gender', 'Count']
    ).properties(
        title="User Demographics by Gender"
    )

    # Streamlit visualization
    st.title("User Demographics by Gender")
    st.write("This pie chart shows the distribution of users by gender.")
    st.altair_chart(pie_chart, use_container_width=True)

def movie_count():
    movies_df, ratings_df, users_df = read_df()

    # Extract year from the title (assuming format is "Title (Year)")
    movies_df['Year'] = movies_df['Title'].str.extract(r'\((\d{4})\)')

    # Count the number of movies per year
    year_counts = movies_df['Year'].value_counts().reset_index()
    year_counts.columns = ['Year', 'Count']

    # Create a pie chart using Altair
    pie_chart = alt.Chart(year_counts).mark_arc().encode(
        theta=alt.Theta(field="Count", type="quantitative"),
        color=alt.Color(field="Year", type="nominal", scale=alt.Scale(scheme='category20b')),
        tooltip=['Year', 'Count'],
        text=alt.Text(field="Year", type="nominal")
    ).properties(
        title="Movie Count by Release Year"
    )

    # Add labels to the pie slices
    text = pie_chart.mark_text(radiusOffset=10, size=10).encode(
        text='Year'
    )

    # Combine the pie chart with the text
    final_chart = alt.layer(pie_chart, text).resolve_scale(
        color='independent',  # Allows each layer to have its own color scale if needed
        theta='shared'        # Ensures that the theta channel is shared between layers
    ).configure_view(
        strokeOpacity=0  # Removes the white border around the pie chart
    ).configure_mark(
        fillOpacity=0.8
    )

    # Streamlit visualization
    st.title("Movie Count by Release Year")
    st.write("This pie chart shows the distribution of movies by their release year.")
    st.altair_chart(final_chart, use_container_width=True)

def popular_movies(selected_genre):
    movies_df, ratings_df, users_df = read_df()

    if selected_genre is not None:
        movies_df = movies_df[movies_df['Genres'].astype(str).str.contains(selected_genre)]

    st.title('Most popular movies')
    rating_stats = ratings_df.groupby('MovieID').agg(Average_Rating=('Rating', 'mean'), Number_of_Ratings=('Rating', 'count')).reset_index()

    # Merge with movies_df to keep movie details
    movies_with_ratings = pd.merge(movies_df, rating_stats, on='MovieID')

    # Calculate C, the mean rating across all movies
    C = rating_stats['Average_Rating'].mean()

    # Calculate m, the minimum number of ratings required to be listed (let's use the 50th percentile)
    m = rating_stats['Number_of_Ratings'].quantile(0.50)

    # Compute the weighted rating score for each movie
    movies_with_ratings['IMDb Score'] = (movies_with_ratings['Number_of_Ratings'] / (movies_with_ratings['Number_of_Ratings'] + m) * movies_with_ratings['Average_Rating']) + (m / (movies_with_ratings['Number_of_Ratings'] + m) * C)

    # Sort movies by the score in descending order
    sorted_movies = movies_with_ratings.sort_values(by='IMDb Score', ascending=False)

    # Show the sorted DataFrame (or process it as needed)
    st.dataframe(sorted_movies[['Title', 'Average_Rating', 'Number_of_Ratings', 'IMDb Score']], hide_index=True, use_container_width=True)

def movie_genres():
    movies_df, ratings_df, users_df = read_df()

    # Calculate average rating and number of ratings per movie
    rating_stats = ratings_df.groupby('MovieID').agg(Average_Rating=('Rating', 'mean'), Number_of_Ratings=('Rating', 'count')).reset_index()

    # Merge with movies_df
    movies_with_ratings = pd.merge(movies_df, rating_stats, on='MovieID')

    # Constants for IMDb formula
    C = rating_stats['Average_Rating'].mean()
    m = rating_stats['Number_of_Ratings'].quantile(0.50)

    # Compute the weighted rating score for each movie
    movies_with_ratings['Score'] = (movies_with_ratings['Number_of_Ratings'] / (movies_with_ratings['Number_of_Ratings'] + m) * movies_with_ratings['Average_Rating']) + (m / (movies_with_ratings['Number_of_Ratings'] + m) * C)

    # Explode 'Genres' into separate rows
    movies_with_ratings = movies_with_ratings.explode('Genres')

    # Calculate average weighted score per genre
    genre_popularity = movies_with_ratings.groupby('Genres')['Score'].mean().reset_index()

    # Create a bar chart
    bar_chart = alt.Chart(genre_popularity).mark_bar().encode(
        x=alt.X('Genres:N', sort='-y', title='Genre'),
        y=alt.Y('Score:Q', title='Average Weighted Rating'),
        color=alt.Color('Genres:N', legend=None),
        tooltip=['Genres', alt.Tooltip('Score', format='.3f')]
    )

    # Streamlit visualization
    st.title("Movie Genre Popularity by IMDb WR")
    st.write("This bar chart shows the popularity of movie genres based on IMDb weighted ratings.")
    st.altair_chart(bar_chart, use_container_width=True)

def dashboard4():
    import streamlit as st
    import pandas as pd
    import altair as alt

    # Reading data using the pre-defined function
    movies_df, ratings_df, users_df = read_df()

    # Calculate total number of users
    total_users = users_df['UserID'].nunique()

    # Calculate total number of ratings
    total_ratings = ratings_df['Rating'].count()

    # Calculate average ratings per genre
    movies_exploded = movies_df.explode('Genres')
    merged_df = ratings_df.merge(movies_exploded, on='MovieID')
    average_ratings_per_genre = merged_df.groupby('Genres')['Rating'].mean().reset_index()

    # Calculate user activity over time (number of ratings per month)
    ratings_df['Timestamp'] = pd.to_datetime(ratings_df['Timestamp'], unit='s')
    ratings_df['Month'] = ratings_df['Timestamp'].dt.to_period('M')
    user_activity_over_time = ratings_df.groupby('Month').size().reset_index(name='count')
    user_activity_over_time['Month'] = user_activity_over_time['Month'].dt.to_timestamp()

    # Get the range of dates
    start_date = ratings_df['Timestamp'].min().date()
    end_date = ratings_df['Timestamp'].max().date()

    # Calculate genre distribution of rated movies
    genre_distribution = merged_df['Genres'].value_counts().reset_index()
    genre_distribution.columns = ['Genres', 'Count']

    # Streamlit layout
    st.title("MovieLens User Engagement Dashboard")

    # Metrics in one row
    col1, col2 = st.columns(2)
    col1.metric(label="Total Users", value=total_users, help="The total number of unique users in the dataset.")
    col2.metric(label="Total Ratings", value=total_ratings, help="The total number of ratings provided by users.")

    # Average ratings per genre bar chart
    st.write("### Average Ratings per Genre")
    st.write("This bar chart shows the average ratings given to movies in each genre. It helps identify which genres are generally rated higher by users.")
    bar_chart = alt.Chart(average_ratings_per_genre).mark_bar().encode(
        x=alt.X('Genres', title='Genre'),
        y=alt.Y('Rating', title='Average Rating'),
        tooltip=['Genres', 'Rating']
    ).properties(
        title="Average Ratings per Genre"
    )
    st.altair_chart(bar_chart, use_container_width=True)
    st.write("**Observations and Insights:**")
    st.write("- Genres such as 'Film-Noir' and 'Documentary' have the highest average ratings, indicating that these genres are particularly well-received by users.")
    st.write("- On the other hand, genres like 'Animation' and 'Horror' have lower average ratings, suggesting they may not be as favored by the audience.")

    # User activity over time line chart
    st.write("### User Activity Over Time")
    st.write(f"This line chart displays the number of ratings provided by users each month from {start_date} to {end_date}. It helps identify trends and peak periods of user activity.")
    line_chart = alt.Chart(user_activity_over_time).mark_line().encode(
        x=alt.X('Month', title='Month'),
        y=alt.Y('count', title='Number of Ratings'),
        tooltip=['Month', 'count']
    ).properties(
        title="User Activity Over Time"
    )
    st.altair_chart(line_chart, use_container_width=True)
    st.write("**Observations and Insights:**")
    st.write("- The data shows a peak in user activity around December 2000, which might be due to a surge in new users or a seasonal increase in movie watching.")
    st.write("- After the peak, there is a significant drop in activity, which stabilizes at a lower level. This trend could indicate initial enthusiasm followed by a tapering off of regular usage.")

    # Genre distribution pie chart
    st.write("### Genre Distribution of Rated Movies")
    st.write("This pie chart shows the distribution of genres among the rated movies. It highlights the most popular genres based on the number of ratings.")
    pie_chart = alt.Chart(genre_distribution).mark_arc().encode(
        theta=alt.Theta(field='Count', type='quantitative'),
        color=alt.Color(field='Genres', type='nominal'),
        tooltip=['Genres', 'Count']
    ).properties(
        title="Genre Distribution of Rated Movies"
    )
    st.altair_chart(pie_chart, use_container_width=True)
    st.write("**Observations and Insights:**")
    st.write("- The 'Drama' genre is the most rated, followed by 'Comedy' and 'Action', indicating these genres are the most popular among users.")
    st.write("- 'Film-Noir' and 'Documentary' genres, while having high average ratings, represent a smaller portion of the total ratings, suggesting they are niche but appreciated.")

