
import os
import time
import sys
import qi

IP = "192.168.8.101"
PORT = 9559
PHOTO_PATH = "/home/nao/recordings/cameras/"
STATES = {0: "wait_for_new_customer", 1: "wait_for_ready", 2: "wait_until_they_smile", 3: "wait_for_goodbye"}


class Photographer(object):

    def __init__(self, app):
        super(Photographer, self).__init__()
        app.start()
        self.state = 0

        session = app.session
        self.memory = session.service("ALMemory")
        self.tts = session.service("ALAnimatedSpeech")
        self.awareness = session.service("ALBasicAwareness")

        # Setting the Speech Recognition Service
        self.sr_service = session.service("ALSpeechRecognition")
        self.sr_service.deleteAllContextSets()
        self.sr_service.setLanguage("English")
        self.sr_service.pause(True)
        self.sr_service.setVocabulary(["I am ready.", "Goodbye Ginger!"], False)
        self.sr_service.pause(False)
        self.sr_service.subscribe("Photographer")

        # Connecting a callback function to FaceDetected signal
        self.face_subscriber = self.memory.subscriber("FaceDetected")
        self.face_subscriber.signal.connect(self.on_face_detected)

        # Connecting a callback function to PersonSmiling signal
        self.smile_subscriber = self.memory.subscriber("FaceCharacteristics/PersonSmiling")
        self.smile_subscriber.signal.connect(self.on_smile)

        # Setting the Face Characteristics Service
        self.face_char = session.service("ALFaceCharacteristics")
        self.face_char.subscribe("Photographer")
        self.face_char.setSmilingThreshold(0.5)

        # Setting the Face Detection Service
        self.face_detection = session.service("ALFaceDetection")
        self.face_detection.subscribe("Photographer")

        # Connecting a callback function to WordRecognized signal
        self.word_recognizer = self.memory.subscriber("WordRecognized")
        self.word_recognizer.signal.connect(self.on_word_recognized)

        # Setting the Photo Capture Service
        self.photo_capture = session.service("ALPhotoCapture")
        self.photo_capture.setPictureFormat("jpg")

    def next_state(self):
        next_state = (self.state + 1) % len(STATES)
        print("State changed from", STATES[self.state], "to", STATES[next_state])
        self.state = None
        return next_state
        
    def on_face_detected(self, value):
        if STATES[self.state] == "wait_for_new_customer" and value != []: 
            next_state = self.next_state()
            self.tts.say("^start(animations/Stand/Gestures/Hey_1) Welcome my friend!")
            time.sleep(1)
            self.tts.say("Please say 'I am ready' when you are ready.")
            self.state = next_state
       
    def on_word_recognized(self, value):
        if STATES[self.state] == "wait_for_ready" and "ready" in value[0] and value[1] > 0.3:
            next_state = self.next_state()
            self.tts.say("Now, please look at me and smile.") 
            self.state = next_state
        elif STATES[self.state] == "wait_for_goodbye" and "Goodbye" in value[0] and value[1] > 0.3:
            next_state = self.next_state()
            self.tts.say("Goodbye my friend!") 
            self.awareness.pauseAwareness()
            time.sleep(10)
            self.awareness.resumeAwareness()
            self.state = next_state

    def on_smile(self, value):
        if STATES[self.state] == "wait_until_they_smile":
            next_state = self.next_state()
            file_name = "photo_" + str(int(round(time.time())))
            self.photo_capture.takePicture(PHOTO_PATH, file_name)
            self.tts.say("I took your photo")   
            os.system('sshpass -p "nao" scp nao@' + IP + ':' + PHOTO_PATH + file_name + '.jpg .')
            self.state = next_state

    def run(self):
        print("Starting Photographer")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Interrupted by user, stopping Photographer")
            sys.exit(0)

photographer = Photographer(qi.Application(["Photographer", "--qi-url=" + "tcp://" + IP + ":" + str(PORT)]))
photographer.run()
