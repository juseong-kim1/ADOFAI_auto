import os
import shutil
import json
import time
import pyautogui as pg
import math


class AdofaiParser:
    def __init__(self, file):
        file_name = file.split('/')[-1]
        file_dir = file[:-len(file_name)-1]

        # create temporary space
        self.createFolder(file_dir + '/adofai_auto')

        # copy adofai file and change to txt file
        shutil.copyfile(file_dir + '/' + file_name, file_dir + '/adofai_auto/' + file_name)
        self.deleteFile(file_dir + '/adofai_auto/' + file_name.split('.')[0] + '.txt')
        os.rename(file_dir + '/adofai_auto/' + file_name, file_dir + '/adofai_auto/' + file_name.split('.')[0] + '.txt')

        # open adofai file
        print(file_dir + '/adofai_auto/' + file_name.split('.')[0] + '.txt')
        adofai_file = open(file_dir + '/adofai_auto/' + file_name.split('.')[0] + '.txt', 'r', encoding='utf-8-sig')

        # parse data
        self.Data = self.parse(adofai_file.read())

    def __call__(self, *args, **kwargs):
        return self.Data

    def createFolder(self, directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except OSError:
            print('Error: Creating directory. ' + directory)

    def deleteFile(self, directory):
        try:
            if os.path.exists(directory):
                os.remove(directory)
        except OSError:
            print('Error: Deleteing file. ' + directory)

    def parse(self, data):
        data = data.replace('\n', '') \
            .replace(" ", "") \
            .replace("	", "") \
            .replace(',,', ',') \
            .replace(',]', ']') \
            .replace(',}', '}') \
            .replace(']"', '],"')
        return json.loads(data)

class Scripter:
    def __init__(self, data):
        self.DATA = data

    def normalize_degree(self, degree):
        degree = degree % 360
        if degree == 0:
            return 360
        return degree

    def convert_pathData_to_angleData(self, pathData):
        angleData = []
        for c in str(pathData):
            if c == 'R':
                angleData.append(0)
            elif c == 'L':
                angleData.append(180)
            elif c == 'U':
                angleData.append(90)
            elif c == 'D':
                angleData.append(-90)
            elif c == 'E':
                angleData.append(45)
            elif c == 'Q':
                angleData.append(135)
            elif c == 'Z':
                angleData.append(-135)
            elif c == 'C':
                angleData.append(-45)
            elif c == 'J':
                angleData.append(30)
            elif c == 'T':
                angleData.append(60)
            elif c == 'G':
                angleData.append(120)
            elif c == 'H':
                angleData.append(150)
            elif c == 'N':
                angleData.append(-150)
            elif c == 'F':
                angleData.append(-120)
            elif c == 'B':
                angleData.append(-60)
            elif c == 'M':
                angleData.append(-30)
            elif c == 'p':
                angleData.append(15)
            elif c == 'W':
                angleData.append(165)
            elif c == 'V':
                angleData.append(-165)
            elif c == 'A':
                angleData.append(-15)
            elif c == '!':
                angleData.append(999)
            else:
                print(c)
                raise

        return angleData

    # create list of intervals between every key pressing
    def create_keyDelayScript(self):
        # get angle, twirl, bpm,  pitch
        angleData = []
        if 'angleData' in self.DATA.keys():
            angleData = self.DATA['angleData']
        else:
            angleData = self.convert_pathData_to_angleData(self.DATA['pathData'])
        angleData = [0] + angleData

        action_SetSpeed = [None] * len(angleData)
        action_Twirl = [False] * len(angleData)

        bpm = int(self.DATA['settings']['bpm'])
        for action in self.DATA['actions']:

            floor = int(action['floor'])
            if action['eventType'] == 'SetSpeed':
                if action['speedType'] == 'Multiplier':
                    bpm = bpm * action["bpmMultiplier"]
                else:
                    bpm = int(action['beatsPerMinute'])
                action_SetSpeed[floor] = bpm

            if action['eventType'] == 'Twirl':
                action_Twirl[floor] = True

        pitch = int(self.DATA['settings']['pitch'])

        # calculate every time to press key
        spin = -1
        bpm = int(self.DATA['settings']['bpm'])
        Script = []
        floor_tile = None
        for i in range(len(angleData) - 1):
            if action_Twirl[i]:
                spin *= -1
            if action_SetSpeed[i]:
                bpm = action_SetSpeed[i]

            # if this tile is mid-spin
            if angleData[i + 1] == 999:
                floor_tile = angleData[i]
                continue
            # if previous tile was mid-spin
            if angleData[i] == 999:
                pass
            else:
                floor_tile = angleData[i] + 180

            next_tile = angleData[i + 1]
            degree = self.normalize_degree(spin * (next_tile - floor_tile))
            delay = 100 * degree / bpm / pitch / 3  # (100/pitch)*(60/bpm)*degree/180
            Script.append(delay)

        return Script

    # create hand movement script
    def create_handScript(self, len, ONE_HAND_DELAY):
        keyScript = self.create_keyDelayScript() + [0]
        handScript = []

        hand = True
        finger = 0

        time = 0
        hand_time = 0
        for delay in keyScript:
            if hand:
                handScript.append((time, finger))
            else:
                handScript.append((time, len//2+finger))

            time += delay

            if (delay > 2*ONE_HAND_DELAY):
                hand = True
                finger = 0
                continue

            finger += 1

            hand_time += delay
            if (hand_time >= ONE_HAND_DELAY) or finger==len//2:
                hand = not hand
                hand_time = 0
                finger = 0

        return handScript

class AdofaiPlayer:
    def __init__(self, file, keys, mode='rightMain_inside', one_hand_cps=10):
        self.DATA = AdofaiParser(file)()
        self.ONE_HAND_DELAY = 1 / one_hand_cps
        self.KEYS = keys

        scripter = Scripter(self.DATA)

        self.HAND_SCRIPT = scripter.create_handScript(len(self.KEYS), self.ONE_HAND_DELAY)
        self.KEY_GATE = range(len(keys))

        self.MODE = ''
        self.set_mode(mode)


        self.KEY_PRESSED = [False] * len(keys)
        self.KEY_T_RELEASE = [0] * len(keys)

        self.KEY_T_START = [0] * len(keys)
        self.KEY_T = [0] * len(keys)



    def clear_timer(self, n):
        self.KEY_T_START[n] = time.time()
        self.KEY_T[n] = 0

    def update_timer(self):
        for i in range(len(self.KEYS)):
            self.KEY_T[i] = time.time() - self.KEY_T_START[i]

    def set_mode(self, mode):
        l = len(self.KEYS)
        self.KEY_GATE = list(range(l-l//2, l)) + list(range(l//2-1, -1, -1))

    def press(self, key_num, delay, release_self=False):
        if self.KEY_PRESSED[key_num]:
            pg.keyUp(self.KEYS[key_num], _pause=False)
        pg.keyDown(self.KEYS[key_num], _pause=False)
        self.KEY_T_RELEASE[key_num] = delay
        self.KEY_PRESSED[key_num] = True
        self.clear_timer(key_num)

    def release(self):
        self.update_timer()
        for i in range(len(self.KEYS)):
            if self.KEY_PRESSED[i] and self.KEY_T[i] >= self.KEY_T_RELEASE[i]:
                pg.keyUp(self.KEYS[i], _pause=False)
                self.KEY_PRESSED[i] = False

    def modify_key(self, n):
        return self.KEY_GATE[n]

    def play(self, wait):
        bpm = int(self.DATA['settings']['bpm'])
        pitch = int(self.DATA['settings']['pitch'])
        countdownTicks = int(self.DATA['settings']['countdownTicks'])
        offset = int(self.DATA['settings']['offset'])

        pg.press('space')
        start = time.time()
        t = 0
        while t < countdownTicks * 60 / bpm * 100 / pitch + offset*0.001 + wait:
            t = time.time() - start

        print('start')
        start = time.time()
        t = 0
        i = 1
        while i < len(self.HAND_SCRIPT):
            block = self.HAND_SCRIPT[i]
            if t >= block[0]:
                block = self.HAND_SCRIPT[i]
                print('press', self.KEYS[self.modify_key(block[1])], block[0])
                self.press(self.modify_key(block[1]), self.ONE_HAND_DELAY / 2)
                i += 1

            self.release()
            t = time.time() - start