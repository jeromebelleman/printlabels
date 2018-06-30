'''
Make label PDFs from addresses
'''

import sys
reload(sys)
sys.setdefaultencoding('UTF8')
import os
import subprocess
import xml.etree.ElementTree
import uuid
import yaml
from PyQt5 import QtWidgets, QtCore
from gi.repository import Nautilus, GObject

LABELS = ".//*[@{http://www.inkscape.org/namespaces/inkscape}label='#label']"
PARA = "{http://www.w3.org/2000/svg}flowPara"


def addline(flow, text):
    '''
    Add line of text to flow
    '''

    para = xml.etree.ElementTree.Element(PARA)
    para.text = text
    flow.append(para)

class LabelThread(QtCore.QThread): # pylint: disable=too-few-public-methods
    '''
    Label-making thread
    '''

    updateprogress = QtCore.pyqtSignal(int)

    def __init__(self, svg, addrs):
        '''
        Set up thread
        '''

        super(LabelThread, self).__init__()
        self.svg = svg
        self.addrs = addrs


    def run(self):
        '''
        Run thread
        '''

        self.addrs.sort(reverse=True)

        if len(self.addrs) == 1:
            tree = xml.etree.ElementTree.parse(self.svg)
            self.addrs = self.addrs * (len(tree.findall(LABELS)) - 1)

        pdfpaths = []
        i = 0
        while self.addrs:
            tree = xml.etree.ElementTree.parse(self.svg)
            labels = tree.findall(LABELS)
            first = True
            for label in labels:
                if first:
                    first = False
                else:
                    try:
                        path = self.addrs.pop()
                        i += 1
                        self.updateprogress.emit(i)
                        with open(path) as fhl:
                            addr = yaml.load(fhl)

                        label[1].text = os.path.basename(path)[:-5]
                        try:
                            for line in addr['address'][0].splitlines():
                                line = line.strip()
                                if line:
                                    addline(label, line)
                        except KeyError:
                            pass
                    except IndexError:
                        label[1].text = ''

            uuid4 = uuid.uuid4()

            svgpath = '/tmp/labels-%s.svg' % uuid4
            tree.write(svgpath)

            pdfpath = '/tmp/labels-%s.pdf' % uuid4
            subprocess.call(['inkscape',
                             '--export-area-page',
                             '--export-dpi=300',
                             '--export-pdf=' + pdfpath,
                             svgpath])
            pdfpaths.append(pdfpath)

        subprocess.call(['pdfjoin'] + pdfpaths + ['-o', '/tmp/labels.pdf'])


class MainWindow(QtWidgets.QMainWindow): # pylint: disable=too-few-public-methods
    '''
    Main window
    '''

    def __init__(self, svg, addrs):
        '''
        Lay out main window
        '''

        super(MainWindow, self).__init__()

        self.setWindowTitle("Making Labels...")

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, len(addrs))
        self.setCentralWidget(self.progress)

        self.thread = LabelThread(svg, addrs)
        self.thread.start()
        self.thread.updateprogress.connect(self.updateprogress)


    def updateprogress(self, value):
        '''
        Update progress
        '''

        self.progress.setValue(value)
        if value == self.progress.maximum():
            self.close()


def printlabels(_, (svg, addrs)):
    '''
    Print labels
    '''

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow(svg, addrs)
    win.show()
    app.exec_()
    subprocess.Popen(['evince', '/tmp/labels.pdf'])


class PrintLabels(GObject.GObject, Nautilus.MenuProvider):
    '''
    Menu provider
    '''

    def get_file_items(self, _, files): # pylint: disable=arguments-differ
        # Collect files
        addrs = []
        svg = None
        for fle in files:
            if fle.is_directory():
                for root, _, subfiles in os.walk(fle.get_location().get_path()):
                    for subfle in subfiles:
                        if subfle.endswith('.addr'):
                            addrs.append('%s/%s' % (root, subfle))
                        elif subfle.endswith('.svg'):
                            svg = '%s/%s' % (root, subfle)
            elif fle.get_name().endswith('.svg'):
                svg = fle.get_location().get_path()
            elif fle.get_name().endswith('.addr'):
                addrs.append(fle.get_location().get_path())

        if not (svg and addrs):
            return

        item = Nautilus.MenuItem(name='Nautilus::printlabels',
                                 label='Print Labels')
        item.connect('activate', printlabels, (svg, addrs))

        return item,
