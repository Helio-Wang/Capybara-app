import os
import sys
import PyQt5 as qt
import PyQt5.QtWidgets as qtw
import nexparser
import worker


def test_open(filename):
    try:
        with open(filename, 'r'):
            pass
    except PermissionError:
        qtw.QMessageBox.critical(None, 'Permission denied',
                                 'Permission denied. (Is the file opened by another application?).',
                                 qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
        return False
    return True


def handle_overwrite(filename):
    """!
    @brief Handle manually the overwrite option when saving output file
    """
    if os.path.exists(filename):
        msg = qtw.QMessageBox.warning(None, 'Confirm overwrite',
                                      'The file already exists. Do you want to replace it?',
                                      qtw.QMessageBox.Yes | qtw.QMessageBox.Cancel, qtw.QMessageBox.Yes)
        if msg == qtw.QMessageBox.Cancel:
            return False
        try:
            with open(filename, 'w'):
                pass
        except PermissionError:
            qtw.QMessageBox.critical(None, 'Permission denied',
                                     'Permission denied (Is the file opened by another application?).',
                                     qtw.QMessageBox.Ok,  qtw.QMessageBox.Ok)
            return False
        try:
            os.remove(filename)
        except PermissionError:
            pass
    return True


def open_dialog():
    filename, _ = qtw.QFileDialog.getOpenFileName(None, 'Open a Nexus file', '', 'Nexus Files (*.nex)',
                                                  options=qtw.QFileDialog.Options()
                                                        | qtw.QFileDialog.DontUseNativeDialog)
    if not filename or not test_open(filename):
        return False, ''
    return True, filename


def save_dialog(default_name):
    filename, _ = qtw.QFileDialog.getSaveFileName(None, 'Save the output file', default_name,
                                                  'Text Files (*.txt) ;; All Files (*)',
                                                  options=qtw.QFileDialog.Options()
                                                        | qtw.QFileDialog.DontUseNativeDialog
                                                        | qtw.QFileDialog.DontConfirmOverwrite)
    if not filename or not handle_overwrite(filename):
        return False, ''
    return True, filename


class EnumerateDialog(qtw.QDialog):
    def __init__(self, filename, task):
        super().__init__()
        self.task = task
        self.setWindowTitle('Enumeration options')
        self.nameBox = qtw.QLineEdit()
        self.nameBox.setReadOnly(True)
        self.nameBox.setText(filename)

        groupBox = qtw.QGroupBox('Maximum number of output')
        infiniteButton = qtw.QRadioButton('Unlimited')
        infiniteButton.setChecked(True)
        limitedButton = qtw.QRadioButton('Max')
        self.limitedText = qtw.QLineEdit()
        self.limitedText.setEnabled(False)
        limitedButton.toggled.connect(self.change_limit)
        self.limitedText.editingFinished.connect(self.validate_limit)
        vlayout = qtw.QVBoxLayout()
        vlayout.addWidget(infiniteButton)
        hlayout = qtw.QHBoxLayout()
        hlayout.addWidget(limitedButton)
        hlayout.addWidget(self.limitedText)
        vlayout.addLayout(hlayout)
        groupBox.setLayout(vlayout)
        groupBox.setMaximumHeight(200)

        groupBox2 = qtw.QGroupBox('Output file')
        vlayout2 = qtw.QVBoxLayout()
        vlayout2.addWidget(self.nameBox)
        groupBox2.setLayout(vlayout2)

        layout = qtw.QVBoxLayout()
        layout.addWidget(groupBox2)
        layout.addWidget(groupBox)

        self.filter_cyclic = False
        self.vector_output = False
        if self.task == 0:
            groupBox3 = qtw.QGroupBox('Filter out cyclic solutions ')
            vlayout3 = qtw.QVBoxLayout()
            onlyButton = qtw.QRadioButton('Keep only acyclic (slower)')
            bothButton = qtw.QRadioButton('Keep both cyclic and acyclic')
            bothButton.setChecked(True)
            onlyButton.toggled.connect(self.change_cyclic)
            vlayout3.addWidget(bothButton)
            vlayout3.addWidget(onlyButton)
            groupBox3.setLayout(vlayout3)
            layout.addWidget(groupBox3)

        elif self.task == 1:
            groupBox3 = qtw.QGroupBox('Event vector enumeration ')
            vlayout3 = qtw.QVBoxLayout()
            onlyButton = qtw.QRadioButton('Reconciliation only')
            onlyButton.setChecked(True)
            bothButton = qtw.QRadioButton('Output the event vector (in comment) with the reconciliation')
            bothButton.toggled.connect(self.check_vector_output)
            vlayout3.addWidget(onlyButton)
            vlayout3.addWidget(bothButton)
            groupBox3.setLayout(vlayout3)
            layout.addWidget(groupBox3)

        buttons = qtw.QDialogButtonBox(qtw.QDialogButtonBox.Ok | qtw.QDialogButtonBox.Cancel,
                                       qt.QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 5, 10)
        self.setLayout(layout)
        self.resize(500, 300)

    def change_limit(self, checked):
        if checked:
            self.limitedText.setEnabled(True)
            self.limitedText.setText('1000')
        else:
            self.limitedText.setEnabled(False)
            self.limitedText.clear()

    def validate_limit(self):
        try:
            _ = int(self.limitedText.text())
        except ValueError:
            qtw.QMessageBox.critical(None, 'Error', 'Limit must be a number!', qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            self.limitedText.setText('1000')

    def change_cyclic(self, checked):
        self.filter_cyclic = checked

    def check_vector_output(self, checked):
        self.vector_output = checked


class CostVectorBox(qtw.QGroupBox):
    def __init__(self):
        super().__init__()
        self.setTitle('Cost vector')
        self.cospBox = qtw.QLineEdit()
        self.dupBox = qtw.QLineEdit()
        self.switchBox = qtw.QLineEdit()
        self.lossBox = qtw.QLineEdit()
        self.setFixedWidth(200)
        self.reset()

        glayout = qtw.QGridLayout()
        glayout.addWidget(qtw.QLabel('Cospectiation'), 1, 1)
        glayout.addWidget(self.cospBox, 1, 2)
        glayout.addWidget(qtw.QLabel('Duplication'), 2, 1)
        glayout.addWidget(self.dupBox, 2, 2)
        glayout.addWidget(qtw.QLabel('Host-switch'), 3, 1)
        glayout.addWidget(self.switchBox, 3, 2)
        glayout.addWidget(qtw.QLabel('Loss'), 4, 1)
        glayout.addWidget(self.lossBox, 4, 2)
        glayout.setSpacing(10)
        self.setLayout(glayout)

        self.cost_vector = [-1, 1, 1, 1]
        self.cospBox.editingFinished.connect(lambda: self.validate(0, self.cospBox))
        self.dupBox.editingFinished.connect(lambda: self.validate(1, self.dupBox))
        self.switchBox.editingFinished.connect(lambda: self.validate(2, self.switchBox))
        self.lossBox.editingFinished.connect(lambda: self.validate(3, self.lossBox))

    def reset(self):
        self.cospBox.setText('-1')
        self.dupBox.setText('1')
        self.switchBox.setText('1')
        self.lossBox.setText('1')

    def validate(self, index, box):
        try:
            self.cost_vector[index] = int(box.text())
        except ValueError:
            qtw.QMessageBox.critical(None, 'Error', 'Cost must be a number!', qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            box.setText('1')


class TaskBox(qtw.QGroupBox):
    def __init__(self):
        super().__init__()
        self.setTitle('Task')
        self.setMaximumWidth(300)
        self.tasks = {0}
        self.last_check = None

        self.boxAll = qtw.QCheckBox('T1: All solutions')
        self.boxEq1 = qtw.QCheckBox('T2: Event vectors')
        self.boxEq2 = qtw.QCheckBox('T3: Event partitions')
        self.boxEq3 = qtw.QCheckBox('T4: Equivalence classes')
        self.boxAll.setChecked(True)
        self.boxAll.toggled.connect(lambda: self.validate(0, self.boxAll))
        self.boxEq1.toggled.connect(lambda: self.validate(1, self.boxEq1))
        self.boxEq2.toggled.connect(lambda: self.validate(2, self.boxEq2))
        self.boxEq3.toggled.connect(lambda: self.validate(3, self.boxEq3))

        vlayout = qtw.QVBoxLayout()
        vlayout.addWidget(self.boxAll)
        vlayout.addWidget(self.boxEq1)
        vlayout.addWidget(self.boxEq2)
        vlayout.addWidget(self.boxEq3)
        self.setLayout(vlayout)

    def validate(self, task, box):
        if box.isChecked():
            self.last_check = box
            self.tasks.add(task)
        else:
            self.tasks.remove(task)


class AppWindow(qtw.QWidget):
    sig = qt.QtCore.pyqtSignal(list)
    sig2 = qt.QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(800)
        self.setMinimumHeight(800)

        self.btnOpen = qtw.QPushButton('Open', self, icon=self.style().standardIcon(qtw.QStyle.SP_DialogOpenButton))
        self.btnOpen.setToolTip('<b>Open</b> a Nexus file')
        self.btnOpen.setFixedSize(105, 50)
        self.btnOpen.clicked.connect(self.open_event)

        self.btnCount = qtw.QPushButton('Count', self, icon=self.style().standardIcon(qtw.QStyle.SP_DialogOkButton))
        self.btnCount.setToolTip('<b>Count</b> the number of solutions')
        self.btnCount.setFixedSize(105, 50)
        self.btnCount.clicked.connect(self.count_event)

        self.btnEnumerate = qtw.QPushButton(' Enumerate', self, icon=self.style().standardIcon(qtw.QStyle.SP_DialogSaveButton))
        self.btnEnumerate.setToolTip('<b>Enumerate</b> all solutions')
        self.btnEnumerate.setFixedSize(105, 50)
        self.btnEnumerate.clicked.connect(self.enumerate_event)

        self.btnSave = qtw.QPushButton(' Save', self, icon=self.style().standardIcon(qtw.QStyle.SP_DialogSaveButton))
        self.btnSave.setToolTip('<b>Save</b> the output to a file')
        self.btnSave.setFixedSize(75, 50)
        self.btnSave.clicked.connect(self.save_event)

        self.inNameBox = qtw.QLineEdit()
        self.inNameBox.setReadOnly(True)
        self.summaryTextBox = qtw.QPlainTextEdit()
        self.summaryTextBox.setFixedHeight(100)
        self.summaryTextBox.setReadOnly(True)
        self.outTextBox = qtw.QTextEdit()
        self.outTextBox.setFont(qt.QtGui.QFontDatabase.systemFont(qt.QtGui.QFontDatabase.FixedFont))  # magic trick ;)
        self.outTextBox.setReadOnly(True)
        self.outTextBox.setMinimumHeight(150)

        self.costVectorBox = CostVectorBox()
        self.taskBox = TaskBox()

        self.set_layout()

        self.count_thread = worker.CountThread()
        self.sig.connect(self.count_thread.on_source)
        self.count_thread.sig.connect(self.thread_output)

        self.enum_thread = worker.EnumerateThread()
        self.sig2.connect(self.enum_thread.on_source)
        self.enum_thread.sig.connect(self.thread_output)

        self.data = None
        self.reset()
        self.has_output = False
        self.unsaved = False

    def set_layout(self):
        main_layout = qtw.QVBoxLayout()
        hlayout = qtw.QHBoxLayout()
        hlayout.addWidget(self.btnOpen)
        hlayout.addWidget(self.costVectorBox)
        hlayout.addWidget(self.taskBox)
        vlayout = qtw.QVBoxLayout()
        vlayout.addWidget(self.btnCount)
        vlayout.addWidget(self.btnEnumerate)
        hlayout.addLayout(vlayout)
        hlayout.setSpacing(30)
        main_layout.addLayout(hlayout)
        main_layout.addItem(qtw.QSpacerItem(10, 10))

        glayout = qtw.QGridLayout()
        glayout.addWidget(qtw.QLabel('Input file'), 1, 1, qt.QtCore.Qt.AlignTop)
        glayout.addWidget(self.inNameBox, 1, 2)
        glayout.addWidget(qtw.QLabel('Input\nSummary'), 2, 1, qt.QtCore.Qt.AlignTop)
        glayout.addWidget(self.summaryTextBox, 2, 2)
        vlayout = qtw.QVBoxLayout()
        vlayout.addWidget(qtw.QLabel('Output'))
        vlayout.addWidget(self.btnSave)
        glayout.addLayout(vlayout, 3, 1, qt.QtCore.Qt.AlignTop)
        glayout.addWidget(self.outTextBox, 3, 2)
        glayout.setSpacing(10)
        main_layout.addLayout(glayout)
        main_layout.setContentsMargins(30, 30, 30, 30)
        self.setLayout(main_layout)

    def reset(self):
        self.data = None
        self.has_output = False
        self.unsaved = False
        self.inNameBox.clear()
        self.summaryTextBox.clear()
        self.outTextBox.clear()
        self.btnCount.setEnabled(False)
        self.btnEnumerate.setEnabled(False)
        self.btnSave.setEnabled(False)

    def open_event(self):
        if self.has_output and self.unsaved:
            msg = qtw.QMessageBox.warning(None, 'Confirm new input',
                                          'The current output will be lost if unsaved.\n'
                                          'Do you want to continue?',
                                          qtw.QMessageBox.Ok | qtw.QMessageBox.Cancel, qtw.QMessageBox.Ok)
            if msg == qtw.QMessageBox.Cancel:
                return
        success, filename = open_dialog()
        if not success:
            return
        self.reset()
        if not self.read_data(filename):
            return
        self.inNameBox.setText(filename)
        self.summaryTextBox.appendPlainText(f"The parasite tree has\t {self.data.parasite_tree.size()} nodes.\n"
                                            f"The host tree has\t {self.data.host_tree.size()} nodes.")
        self.outTextBox.append(f'The input file is {filename}\n')

    def read_data(self, filename):
        try:
            with open(filename, 'r') as file:
                parser = nexparser.NexusParser(file)
                parser.read()
                host_tree = parser.host_tree
                parasite_tree = parser.parasite_tree
                leaf_map = parser.leaf_map
        except nexparser.NexusFileParserException as e:
            qtw.QMessageBox.critical(None, 'Nexus Error', e.message, qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            return False
        except NotImplementedError:
            qtw.QMessageBox.critical(None, 'Format Error', 'The file format is not supported.',
                                     qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            return False
        self.data = worker.WorkerData(parasite_tree, host_tree, leaf_map)
        self.btnCount.setEnabled(True)
        self.btnEnumerate.setEnabled(True)
        self.btnSave.setEnabled(True)
        return True

    def thread_output(self, text):
        self.outTextBox.append(text)
        if not text:
            self.out_thread()

    def count_event(self):
        if not self.taskBox.tasks:
            qtw.QMessageBox.critical(None, 'Error', 'Choose at least one task!', qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            self.taskBox.last_check.setChecked(True)
            return
        self.sig.emit([self.data] + self.costVectorBox.cost_vector + sorted(list(self.taskBox.tasks)))
        self.count_thread.start()
        self.in_thread()

    def enumerate_event(self):
        if not self.taskBox.tasks:
            qtw.QMessageBox.critical(None, 'Error', 'Choose at least one task!', qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            self.taskBox.last_check.setChecked(True)
            return
        if len(self.taskBox.tasks) > 1:
            qtw.QMessageBox.critical(None, 'Error', 'Choose one task at a time for enumeration.',
                                     qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            return
        task = list(self.taskBox.tasks).pop()
        success, filename = save_dialog('output.txt')
        if not success:
            return
        dlg = EnumerateDialog(filename, task)
        if dlg.exec() == qtw.QDialog.Rejected:
            return
        if not dlg.limitedText.text():
            max_nb = float('Inf')
        else:
            max_nb = int(dlg.limitedText.text())
        self.sig2.emit([self.data] + self.costVectorBox.cost_vector + [task, filename, max_nb,
                                                                       dlg.filter_cyclic, dlg.vector_output])
        self.enum_thread.start()
        self.in_thread()

    def save_event(self):
        success, filename = save_dialog('log.txt')
        if not success:
            return
        with open(filename, 'w') as f:
            f.write(self.outTextBox.toPlainText())
        self.unsaved = False

    def in_thread(self):
        self.btnCount.setEnabled(False)
        self.btnEnumerate.setEnabled(False)
        self.btnOpen.setEnabled(False)
        self.btnSave.setEnabled(False)
        self.costVectorBox.setEnabled(False)
        self.taskBox.setEnabled(False)

    def out_thread(self):
        self.btnCount.setEnabled(True)
        self.btnEnumerate.setEnabled(True)
        self.btnOpen.setEnabled(True)
        self.btnSave.setEnabled(True)
        self.costVectorBox.setEnabled(True)
        self.taskBox.setEnabled(True)
        self.has_output = True
        self.unsaved = True

    def closeEvent(self, event):
        msg = qtw.QMessageBox.warning(None, 'Confirm exit', 'Are you sure you want to exit the program?'
                                      + ('\n(The current output will be lost if unsaved)'
                                         if self.has_output and self.unsaved else ''),
                                      qtw.QMessageBox.Yes | qtw.QMessageBox.Cancel, qtw.QMessageBox.Yes)

        if msg == qtw.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    widget = AppWindow()
    widget.show()
    widget.move(qtw.QApplication.desktop().screen().rect().center() - widget.rect().center())
    app.exec_()

