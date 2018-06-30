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


def printlabels(_, (svg, addrs)):
    '''
    Print labels
    '''

    addrs.sort(reverse=True)

    if len(addrs) == 1:
        tree = xml.etree.ElementTree.parse(svg)
        addrs = addrs * (len(tree.findall(LABELS)) - 1)

    pdfpaths = []
    while addrs:
        tree = xml.etree.ElementTree.parse(svg)
        labels = tree.findall(LABELS)
        first = True
        for label in labels:
            if first:
                first = False
            else:
                try:
                    path = addrs.pop()
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


def main():
    '''
    Main loop
    '''

    subprocess.call(['xfce4-terminal', '-H', '-x', 'echo', __file__])


if __name__ == '__main__':
    sys.exit(main())
