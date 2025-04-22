import gspread, os, datetime, subprocess
from llm_writer import make_script
from voice_maker import tts
from podcast_uploader import upload
from pydub import AudioSegment

# 1) Read next topic from Google Sheet
svc_key = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]   # path we injected
gc = gspread.service_account(filename=svc_key)                # uses creds in GOOGLE_APPLICATION_CREDENTIALS
sheet = gc.open_by_key(os.getenv("GSHEET_ID")).sheet1
topic = sheet.row_values(2)[0]                # cell A2 holds newest idea

print("Topic picked:", topic)

# 2) Generate script
script = make_script(topic)
open("script.json", "w").write(str(script))

# 3) TTS voice‑over
tts(script["full_script"], "voice.wav")

# 4) Concatenate intro + voice + outro, normalise loudness
intro = AudioSegment.from_mp3("assets/intro.mp3")
outro = AudioSegment.from_mp3("assets/outro.mp3")
voice = AudioSegment.from_wav("voice.wav")
final = intro + voice + outro
final.export("episode.mp3", format="mp3", bitrate="128k")

# 5) Upload
upload("episode.mp3", script["title"], script["description"])

print("Episode published ✔")
