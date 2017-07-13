import httplib2
import sys

from apiclient.discovery import build
from oauth2client import tools
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
import json
import time
import datetime
import string

creds_file = open("credentials.json","r")
creds = json.load( creds_file )
client_id = creds['client_id']
client_secret = creds['client_secret']
creds_file.close()

scope = 'https://www.googleapis.com/auth/youtube.force-ssl'

# Create a flow object. This object holds the client_id, client_secret, and
# scope. It assists with OAuth 2.0 steps to get user authorization and
# credentials.
flow = OAuth2WebServerFlow(client_id, client_secret, scope)

def main():
    youtube = get_authenticated_service()
    comment = open("comment.txt", "r").read()
    channels = open("channels.txt","r").read().split('\n')
    latest_videos = { c: "" for c in channels }
    while True:
        val = check_for_new_videos(youtube, channels, latest_videos)
        latest_videos = val[0]
        newest_video = val[1]
        post_comment_and_upvote(youtube, newest_video, comment)


def get_authenticated_service():

  storage = Storage('credentials.dat')

  credentials = storage.get()

  if credentials is None or credentials.invalid:
    credentials = tools.run_flow(flow, storage, tools.argparser.parse_args())

  http = httplib2.Http()
  http = credentials.authorize(http)

  return build('youtube', 'v3', http=http)

def build_resource(properties):
  resource = {}
  for p in properties:
    # Given a key like "snippet.title", split into "snippet" and "title", where
    # "snippet" will be an object and "title" will be a property in that object.
    prop_array = p.split('.')
    ref = resource
    for pa in range(0, len(prop_array)):
      is_array = False
      key = prop_array[pa]
      # Convert a name like "snippet.tags[]" to snippet.tags, but handle
      # the value as an array.
      if key[-2:] == '[]':
        key = key[0:len(key)-2:]
        is_array = True
      if pa == (len(prop_array) - 1):
        # Leave properties without values out of inserted resource.
        if properties[p]:
          if is_array:
            ref[key] = properties[p].split(',')
          else:
            ref[key] = properties[p]
      elif key not in ref:
        # For example, the property is "snippet.title", but the resource does
        # not yet have a "snippet" object. Create the snippet object here.
        # Setting "ref = ref[key]" means that in the next time through the
        # "for pa in range ..." loop, we will be setting a property in the
        # resource's "snippet" object.
        ref[key] = {}
        ref = ref[key]
      else:
        # For example, the property is "snippet.description", and the resource
        # already has a "snippet" object.
        ref = ref[key]
  return resource

# Remove keyword arguments that are not set
def remove_empty_kwargs(**kwargs):
  good_kwargs = {}
  if kwargs is not None:
    for key, value in kwargs.iteritems():
      if value:
        good_kwargs[key] = value
  return good_kwargs

# Block execution until a new video has been uploaded by a channel in the 
# provided list and returns the video code
def check_for_new_videos(youtube,channels,latest_videos):
    while True:
        for channel in channels:
            print channel
            newest = get_channel_newest_video(youtube, channel)
            if newest[1] != latest_videos[channel]:
                latest_videos[channel] = newest[1]
                return (latest_videos, newest[1])
        time.sleep(1)

def get_channel_id(youtube, video):
    video_response = youtube.videos().list(
            part="snippet",
            id=video
        ).execute()

    return video_response["items"][0]["snippet"]["channelId"]

# Post a comment to a video
def post_comment_and_upvote(youtube, video, comment):
    channel = get_channel_id(youtube, video)
    body = {
             "snippet": {
              "topLevelComment": {
               "snippet": {
                "textOriginal": comment
               }
              },
              "videoId": video,
              "channelId": channel
             }
          }
    comment_response = youtube.commentThreads().insert(
            body=body,
            part="snippet"
        ).execute()

    return comment_response


def get_channel_newest_video(youtube, channelName):
    channels_response = youtube.channels().list(
      forUsername=channelName,
      part="contentDetails"
    ).execute()

    playlistId = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    playlist_videos = []

    playlist_response = youtube.playlistItems().list(
        part="snippet,contentDetails",
        maxResults=50,
        playlistId=playlistId
    ).execute()

    nextPageToken = playlist_response["nextPageToken"]

    while nextPageToken != None:
        playlist_videos = playlist_videos + playlist_response["items"]


        playlist_response = youtube.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=playlistId,
            pageToken=nextPageToken
        ).execute()

        if "nextPageToken" in playlist_response:
            nextPageToken = playlist_response["nextPageToken"]
        else:
            nextPageToken = None

    newest_time = 0
    newest_video = ""
    for video in playlist_videos:
        publishTime = time.mktime( datetime.datetime.strptime( video["contentDetails"]["videoPublishedAt"], "%Y-%m-%dT%H:%M:%S.000Z").timetuple() )
        if publishTime > newest_time:
            newest_time = publishTime
            newest_video = video["contentDetails"]["videoId"]

    return (newest_time, newest_video)

main()
