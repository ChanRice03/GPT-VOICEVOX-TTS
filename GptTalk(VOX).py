import pyaudio
import wave
import requests
import json
import whisper
import time
from openai import OpenAI
import re
import simpleaudio as sa  # wav 바로 재생

# 위스퍼 모델
model = whisper.load_model("medium")

# OpenAi Assistant Ai
client = OpenAI(api_key='')  # Api 키 입력
assistant = client.beta.assistants.retrieve(assistant_id='')  # Api 키 입력
thread = client.beta.threads.retrieve(thread_id="") #Api 키 입력


# Voicevox 로컬 주소 설정
host = "127.0.0.1"
port = "50021"
ngrok = "http://127.0.0.1:50021" #ngrok으로 주소 변경 가능


# Voicevox 음성 합성 함수 (로컬 API 사용)
def save_voice_with_voicevox_local(text: str, output_filename: str = "voice.wav", speaker: int = 79):  #int 값으로 모델 설정
    # VOICEVOX audio_query 호출
    params = {"text": text, "speaker": speaker}
    audio_query_response = requests.post(f"{ngrok}/audio_query", params=params)
    audio_query_response.raise_for_status()
    audio_query_data = audio_query_response.json()
    audio_query_data["speedScale"] = 1.1


    # VOICEVOX synthesis 호출
    headers = {"content-type": "application/json"}
    synthesis_response = requests.post(
        f"{ngrok}/synthesis",
        params={"speaker": speaker},
        data=json.dumps(audio_query_data),
        headers=headers,
    )
    synthesis_response.raise_for_status()


    # 결과를 파일로 저장
    with open(output_filename, "wb") as f:
        f.write(synthesis_response.content)




def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        time.sleep(0.5)
    return run


# 위스퍼 사전 세팅 및 실행 함수
def transcribe_and_synthesize():
    sample_rate = 16000
    bits_per_sample = 16
    chunk_size = 1024
    audio_format = pyaudio.paInt16
    channels = 1

    def callback(in_data, frame_count, time_info, status):
        wav_file.writeframes(in_data)
        return None, pyaudio.paContinue

    # wav 파일 세팅
    wav_file = wave.open('./output.wav', 'wb')
    wav_file.setnchannels(channels)
    wav_file.setsampwidth(bits_per_sample // 8)
    wav_file.setframerate(sample_rate)

    # PyAudio 녹음 시작
    audio = pyaudio.PyAudio()
    stream = audio.open(format=audio_format,
                        channels=channels,
                        rate=sample_rate,
                        input=True,
                        frames_per_buffer=chunk_size,
                        stream_callback=callback)

    print("녹음중... 'Enter'로 중지.")
    input()  # 정지 버튼

    # 녹음중지
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # wav 파일로 저장 완료
    wav_file.close()

    print("오디오 번역중...")
    audio_file = open('output.wav', "rb")
    transcribed_text = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="text",
        language="ja"
    )
    print(f"번역된 텍스트: {transcribed_text}")

    print("GPT로 보내는중...")
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role='user',
        content=transcribed_text
    )

    # GPT id 매칭 및 실행 대기
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )
    
    wait_on_run(run, thread)

    
    messages = client.beta.threads.messages.list(
        thread_id=thread.id, order="asc", after=message.id
    )

    # 답변 정리(안하면 다른 문자들도 다 딸려옴)
    response_text = ""
    for message in messages:
        for c in message.content:
            response_text += c.text.value
    
    clean_text = re.sub('【.*?】', '', response_text)
    
    print(f"GPT 답변: {clean_text}")

    print("음성 변환중...")

    # Voicevox로 음성 저장 (동기 실행)
    save_voice_with_voicevox_local(clean_text)

    
    print("음성 저장 성공 'voice.wav'.")

    # 바로 자동재생
    wave_obj = sa.WaveObject.from_wave_file("voice.wav")
    play_obj = wave_obj.play()
    play_obj.wait_done()


if __name__ == "__main__":
    transcribe_and_synthesize()