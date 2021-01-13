from PyQt5.QtCore import QThread, pyqtSignal


class LoadThread(QThread):
    trigger = pyqtSignal(str, str, str, str, str, str, int, int)
    finishTrigger = pyqtSignal(str)

    def __int__(self):
        super().__init__()
        self.playerName = ''
        self.player = None

    def run(self):
        print('running')
        fullname = self.playerName.strip().split('#')
        try:
            self.player.inspectPlayer(fullname[0], fullname[1], self.trigger.emit, self.finishTrigger.emit)
        except IndexError:
            return
        
