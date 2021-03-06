#!/usr/bin/python3
# This Python file uses the following encoding: utf-8
from PyQt5 import QtCore, QtWidgets, uic, QtGui
from PyQt5.QtWidgets import QInputDialog, QFileDialog, QApplication, QMainWindow, QSpinBox, QCheckBox
from functools import partial

import sys
from mainwindow import Ui_qencoder

from pav1n import Av1an

import traceback

import multiprocessing
from threading import Thread

from types import SimpleNamespace
from pathlib import Path
import os

import pickle

#baseUIClass, baseUIWidget = uic.loadUiType("mainwindow.ui")

class window(QMainWindow, Ui_qencoder):
    twopassState = True
    realtimeState = False
    qualityState = 3
    audioState = 4
    runningEncode = False
    encodeList = []
    currentFile = ""
    if 'APPDATA' in os.environ:
        confighome = os.environ['APPDATA']
    elif 'XDG_CONFIG_HOME' in os.environ:
        confighome = os.environ['XDG_CONFIG_HOME']
    else:
        confighome = os.path.join(os.environ['HOME'], '.config')
    configpath = os.path.join(confighome, 'qencoder.qec')

    def __init__(self, *args, **kwargs):
        if __name__ == '__main__':
            QMainWindow.__init__(self, *args, **kwargs)
            self.setupUi(self)
            self.inputFileChoose.clicked.connect(self.inputFileSelect)
            self.outputFileChoose.clicked.connect(self.outputFileSelect)
            self.label_audio.setEnabled(0)
            self.spinBox_quality.setValue(26)
            enable_slot = partial(self.audioEnableState, self.checkBox_audio)
            disable_slot = partial(self.audioDisableState, self.checkBox_audio)
            self.checkBox_audio.stateChanged.connect(lambda x: enable_slot() if x else disable_slot())

            enable_slot2 = partial(self.bitrateEnableState, self.checkBox_bitrate)
            disable_slot2 = partial(self.bitrateDisableState, self.checkBox_bitrate)
            self.checkBox_bitrate.stateChanged.connect(lambda x: enable_slot2() if x else disable_slot2())

            self.pushButton.clicked.connect(self.encodeVideo)
            
            self.audioqualitybox.activated[int].connect(self.changeAudioPreset)
            
            self.comboBox_quality.activated[int].connect(self.changeQPreset)
            
            self.presetbox.activated[int].connect(self.changePresetSimple)

            self.comboBox_colorspace.activated[int].connect(self.changeColorspace)

            self.comboBox_encoder.activated[int].connect(self.changeEncoder)

            self.audioqualitybox.setEnabled(0)
            self.label_audioquality.setEnabled(0)
            self.spinBox_speed.valueChanged.connect(self.changePresetAdvanced)
            self.spinBox_quality.valueChanged.connect(self.customQPreset)
            self.spinBox_audio.valueChanged.connect(self.customAPreset)
            self.checkBox_rtenc.stateChanged.connect(self.changeRTState)
            self.checkBox_videocmd.stateChanged.connect(self.customVidCmd)
            self.checkBox_audiocmd.stateChanged.connect(self.customAudCmd)
            self.checkBox_ffmpegcmd.stateChanged.connect(self.customFFCmd)
            self.actionOpen.triggered.connect(self.inputFileSelect)
            self.actionSave.triggered.connect(self.outputFileSelect)
            self.actionExit.triggered.connect(self.quitProgram)
            self.actionSave_Queue.triggered.connect(self.saveQueueAuto)
            self.actionSave_Queue_As.triggered.connect(self.saveQueueTo)
            self.actionOpen_Queue.triggered.connect(self.openQueueFrom)
            self.pushButton_save.setEnabled(0)
            self.pushButton_save.clicked.connect(self.saveToQueue)
            self.tabWidget.currentChanged[int].connect(self.setCustomText)
            self.pushButton_up.clicked.connect(self.queueMoveUp)
            self.pushButton_down.clicked.connect(self.queueMoveDown)
            self.pushButton_del.clicked.connect(self.removeFromQueue)
            self.actionSave_Preset.triggered.connect(self.savePresetAs)
            self.actionOpen_Preset.triggered.connect(self.openPresetFrom)

            #this dictionary will be use to map combobox index into a values
            self.qualitydict = {
                0: 40,
                1: 36,
                2: 32,
                3: 28,
                4: 26,
                5: 24,
                6: 20,
                7: 10,
                8: 0
            }

            self.audiobitratedict = {
                0: 24,
                1: 32,
                2: 64,
                3: 76,
                4: 96,
                5: 128,
                6: 160,
                7: 250
            }

            self.colorspacedict = {
                0: ["", "--color-space=unknown"],
                1: ["--color-primaries=bt709 --transfer-characteristics=bt709 --matrix-coefficients=bt709", "--color-space=bt709"],
                2: ["--color-primaries=bt601 --transfer-characteristics=bt601 --matrix-coefficients=bt601", "--color-space=bt601"],
                3: ["--color-primaries=bt2020 --transfer-characteristics=bt2020-10bit --matrix-coefficients=bt2020ncl", "--color-space=bt2020"],
                4: ["--color-primaries=bt2020 --transfer-characteristics=bt2020-10bit --matrix-coefficients=bt2020cl", "--color-space=bt2020"]
            }

            try:
                filehandler = open(self.configpath, 'rb')
                settings = pickle.load(filehandler)
                self.setFromPresetDict(settings)
            except:
                print("Unable to load existing preset at: " + str(self.configpath) + ".")
                print("Possibly the first time you have run this, corrupted, or an older version")
                print("Do not report this")
            # self.speedButton.changeEvent.connect(self.setSpeed)

    def encodeFinished(self, success):
        if success:
            self.pushButton.setEnabled(1)
            self.pushButton.setStyleSheet("color: black; background-color: white")
            self.pushButton.setText("Finalize")
            self.label_status.setText("Encoding complete!")
        else:
            self.pushButton.setEnabled(1)
            self.pushButton.setStyleSheet("color: red; background-color: white")
            self.pushButton.setText("Reset")
            self.label_status.setText("ERR. See temp/log.log")

    def updateStatusProgress(self, status, progress):
        self.label_status.setText(status)
        self.progressBar_total.setValue(progress)

    def updateQueuedStatus(self, queueString):
        self.label_queueprog.setText(queueString)

    def openPresetFrom(self):
        filename = QFileDialog.getOpenFileName(filter = "Qencoder encoder config (*.qec)")
        newlist = []
        if (filename[0].endswith(".qec")):
            pass
        elif (len(filename[0]) > 0):
            self.outputPath.setText(filename[0] + ".qec")
        else:
            return
        filehandler = open(filename[0], 'rb')
        tempdict = pickle.load(filehandler)
        self.setFromPresetDict(tempdict)

    def savePresetAs(self):
        filename = QFileDialog.getSaveFileName(filter = "Qencoder encoder config (*.qec)")
        if (filename[0].endswith(".qec")):
            pass
        elif (len(filename[0]) > 0):
            self.outputPath.setText(filename[0] + ".qec")
        else:
            return
        file_pi = open(filename[0], 'wb')
        pickle.dump(self.getPresetDict(), file_pi)

    def closeEvent(self, event):
        print("Writing current settings to config")
        curSettings = self.getPresetDict()
        file_pi = open(self.configpath, 'wb')
        pickle.dump(curSettings, file_pi)

    def saveQueueAuto(self):
        if (len(self.currentFile) < 1):
            self.saveQueueTo()
        else:
            file_pi = open(self.currentFile, 'wb')
            pickle.dump(self.encodeList, file_pi)

    def saveQueueTo(self):
        filename = QFileDialog.getSaveFileName(filter = "Qencoder encoder queue data (*.eqd)")
        if (filename[0].endswith(".eqd")):
            pass
        elif (len(filename[0]) > 0):
            self.outputPath.setText(filename[0] + ".eqd")
        else:
            return
        file_pi = open(filename[0], 'wb')
        pickle.dump(self.encodeList, file_pi)
        self.currentFile = filename[0]

    def openQueueFrom(self):
        filename = QFileDialog.getOpenFileName(filter = "Qencoder encoder queue data (*.eqd)")
        newlist = []
        if (filename[0].endswith(".eqd")):
            pass
        elif (len(filename[0]) > 0):
            self.outputPath.setText(filename[0] + ".eqd")
        else:
            return
        filehandler = open(filename[0], 'rb')
        self.encodeList = pickle.load(filehandler)
        self.currentFile = filename[0]
        self.redrawQueueList()

    def queueMoveUp(self):
        if (self.listWidget.currentRow() > 0):
            self.encodeList[self.listWidget.currentRow()], self.encodeList[self.listWidget.currentRow() - 1] = self.encodeList[self.listWidget.currentRow() - 1], self.encodeList[self.listWidget.currentRow()]
            self.redrawQueueList()

    def queueMoveDown(self):
        if (self.listWidget.currentRow() < (self.listWidget.count() - 1)):
            self.encodeList[self.listWidget.currentRow()], self.encodeList[self.listWidget.currentRow() + 1] = self.encodeList[self.listWidget.currentRow() + 1], self.encodeList[self.listWidget.currentRow()]
            self.redrawQueueList()

    def removeFromQueue(self):
        if (len(self.encodeList) > 0) :
            index = self.listWidget.currentRow()
            del self.encodeList[index]
            self.redrawQueueList()

    def saveToQueue(self):
        self.encodeList.append(self.getArgs())
        self.redrawQueueList()
        self.outputPath.setText("")
        self.pushButton.setEnabled(1)
        self.pushButton_save.setEnabled(0)

    def redrawQueueList(self):
        self.listWidget.clear()
        for i in self.encodeList:
            inputFile = i['input_file'].parts[-1]
            outputFile = i['output_file'].parts[-1]
            finalString = inputFile + " -> " + outputFile
            self.listWidget.addItem(finalString)
        if (len(self.encodeList) > 0):
            self.pushButton.setEnabled(1)
        else:
            self.pushButton.setEnabled(0)

    def quitProgram(self):
        sys.exit(0)

    def customVidCmd(self, newState):
        self.textEdit_videocmd.setEnabled(newState)
        if (not newState):
            self.textEdit_videocmd.setPlainText(self.getVideoParams())

    def customFFCmd(self, newState):
        self.textEdit_ffmpegcmd.setEnabled(newState)
        if (not newState):
            self.textEdit_ffmpegcmd.setPlainText(self.getFFMPEGParams())

    def customAudCmd(self, newState):
        self.textEdit_audiocmd.setEnabled(newState)
        if (not newState):
            self.textEdit_audiocmd.setPlainText(self.getAudioParams())


    def setCustomText(self, i):
        self.textEdit_ffmpegcmd.setPlainText(self.getFFMPEGParams())
        self.textEdit_videocmd.setPlainText(self.getVideoParams())
        self.textEdit_audiocmd.setPlainText(self.getAudioParams())

    def getCPUUsed(self):
        if (self.presetbox.currentIndex() == 9):
            return self.spinBox_speed.value()
        if (self.comboBox_encoder.currentIndex() == 0):
            return (8 - self.presetbox.currentIndex())
        if (self.comboBox_encoder.currentIndex() == 1):
            return -int((self.presetbox.currentIndex() - 4) * 2.25)  # Maps the presets between -9 and 9
        if (self.comboBox_encoder.currentIndex() == 2):
            return -int((self.presetbox.currentIndex() - 4) * 4.125)  # Maps the presets between -16 and 16
        return 0
    def getColorData(self):
        #Get indexes of current colorspace comboBox
        inputSpace = self.comboBox_colorspace.currentIndex()
        # if colorspace index is 5 uses a custom value set by the user
        if (inputSpace == 5):
            return self.lineEdit_colordata.text()
        #return empty string if current encoder combobox indexes is 2 
        if (self.comboBox_encoder.currentIndex() == 2):
            return ""
        #else map the colorspace index into a list of av1,vp9 color space then return the appropriate string based on the encoder
        else:
            return self.colorspacedict[inputSpace][self.comboBox_encoder.currentIndex()]

    def changeEncoder(self, newencoder):
        spdpreset = self.presetbox.currentIndex()
        if (newencoder == 0):
            self.spinBox_speed.setMaximum(8)
            self.spinBox_speed.setMinimum(0)
        elif (newencoder == 1):
            self.spinBox_speed.setMaximum(9)
            self.spinBox_speed.setMinimum(-9)
        else:
            self.spinBox_speed.setMaximum(16)
            self.spinBox_speed.setMinimum(-16)
        self.spinBox_speed.setValue(self.getCPUUsed())
        self.lineEdit_colordata.setText(self.getColorData())
        self.presetbox.setCurrentIndex(spdpreset)
        self.changePresetSimple(spdpreset)
        if (newencoder > 1):
            self.comboBox_colorspace.setCurrentIndex(0)
            self.comboBox_colorspace.setEnabled(0)
            self.lineEdit_colordata.setEnabled(0)
            self.label_2.setEnabled(0)
        else:
            self.comboBox_colorspace.setEnabled(1)
            if (self.comboBox_colorspace.currentIndex() == 5):
                self.lineEdit_colordata.setEnabled(1)
            self.label_2.setEnabled(1)

    def changeColorspace(self, newspace):
        colorInfo = self.getColorData()
        self.lineEdit_colordata.setText(colorInfo)
        if (newspace == 5):
            self.lineEdit_colordata.setEnabled(1)
        else:
            self.lineEdit_colordata.setEnabled(0)

    def changeRTState(self, newState):
        if (newState):
            if (self.checkBox_twopass.isEnabled()):
                self.twopassState = self.checkBox_twopass.isChecked()
            self.checkBox_twopass.setChecked(0)
            self.checkBox_twopass.setEnabled(0)
        else:
            self.checkBox_twopass.setChecked(self.twopassState)
            self.checkBox_twopass.setEnabled(1)

    def customAPreset(self):
        self.audioqualitybox.setCurrentIndex(7)  # custom

    def changeAudioPreset(self, i):
        self.audioState = i
        trueQuality = self.getAudioBitrate(i)
        print(str(trueQuality) + " is current quality")
        self.spinBox_audio.setValue(trueQuality)
        self.audioqualitybox.setCurrentIndex(i)

    def customQPreset(self):
        self.comboBox_quality.setCurrentIndex(9)  # custom

    def changeQPreset(self, i):
        trueQuality = self.getQuality(i)
        self.spinBox_quality.setValue(trueQuality)
        self.qualityState = i
        self.comboBox_quality.setCurrentIndex(i)

    def changePresetAdvanced(self):
        if (self.spinBox_speed.value() > 6 and self.comboBox_encoder.currentIndex() == 0):
            if (self.checkBox_rtenc.isEnabled()):
                self.realtimeState = self.checkBox_rtenc.isChecked()
            if (self.checkBox_twopass.isEnabled()):
                self.twopassState = self.checkBox_twopass.isChecked()
            self.checkBox_twopass.setChecked(0)
            self.checkBox_twopass.setEnabled(0)
            self.checkBox_rtenc.setChecked(1)
            self.checkBox_rtenc.setEnabled(0)
        else:
            if (self.checkBox_rtenc.isEnabled()):
                self.realtimeState = self.checkBox_rtenc.isChecked()
            if (self.checkBox_twopass.isEnabled()):
                self.twopassState = self.checkBox_twopass.isChecked()
            self.checkBox_twopass.setChecked(self.twopassState)
            self.checkBox_twopass.setEnabled(1)
            self.checkBox_rtenc.setEnabled(1)
            self.checkBox_rtenc.setChecked(self.realtimeState)
        self.presetbox.setCurrentIndex(9)

    def changePresetSimple(self, i):
        if (i <= 1 and self.comboBox_encoder.currentIndex() == 0):
            if (self.checkBox_rtenc.isEnabled()):
                self.realtimeState = self.checkBox_rtenc.isChecked()
            if (self.checkBox_twopass.isEnabled()):
                self.twopassState = self.checkBox_twopass.isChecked()
            self.checkBox_twopass.setChecked(0)
            self.checkBox_twopass.setEnabled(0)
            self.checkBox_rtenc.setEnabled(0)
            self.checkBox_rtenc.setChecked(1)
        else:
            if (self.checkBox_rtenc.isEnabled()):
                self.realtimeState = self.checkBox_rtenc.isChecked()
            if (self.checkBox_twopass.isEnabled()):
                self.twopassState = self.checkBox_twopass.isChecked()
            self.checkBox_twopass.setChecked(self.twopassState)
            self.checkBox_twopass.setEnabled(1)
            self.checkBox_rtenc.setEnabled(1)
            self.checkBox_rtenc.setChecked(self.realtimeState)
        self.spinBox_speed.setValue(self.getCPUUsed())
        self.presetbox.setCurrentIndex(i)

    def getAudioBitrate(self, iindex):
        if (iindex < 8):
            return self.audiobitratedict[iindex]
        else:
            return self.spinBox_audio.value()

    def getQuality(self, qval):
        if (qval < 9):
            return self.qualitydict[qval]
        else:
            return self.spinBox_quality.value()

    def inputFileSelect(self):
        filename = QFileDialog.getOpenFileName(filter = "Videos(*.mp4 *.mkv *.webm *.flv *.gif *.3gp *.wmv *.avi);;All(*)")
        self.inputPath.setText(filename[0])
        if (len(self.outputPath.text()) > 1):
            self.pushButton.setEnabled(1)
            self.pushButton_save.setEnabled(1)

    def outputFileSelect(self):
        filename = QFileDialog.getSaveFileName(filter = "mkv and webm videos(*.mkv *.webm)")
        if (filename[0].endswith(".mkv") or filename[0].endswith(".webm")):
            self.outputPath.setText(filename[0])
        elif (len(filename[0]) > 0):
            self.outputPath.setText(filename[0] + ".mkv")
        if (len(self.inputPath.text()) > 1):
            self.pushButton.setEnabled(1)
            self.pushButton_save.setEnabled(1)

    def audioEnableState(self, checkbox):
        self.label_audio.setEnabled(1)
        self.spinBox_audio.setReadOnly(0)
        self.audioqualitybox.setEnabled(1)
        self.label_audioquality.setEnabled(1)
        self.spinBox_audio.setEnabled(1)

    def audioDisableState(self, checkbox):
        self.label_audio.setEnabled(0)
        self.spinBox_audio.setReadOnly(1)
        self.audioqualitybox.setEnabled(0)
        self.label_audioquality.setEnabled(0)
        self.spinBox_audio.setEnabled(0)

    def bitrateEnableState(self, checkbox):
        self.label_q.setText("Bitrate (kbps)")
        self.spinBox_quality.setMaximum(99999)
        self.spinBox_quality.setMinimum(8)
        self.spinBox_quality.setValue(3000)
        self.spinBox_boost.setReadOnly(1)
        self.label_boost.setEnabled(0)
        self.comboBox_quality.setCurrentIndex(9)  # custom
        self.comboBox_quality.setEnabled(0)
        self.label_quality.setEnabled(0)

    def bitrateDisableState(self, checkbox):
        self.label_q.setText("Q factor")
        self.spinBox_quality.setMaximum(63)
        self.spinBox_quality.setMinimum(0)
        self.spinBox_quality.setValue(30)
        self.spinBox_boost.setReadOnly(0)
        self.label_boost.setEnabled(1)
        self.comboBox_quality.setEnabled(1)
        self.label_quality.setEnabled(1)

    def getFFMPEGParams(self):
        if (self.checkBox_ffmpegcmd.isChecked()):
            return self.textEdit_ffmpegcmd.toPlainText()
        return ""

    def getVideoParams(self):
        if (self.checkBox_videocmd.isChecked()):
            return self.textEdit_videocmd.toPlainText()
        vparams = "--threads=" + str(self.spinBox_threads.value())
        if (self.comboBox_encoder.currentIndex() < 2):
            vparams += " --tile-columns=2 --tile-rows=1 --cpu-used=" + str(self.spinBox_speed.value())
        else:
            vparams += " --codec=vp8 --cpu-used=" + str(self.spinBox_speed.value())

        if (self.comboBox_encoder.currentIndex() == 1):
            vparams += " --codec=vp9"

        if (self.checkBox_rtenc.isChecked()):
            vparams += " --rt"
        else:
            vparams += " --good"
        if (self.checkBox_bitrate.isChecked()):
            vparams += " --end-usage=vbr --target-bitrate=" + str(self.spinBox_quality.value())
        else :
            vparams += " --end-usage=q --cq-level=" + str(self.spinBox_quality.value())
        if (self.checkBox_hdr.isChecked()):
            vparams += " --bit-depth=10 "
        else :
            vparams += " --bit-depth=8 "
        vparams += self.lineEdit_colordata.text()
        if (self.comboBox_inputFormat.currentIndex() <= 2):
            vparams += " --i420"
        elif (self.comboBox_inputFormat.currentIndex() <= 5):
            vparams += " --i422"
        else:
            vparams += " --i444"
        return vparams

    def getAudioParams(self):
        if (self.checkBox_audiocmd.isChecked()):
            return self.textEdit_audiocmd.toPlainText()
        if (self.checkBox_audio.isChecked()):
            return "-b:a " + str(self.spinBox_audio.value()) + " -c:a libopus"
        else :
            return "-c:a copy"

    def setFromPresetDict(self, dict):
        self.comboBox_encoder.setCurrentIndex(dict['enc'])
        self.audioqualitybox.setCurrentIndex(dict['aq'])
        self.presetbox.setCurrentIndex(dict['preset'])
        self.comboBox_quality.setCurrentIndex(dict['vq'])
        self.checkBox_bitrate.setChecked(dict['brmode'])
        self.checkBox_hdr.setChecked(dict['10b'])
        self.checkBox_resume.setChecked(dict['resume'])
        self.checkBox_tempfolder.setChecked(dict['keeptmp'])
        self.checkBox_rtenc.setChecked(dict['rtenc'])
        self.twopassState = dict['2p']
        self.realtimeState = dict['rtenc']
        self.checkBox_twopass.setChecked(dict['2p'])
        if (self.twopassState and self.realtimeState):
            self.twopassState = True
            self.realtimeState = False
            self.checkBox_rtenc.setChecked(False)
            self.checkBox_twopass.setChecked(True)
            print ("Resetting invalid twopass and realtime state combos")
        self.checkBox_minsplit.setChecked(dict['minsplit'])
        self.spinBox_split.setValue(dict['splittr'])
        self.spinBox_speed.setValue(dict['cpuused'])
        self.spinBox_jobs.setValue(dict['jobs'])
        self.spinBox_audio.setValue(dict['audiobr'])
        self.spinBox_boost.setValue(dict['boost'])
        self.spinBox_threads.setValue(dict['threads'])
        self.checkBox_audio.setChecked(dict['audio'])
        self.spinBox_quality.setValue(dict['qual'])
        self.checkBox_videocmd.setChecked(dict['cusvid'])
        self.checkBox_audiocmd.setChecked(dict['cusaud'])
        self.checkBox_ffmpegcmd.setChecked(dict['cusffmpeg'])
        self.textEdit_videocmd.setPlainText(dict['vidcmd'])
        self.textEdit_audiocmd.setPlainText(dict['audcmd'])
        self.textEdit_ffmpegcmd.setPlainText(dict['ffmpegcmd'])

    def getPresetDict(self):
        return {'2p': self.checkBox_twopass.isChecked(), 'audio': self.checkBox_audio.isChecked(), 'enc': self.comboBox_encoder.currentIndex(),
                'aq' : self.audioqualitybox.currentIndex(), 'preset': self.presetbox.currentIndex(),
                'vq': self.comboBox_quality.currentIndex(), 'brmode': self.checkBox_bitrate.isChecked(),
                '10b': self.checkBox_hdr.isChecked(), 'resume' : self.checkBox_resume.isChecked(),
                'keeptmp': self.checkBox_tempfolder.isChecked(), 'rtenc' : self.checkBox_rtenc.isChecked(),
                'minsplit': self.checkBox_minsplit.isChecked(), 'qual' : self.spinBox_quality.value(),
                'splittr': self.spinBox_split.value(), 'cpuused' : self.spinBox_speed.value(),
                'jobs': self.spinBox_jobs.value(), 'audiobr' : self.spinBox_audio.value(),
                'boost': self.spinBox_boost.value(), 'threads' : self.spinBox_threads.value(),
                'cusvid': self.checkBox_videocmd.isChecked(), 'cusaud': self.checkBox_audiocmd.isChecked(),
                'cusffmpeg': self.checkBox_ffmpegcmd.isChecked(), 'vidcmd': self.textEdit_videocmd.toPlainText(),
                'audcmd': self.textEdit_audiocmd.toPlainText(), 'ffmpegcmd': self.textEdit_ffmpegcmd.toPlainText()
        }


    def getArgs(self):
        args = {'video_params': self.getVideoParams(), 'input_file': Path(self.inputPath.text()), 'encoder': 'aom',
                'workers' : self.spinBox_jobs.value(), 'audio_params': self.getAudioParams(),
                'threshold': self.spinBox_split.value(), 'temp': Path(os.path.abspath("temp_" + Path(self.outputPath.text()).parts[-1])),
                'logging' : None, 'passes' : (2 if self.checkBox_twopass.isChecked() else 1),
                'output_file': Path(self.outputPath.text()), 'scenes' : None,
                'resume' : self.checkBox_resume.isChecked(), 'keep' : self.checkBox_tempfolder.isChecked(),
                'min_splits' : self.checkBox_minsplit.isChecked(), 'pix_format' : self.comboBox_inputFormat.currentText(),
                'ffmpeg_cmd' : self.getFFMPEGParams()
        }

        if (self.checkBox_bitrate.isChecked() or self.spinBox_boost.value() < 1):
            args['boost'] = False
            args['br'] = 0
            args['bl'] = 0
        else :
            args['boost'] = True
            args['bl'] = 0
            args['br'] = self.spinBox_boost.value()
        if (self.comboBox_encoder.currentIndex() >= 1):
            args['encoder'] = 'vpx'
        return args

    def encodeVideo(self):
        if (self.runningEncode):
            self.finalizeEncode()
            return
        self.label_3.setEnabled(0)
        self.label_threads.setEnabled(0)
        self.spinBox_threads.setEnabled(0)
        self.checkBox_videocmd.setEnabled(0)
        self.checkBox_audiocmd.setEnabled(0)
        self.checkBox_ffmpegcmd.setEnabled(0)
        self.textEdit_videocmd.setEnabled(0)
        self.textEdit_audiocmd.setEnabled(0)
        self.textEdit_ffmpegcmd.setEnabled(0)

        self.pushButton.setEnabled(0)
        self.pushButton_save.setEnabled(0)
        self.progressBar_total.setEnabled(1)
        self.spinBox_audio.setEnabled(0)
        self.spinBox_quality.setEnabled(0)
        self.spinBox_boost.setEnabled(0)
        self.spinBox_speed.setEnabled(0)
        self.spinBox_split.setEnabled(0)
        self.spinBox_jobs.setEnabled(0)
        self.label_jobs.setEnabled(0)
        self.inputFileChoose.setEnabled(0)
        self.outputFileChoose.setEnabled(0)
        self.label_2.setEnabled(0)
        self.label_audio.setEnabled(0)
        self.label_boost.setEnabled(0)
        self.label_q.setEnabled(0)
        self.label_split.setEnabled(0)
        self.label_inputformat.setEnabled(0)
        self.label_6.setEnabled(0)
        self.comboBox_colorspace.setEnabled(0)
        self.comboBox_inputFormat.setEnabled(0)
        self.comboBox_quality.setEnabled(0)
        self.audioqualitybox.setEnabled(0)
        self.presetbox.setEnabled(0)
        self.checkBox_audio.setEnabled(0)
        self.checkBox_bitrate.setEnabled(0)
        self.checkBox_hdr.setEnabled(0)
        self.checkBox_minsplit.setEnabled(0)
        self.checkBox_resume.setEnabled(0)
        self.checkBox_rtenc.setEnabled(0)
        self.checkBox_tempfolder.setEnabled(0)
        self.checkBox_twopass.setEnabled(0)
        self.audioqualitybox.setEnabled(0)
        self.label_audioquality.setEnabled(0)
        self.label_preset.setEnabled(0)
        self.label_quality.setEnabled(0)
        self.label_4.setEnabled(0)
        self.comboBox_encoder.setEnabled(0)
        self.pushButton_up.setEnabled(0)
        self.pushButton_down.setEnabled(0)
        self.pushButton_del.setEnabled(0)
        self.label_status.setEnabled(1) # self.setupUi(self)
        self.label_status.setText("Initializing...")
        if (len(self.encodeList) == 0):
            args = self.getArgs()
            self.encodeList.append(args)
        print("Running in queued mode with a queue of length " + str(len(self.encodeList)))
        self.runningEncode = True
        self.worker = EncodeWorker(self.encodeList)
        self.workerThread = QtCore.QThread()
        self.worker.updateQueuedStatus.connect(self.updateQueuedStatus)
        self.worker.updateStatusProgress.connect(self.updateStatusProgress)
        self.worker.encodeFinished.connect(self.encodeFinished)
        self.worker.moveToThread(self.workerThread)  # Move the Worker object to the Thread object
        self.workerThread.started.connect(self.worker.run)  # Init worker run() at startup (optional)
        self.workerThread.start()
        self.inputPath.setText("")
        self.outputPath.setText("")
        self.pushButton_del.setEnabled(0)
        self.listWidget.setEnabled(0)

    def finalizeEncode(self):
        self.runningEncode = False
        self.pushButton.setStyleSheet("color: black; background-color: white")
        self.pushButton.setText("▶  Encode")
        self.label_threads.setEnabled(1)
        self.spinBox_threads.setEnabled(1)
        self.checkBox_audio.setEnabled(1)
        self.spinBox_speed.setEnabled(1)
        self.spinBox_speed.setValue(self.spinBox_speed.value())
        self.spinBox_split.setEnabled(1)
        self.spinBox_jobs.setEnabled(1)
        self.label_jobs.setEnabled(1)
        self.inputFileChoose.setEnabled(1)
        self.outputFileChoose.setEnabled(1)
        self.inputPath.setText("")
        self.outputPath.setText("")
        self.label_threads.setEnabled(1)
        self.spinBox_threads.setEnabled(1)
        self.label_2.setEnabled(1)
        self.label_q.setEnabled(1)
        self.label_split.setEnabled(1)
        self.label_inputformat.setEnabled(1)
        self.label_6.setEnabled(1)
        self.label_5.setEnabled(1)
        self.comboBox_colorspace.setEnabled(1)
        self.comboBox_inputFormat.setEnabled(1)
        self.comboBox_quality.setEnabled(1)
        self.presetbox.setEnabled(1)
        self.checkBox_hdr.setEnabled(1)
        self.checkBox_minsplit.setEnabled(1)
        self.checkBox_resume.setEnabled(1)
        if (self.spinBox_speed.value() < 7):
            self.checkBox_rtenc.setEnabled(1)
        self.checkBox_tempfolder.setEnabled(1)
        if (self.checkBox_audio.isChecked()):
            self.spinBox_audio.setEnabled(1)
            self.label_audio.setEnabled(1)
            self.audioqualitybox.setEnabled(1)
            self.label_audioquality.setEnabled(1)
        self.spinBox_quality.setEnabled(1)
        self.checkBox_bitrate.setEnabled(1)
        self.label_preset.setEnabled(1)
        if (not self.checkBox_bitrate.isChecked()):
            self.label_boost.setEnabled(1)
            self.comboBox_quality.setEnabled(1)
            self.label_quality.setEnabled(1)
        if (not self.checkBox_rtenc.isChecked()):
            self.checkBox_twopass.setEnabled(1)
        self.label_status.setEnabled(0) # self.setupUi(self)
        self.label_4.setEnabled(1)
        self.comboBox_encoder.setEnabled(1)
        self.label_3.setEnabled(1)
        self.checkBox_videocmd.setEnabled(1)
        self.checkBox_audiocmd.setEnabled(1)
        self.checkBox_ffmpegcmd.setEnabled(1)
        if (self.checkBox_videocmd.isChecked()):
            self.textEdit_videocmd.setEnabled(1)
        if (self.checkBox_ffmpegcmd.isChecked()):
            self.textEdit_ffmpegcmd.setEnabled(1)
        if (self.checkBox_audiocmd.isChecked()):
            self.textEdit_audiocmd.setEnabled(1)
        self.encodeList = []
        self.redrawQueueList()
        self.pushButton_up.setEnabled(1)
        self.pushButton_down.setEnabled(1)
        self.pushButton_del.setEnabled(1)
        self.listWidget.setEnabled(1)
        self.pushButton_save.setEnabled(0)
        self.progressBar_total.setValue(0)
        print("Enabled all buttons, returning program to normal")

