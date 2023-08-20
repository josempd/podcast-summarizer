import streamlit as st
import modal
import json
import re
import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

JSON_DIR = './podcasts'
GOOGLE_KEY=st.secrets["gcp_service_account"]
GOOGLE_SHEETS_URL=st.secrets["public_gsheets_url"]

def main():
    st.title("Your podcast, summarized")

    json_data = load_data(GOOGLE_SHEETS_URL)
    for index, row in json_data.iterrows():
        json_filename = os.path.join(JSON_DIR, row['json'])
        json_content = json.loads(row['value'])

        with open(json_filename, 'w') as json_file:
            json.dump(json_content, json_file)

    available_podcast_info = create_dict_from_json_files(JSON_DIR)
    # Left section - Input fields
    st.sidebar.header("Podcast RSS Feeds")

    # Dropdown box
    st.sidebar.subheader("Available Podcasts Feeds")
    selected_podcast = st.sidebar.selectbox("Select Podcast", options=available_podcast_info.keys(), index=(len(available_podcast_info)-1))

    if selected_podcast:

        podcast_info = available_podcast_info[selected_podcast]

        # Right section - Newsletter content
        st.header("Podcast details")

        # Display the podcast title
        st.subheader("Episode Title")
        st.write(podcast_info['podcast_details']['episode_title'])

        # Display the podcast summary and the cover image in a side-by-side layout
        col1, col2 = st.columns([7, 3])

        with col1:
            # Display the podcast episode summary
            st.subheader("Podcast Episode Summary")
            st.write(podcast_info['podcast_summary'])

        with col2:
            st.image(podcast_info['podcast_details']['episode_image'], caption="Podcast Cover", width=300, use_column_width=True)

        # Display the podcast guest and their details in a side-by-side layout
        col3, col4 = st.columns([7, 3])

        with col3:
            st.subheader("Podcast Guest")
            st.write(podcast_info['podcast_guest'])

        # Display the five key moments
        st.subheader("Key Moments")
        key_moments = podcast_info['podcast_highlights']
        for moment in key_moments.split('\n'):
            st.markdown(
                f"<p style='margin-bottom: 5px;'>{moment}</p>", unsafe_allow_html=True)

    # User Input box
    st.sidebar.subheader("Add and Process New Podcast Feed (Max 30 min episodes)")
    url = st.sidebar.text_input("Link to RSS Feed")

    process_button = st.sidebar.button("Process Podcast Feed")
    st.sidebar.markdown("**Note**: Podcast processing can take upto 5 mins, please be patient.")

    if process_button:

        # Call the function to process the URLs and retrieve podcast guest information
        podcast_info = process_podcast_info(url)
        st.experimental_rerun()

def create_dict_from_json_files(folder_path):
    json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    data_dict = {}

    for file_name in json_files:
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, 'r') as file:
            podcast_info = json.load(file)
            podcast_name = podcast_info['podcast_details']['podcast_title']
            # Process the file data as needed
            data_dict[podcast_name] = podcast_info

    return data_dict

def process_podcast_info(url):
    f = modal.Function.lookup("corise-podcast-project", "process_podcast")
    output = f.call(url, '/')
    filename = get_next_podcast_filename(output)

    with open(filename, "w") as outfile:
        json.dump(output, outfile)
    return output

def get_next_podcast_filename(json_content):
    # List all files in the directory
    files = os.listdir(JSON_DIR)

    # Extract podcast numbers using regex
    numbers = [int(re.search(r'podcast-(\d+)', file).group(1)) for file in files if re.search(r'podcast-(\d+)', file)]
    
    # If there are no podcast-*.json files, start from 1
    if not numbers:
        next_number = 1
    else:
        next_number = max(numbers) + 1
    json_filename = os.path.join(JSON_DIR, f"podcast-{next_number}.json")
    service_account_info = GOOGLE_KEY
    scopes = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    gc = gspread.authorize(credentials)
    gs = gc.open_by_url(GOOGLE_SHEETS_URL)
    worksheet = gs.worksheet('podcasts')
    # Append the new data to the CSV
    new_row = {
    "json": f"podcast-{next_number}.json",
    "value": json.dumps(json_content)  # Store JSON content as a string
    }
    row_values = list(new_row.values())
    gs.values_append('podcasts', {'valueInputOption': 'USER_ENTERED'}, {'values': [row_values]})
    
    return json_filename

@st.cache_data(ttl=600)
def load_data(sheets_url):
    csv_url = sheets_url.replace("/edit#gid=", "/export?format=csv&gid=")
    return pd.read_csv(csv_url)

if __name__ == '__main__':
    main()
