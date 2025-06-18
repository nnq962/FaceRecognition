from speaker_recognition.speaker_recognition import SpeakerRecognition

obj = SpeakerRecognition()


print(obj.extract_embedding("test.m4a").embedding)