class EncodeWorker(QtCore.QObject):
    updateStatusProgress = QtCore.pyqtSignal(str, int)
    updateQueuedStatus = QtCore.pyqtSignal(str)
    encodeFinished = QtCore.pyqtSignal(bool)

    def __init__(self, argdata):
        super().__init__()
        self.argdat = argdata

    def runProcessing(self, dictargs):
        av1an = Av1an(dictargs)
        print(dictargs)
        av1an.main_thread(self)
        print("\n\nEncode completed for " + str(dictargs['input_file']) + " -> " + str(dictargs['output_file']))

    def run(self):
        self.updateQueuedStatus.emit("Encoding video 1/" + str(len(self.argdat)))
        try:
            for i in range(len(self.argdat)):
                self.updateStatusProgress.emit("Processing video " + str(i + 1), 0)
                self.runProcessing(self.argdat[i])
                self.updateQueuedStatus.emit("Completed encode " + str(i + 1) + "/" + str(len(self.argdat)))
            self.updateQueuedStatus.emit("Completed video queue")
            self.encodeFinished.emit(True)
        except Exception as e:
            print(e)
            traceback.print_exc()
            self.encodeFinished.emit(False)


if __name__ == '__main__':
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()
    print("Loading program... please wait!")
    app = QtWidgets.QApplication(sys.argv)
    window = window()
    window.show()
    sys.exit(app.exec_())
