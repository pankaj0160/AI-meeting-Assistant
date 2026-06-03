import whisper

print("Loading Whisper model...")
model = whisper.load_model("base")


def transcribe_audio(audio_file: str) -> str:

    print("Transcribing audio...")

    result = model.transcribe(str(audio_file))

    return result["text"]