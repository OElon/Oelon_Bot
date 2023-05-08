import tweepy
from dotenv import load_dotenv
import os
import re
import openai
import requests
from io import BytesIO
from typing import Dict
import time

class MyStreamListener(tweepy.Stream):
    def __init__(self, api, openai_api_key, dall_e_api_key):
        super().__init__(api)
        self.openai_api_key = openai_api_key
        self.dall_e_api_key = dall_e_api_key
        self.last_reply_time = time.time()

    def on_status(self, status):
        if status.user.screen_name == '@_oelon_':
            if time.time() - self.last_reply_time > 4.20 * 60:
                tweet_text = status.text
                try:
                    reply_text, image_url = generate_reply(tweet_text, self.openai_api_key, self.dall_e_api_key)
                except Exception as e:
                    print(f"Error generating reply: {e}")
                    return
                
                try:
                    # Download image from URL
                    response = requests.get(image_url)
                    img = BytesIO(response.content)

                    # Update status with reply and image
                    api.update_with_media(filename='dall-e-image.jpg', status=reply_text, file=img.read(), in_reply_to_status_id=status.id, auto_populate_reply_metadata=True)

                    self.last_reply_time = time.time()
                except requests.exceptions.RequestException as e:
                    print(f"Network error: {e}")
                except tweepy.TweepError as e:
                    print(f"Error sending reply: {e}")
            else:
                print("Rate limited. Skipping reply.")

    def on_error(self, status_code):
        if status_code == 420:
            return False

def generate_reply(tweet_text: str, openai_api_key: str, dall_e_api_key: str) -> str:
    # Format prompt for generating sarcastic reply
    prompt = f"As Elon Musk would say, '{re.sub('[^0-9a-zA-Z]+', ' ', tweet_text)}' is just SOOOO impressive! 😒🙄 #sarcasm #ElonMusk"

    # Generate completion using OpenAI API
    try:
        openai.api_key = openai_api_key
        response: Dict = openai.Completion.create(
            engine="davinci",
            prompt=prompt,
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.5,
        )

        # Extract generated text from response
        reply_text = response.choices[0].text.strip()

        # Generate image using DALL-E API
        response = requests.post("https://api.openai.com/v1/images/generations", headers={"Authorization": f"Bearer {dall_e_api_key}"}, json={
            "model": "image-alpha-001",
            "prompt": f"Generate an image to accompany the tweet: '{tweet_text}'",
            "num_images": 1,
            "size": "512x512",
            "response_format": "url"
        })
        image_url = response.json()['data'][0]['url']

    except (openai.Error, requests.exceptions.RequestException) as e:
        print(f"Error generating reply: {e}")
        raise
    
    except (KeyError, IndexError) as e:
        print(f"Invalid API response: {e}")
        raise

    return reply_text, image_url


if __name__ == '__main__':
    # Load environment variables from .env file
    load_dotenv()
     
    # Check if environment variables for Twitter and API keys are present
    required_env_vars = ['CONSUMER_KEY', 'CONSUMER_SECRET', 'ACCESS_TOKEN', 'ACCESS_TOKEN_SECRET', 'OPENAI_API_KEY', 'DALL_E_API_KEY']
    for var in required_env_vars:
        if var not in os.environ:
            print(f"Error: {var} environment variable not found.")
            exit()

    # Initialize Twitter API
    auth = tweepy.OAuthHandler(os.getenv('CONSUMER_KEY'), os.getenv('CONSUMER_SECRET'))
    auth.set_access_token(os.getenv('ACCESS_TOKEN'), os.getenv('ACCESS_TOKEN_SECRET'))
    api = tweepy.API(auth)

    # Initialize stream listener
    myStreamListener = MyStreamListener(api, os.getenv('OPENAI_API_KEY'), os.getenv('DALL_E_API_KEY'))

    # Start stream listener
    myStream = tweepy.Stream(auth=api.auth, listener=myStreamListener)

    # Try to filter the stream with the given track
    try:
        myStream.filter(track=['@YOUR_TWITTER_HANDLE'])
    except requests.exceptions.RequestException as e:
        print(f"Error: Network error occurred. {e}")
    except tweepy.TweepError as e:
        print(f"Error: Tweepy error occurred. {e}")
    except Exception as e:
        print(f"Error: Unexpected error occurred. {e}")


