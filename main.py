# Import the required module for text
# to speech conversion
from dotenv import load_dotenv

load_dotenv()

import requests
from gtts import gTTS
import openai
import os
import time
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.tag import pos_tag
import concurrent.futures
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
from concurrent.futures import ThreadPoolExecutor


nltk.download("punkt")
nltk.download("averaged_perceptron_tagger")


openai.api_key = os.getenv("OPENAI_API_KEY")
pexels_api_key = os.getenv("PEXELS_API_KEY")
# Where pexels stock footage will be downloaded to
download_folder = "stock_footage"


# Returns a list of nouns in a sentence provided


def extract_nouns(paragraph):
    # Tokenize the paragraph into sentences
    sentences = sent_tokenize(paragraph)

    nouns = []
    for sentence in sentences:
        # Tokenize the sentence into words
        words = nltk.word_tokenize(sentence)

        # Perform part-of-speech tagging
        pos_tags = nltk.pos_tag(words)

        for word, pos in pos_tags:
            # Check if the word is a noun
            if pos.startswith("NN"):
                # Add the noun to the list
                nouns.append(word)
                break  # Break out of the loop after finding the first noun

    return nouns


# Function that asks openai to generate script
def generate_script(user_input):
    # Introduce a delay of 1 second before making the API call
    time.sleep(1)

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=user_input,
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.7,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    script = response.choices[0].text.strip()
    return script


clips = []


def download_and_process_video(noun, duration):
    # Generate a query using the noun
    query = f"{noun} footage"

    # Generate a script for the video using ChatGPT (assumed already generated)

    # Retrieve stock footage using Pexels API

    headers = {"Authorization": pexels_api_key}
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=vertical"

    try:
        with requests.get(url, headers=headers) as response:
            response.raise_for_status()
            json_data = response.json()
            if json_data["videos"]:
                video = json_data["videos"][0]
                video_url = video["video_files"][0]["link"]

                # Download the stock footage
                video_data = requests.get(video_url).content
                video_filename = f"{noun}.mp4"

                with open(video_filename, "wb") as f:
                    f.write(video_data)

                # Clip the video based on the duration
                video_clip = VideoFileClip(video_filename).subclip(0, duration)
                # Wait for a short period to ensure the video clip is no longer in use
                time.sleep(1)

                # Remove the downloaded video file
                os.remove(video_filename)

                # Perform any other desired operations on the video clip

                # Return the processed video clip or any other output
                return video_clip

            else:
                print(f"No stock footage found for noun: {noun}")
                return None

    except requests.exceptions.HTTPError as err:
        print(
            f"Error occurred while downloading stock footage for noun: {noun}. Error: {err}"
        )
        return None


# Calculate the duration of a sentence using the audio length
def get_sentence_duration(sentence):
    tts = gTTS(sentence)
    tts.save("temp.mp3")
    audio_clip = AudioFileClip("temp.mp3")
    duration = audio_clip.duration
    audio_clip.close()
    os.remove("temp.mp3")
    return duration


# The text that you want to convert to audio
# article_topic = input("What would you like the article to be about? ")


# generated_script = generate_script(article_topic)
generated_script = "In a world filled with constant motion, take a moment to pause. Close your eyes and let your imagination soar."

nouns = extract_nouns(generated_script)
print("Nouns: ", nouns)
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = []
    for noun in nouns:
        duration = get_sentence_duration(noun)
        future = executor.submit(download_and_process_video, noun, duration)
        futures.append(future)

    for future in concurrent.futures.as_completed(futures):
        clip = future.result()
        if clip:
            clips.append(clip)


# Check if any clips were found before concatenating
if clips:
    # Concatenate all the clips together
    final_clip = concatenate_videoclips(clips)

    # Specify the output video filename
    output_filename = "combined_video.mp4"

    # Write the final concatenated video to a file
    final_clip.write_videofile(output_filename, codec="libx264", fps=24)

    # Close the final clip
    final_clip.close()
else:
    print("No stock footage clips found.")

# Passing the text and language to the engine,
# Language in which you want to convert
language = "en"
# myobj = gTTS(text=generated_script, lang=language, slow=False)
# Saving the converted audio in a mp3 file named
# welcome
# myobj.save("welcome.mp3")
