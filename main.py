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
from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeAudioClip,
)
from concurrent.futures import ThreadPoolExecutor
import random

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
    # Download the stock footage
    response = requests.get(
        f"https://api.pexels.com/videos/search?query={noun}&orientation=portrait&size=large",
        headers={"Authorization": pexels_api_key},
    )
    data = response.json()
    if "videos" not in data:
        print(f"No stock footage found for {noun}")
        return None

    video = data["videos"][0]
    video_url = video["video_files"][0]["link"]

    # Download the video file
    video_filename = f"stock_footage/{noun}_{video['id']}.mp4"
    with open(video_filename, "wb") as f:
        response = requests.get(video_url)
        f.write(response.content)

    # Trim the video to match the duration
    video_clip = VideoFileClip(video_filename).subclip(0, duration)

    # Set the output file path for the trimmed video
    trimmed_filename = f"stock_footage/trimmed_{noun}_{video['id']}.mp4"

    # Write the trimmed video to the output file
    video_clip.write_videofile(trimmed_filename)

    # Close the video clip reader
    video_clip.reader.close()

    # Check if the video has an audio track and close the audio reader if present
    if video_clip.audio is not None:
        video_clip.audio.reader.close_proc()

    # Add the trimmed video clip to the clips list
    clips.append(video_clip)
    # closing video_filename before deletion
    f.close()
    # Clean up the video file
    os.remove(video_filename)


print("clips: ", clips)


# Calculate the duration of a sentence using the audio length
def get_sentence_duration(sentence):
    tts = gTTS(sentence)
    tts.save("temp.mp3")
    audio_clip = AudioFileClip("temp.mp3")
    duration = audio_clip.duration
    audio_clip.close()
    os.remove("temp.mp3")
    return duration


# Returns the sentence that contains the noun
def find_sentence_with_noun(noun):
    sentences = generated_script.split(".")
    for sentence in sentences:
        if noun.lower() in sentence.lower():
            return sentence.strip()
    return None


# The script for everything
generated_script = "In a world filled with constant motion, take a moment to pause. Close your eyes and let your imagination soar."

# Passing the text and language to the engine,
# Language in which you want to convert
language = "en"
myobj = gTTS(text=generated_script, lang=language, slow=False)
# Saving the converted audio in a mp3 file named welcome
myobj.save("voiceover.mp3")

# The text that you want to convert to audio
# article_topic = input("What would you like the article to be about? ")


#  Combines all the mp4 files in a folder
def concatenate_mp4_files(folder="stock_footage", voiceover_file="voiceover.mp3"):
    clips = []

    # Get a list of all MP4 files in the folder
    file_list = [file for file in os.listdir(folder) if file.endswith(".mp4")]

    # Sort the file list based on the creation time
    file_list.sort(key=lambda file: os.path.getctime(os.path.join(folder, file)))

    # Get the resolution of the first video clip
    first_clip_path = os.path.join(folder, file_list[0])
    first_clip = VideoFileClip(first_clip_path)
    target_resolution = first_clip.size

    # Iterate over the files and load them as VideoFileClip objects
    for i, file in enumerate(file_list):
        filepath = os.path.join(folder, file)
        video_clip = VideoFileClip(filepath)

        # Resize the clip to the target resolution
        video_clip = video_clip.resize(target_resolution)

        duration = video_clip.duration  # Get the actual duration of the clip

        # Adjust the clip's start time to match the end time of the previous clip
        if i > 0:
            previous_clip = clips[i - 1]
            video_clip = video_clip.set_start(previous_clip.end)

        # Trim the clip to its actual duration
        trimmed_clip = video_clip.subclip(0, duration)
        clips.append(trimmed_clip)

    # Concatenate the clips
    final_clip = concatenate_videoclips(clips)

    # Load the voiceover file as an AudioFileClip
    voiceover_clip = AudioFileClip(voiceover_file)

    # Choose a random stock music file
    stock_music_folder = "stock_music"
    stock_music_files = [
        file for file in os.listdir(stock_music_folder) if file.endswith(".mp3")
    ]
    random_music_file = random.choice(stock_music_files)
    music_file_path = os.path.join(stock_music_folder, random_music_file)

    # Load the random stock music file as an AudioFileClip
    music_clip = AudioFileClip(music_file_path)

    # Combine the voiceover and music into a single audio file
    combined_audio = CompositeAudioClip(
        [music_clip.volumex(0.6), voiceover_clip.volumex(1.0)]
    )
    # Set the audio of the final video clip to the combined audio
    final_clip = final_clip.set_audio(combined_audio)

    # Define the output file path for the final video
    output_filename = "video_no_sound.mp4"

    # Write the final video file
    final_clip.write_videofile(
        output_filename, codec="libx264", audio_codec="aac", fps=30
    )

    # for clip in clips:
    #     clip.close()

    # # Delete the video files from the folder
    # for file in file_list:
    #     filepath = os.path.join(folder, file)
    #     os.remove(filepath)

    return final_clip


# generated_script = generate_script(article_topic)

nouns = extract_nouns(generated_script)
print("Nouns: ", nouns)
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = []
    for noun in nouns:
        duration = get_sentence_duration(find_sentence_with_noun(noun))
        future = executor.submit(download_and_process_video, noun, duration)
        futures.append(future)

    for future in concurrent.futures.as_completed(futures):
        clip = future.result()
        if clip:
            clips.append(clip)


# Check if any clips were found before concatenating
if clips:
    # Concatenate all the clips together
    concatenated_clip = concatenate_mp4_files()
    output_filename = "concatenated_video.mp4"
    concatenated_clip.write_videofile(output_filename, codec="libx264")
