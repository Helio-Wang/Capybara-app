import os
import sys
import PyQt5 as qt
import PyQt5.QtWidgets as qtw
from eucalypt import nexparser
import worker


def test_open(filename):
    """
    Permission testing for open file dialog
    """
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
    """
    Handle manually the overwrite option when saving output file
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


def open_dialog(nex=True):
    """
    Dialog for opening nexus or txt files
    """
    filename, _ = qtw.QFileDialog.getOpenFileName(None, f'Open a {"Nexus" if nex else "text"} file', '',
                                                  'Nexus Files (*.nex)' if nex else 'Text Files (*.txt)',
                                                  options=qtw.QFileDialog.Options()
                                                        | qtw.QFileDialog.DontUseNativeDialog)
    if not filename or not test_open(filename):
        return False, ''
    return True, filename


def save_dialog(default_name, default_ext):
    """
    Custom dialog for saving text files
    """
    # force the extension manually for now
    filename, _ = qtw.QFileDialog.getSaveFileName(None, 'Save the output file', default_name,
                                                  f'{"Text Files (*.txt)" if default_ext == ".txt" else "DOT Files (*.dot)"}'
                                                  f' ;; All Files (*)',
                                                  options=qtw.QFileDialog.Options()
                                                        | qtw.QFileDialog.DontUseNativeDialog
                                                        | qtw.QFileDialog.DontConfirmOverwrite)
    if not filename:
        return False, ''
    if filename[-4:] != default_ext:
        filename += default_ext
    if not handle_overwrite(filename):
        return False, ''
    return True, filename


class OutputProgressDialog(qtw.QProgressDialog):
    """
    A progress bar for the enumeration tasks
    """
    def __init__(self, message='Output in progress', title='Writing the output...', parent=None):
        super().__init__(message, 'OK', 0, 100, parent)
        self.setMinimumDuration(0)

        self.cancelButton = qtw.QPushButton('Cancel')
        self.setCancelButton(self.cancelButton)
        self.canceled.connect(self.cancel)

        self.setAutoReset(False)
        self.setAutoClose(False)

        self.setWindowTitle(title)
        self.setFixedSize(500, 150)
        self.thread = None

        self.open()
        self.setValue(0)
        qtw.QApplication.processEvents()

    def valueChanged(self, value):
        self.setValue(value)
        if value == 100:
            self.setCancelButtonText('OK')
            self.thread.wait()
            self.close()

    def connectToThread(self, thread):
        self.thread = thread
        thread.sig2.connect(self.valueChanged)

    def cancel(self):
        if self.cancelButton.text() == 'Cancel':
            self.thread.abort()
            self.thread.wait()


class EnumerateDialog(qtw.QDialog):
    """
    After choosing the output file names, the user is provided with further enumeration options
    in particular, whether to filter out cyclic solutions
    """
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
        groupBox2.setMaximumHeight(100)

        layout = qtw.QVBoxLayout()
        layout.addWidget(groupBox2)
        layout.addWidget(groupBox)

        self.filter_cyclic = False
        self.label_output = True
        vlayout3 = qtw.QVBoxLayout()
        if self.task == 0:
            groupBox3 = qtw.QGroupBox('Filter out cyclic solutions?\t ')
            onlyButton = qtw.QRadioButton('Keep only acyclic (slower)')
            bothButton = qtw.QRadioButton('Keep both cyclic and acyclic')
            bothButton.setChecked(True)
            onlyButton.toggled.connect(self.change_cyclic)
            vlayout3.addWidget(bothButton)
            vlayout3.addWidget(onlyButton)
            groupBox3.setLayout(vlayout3)
            layout.addWidget(groupBox3)

        elif self.task in (2, 3):
            groupBox3 = qtw.QGroupBox('Output type ')
            vlayout3 = qtw.QVBoxLayout()
            onlyButton = qtw.QRadioButton('Output the labels only')
            onlyButton.setToolTip(f'<b></b>When checked, in a solution each symbiont node receives a label '
                                  f'({"event" if task == 2 else "event and a host name if available"}). The output'
                                  f' can be visualized in Quokka Viewer.')
            onlyButton.setChecked(True)
            bothButton = qtw.QRadioButton('Output one reconciliation (much slower)')
            bothButton.setToolTip('<b></b>When checked, in a solution each symbiont node receives a host name.')
            onlyButton.toggled.connect(self.check_label_output)
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
        self.resize(500, 350)

    def change_limit(self, checked):
        if checked:
            self.limitedText.setEnabled(True)
            self.limitedText.setText('1000')
        else:
            self.limitedText.setEnabled(False)
            self.limitedText.clear()

    def validate_limit(self):
        if not self.limitedText.isEnabled():
            return True
        try:
            x = int(self.limitedText.text())
            if x < 1:
                qtw.QMessageBox.critical(self, 'Error', 'Limit must be at least one!', qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
                self.limitedText.setText('1000')
                return False
        except ValueError:
            qtw.QMessageBox.critical(self, 'Error', 'Limit must be a number!', qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            self.limitedText.setText('1000')
            return False
        return True

    def change_cyclic(self, checked):
        self.filter_cyclic = checked

    def check_label_output(self, checked):
        self.label_output = checked


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
        glayout.addWidget(qtw.QLabel('Cospeciation'), 1, 1)
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

    def reset(self):
        self.cospBox.setText('-1')
        self.dupBox.setText('1')
        self.switchBox.setText('1')
        self.lossBox.setText('1')
    
    def validate_all(self):
        if self.validate(0, self.cospBox):
            if self.validate(1, self.dupBox):
                if self.validate(2, self.switchBox):
                    if self.validate(3, self.lossBox):
                        return True
        return False

    def validate(self, index, box):
        try:
            self.cost_vector[index] = int(box.text())
        except ValueError:
            qtw.QMessageBox.critical(self, 'Error', 'Cost must be a number!', qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            self.reset()
            return False
        return True
            

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
        self.boxAll.setToolTip('A <b>solution</b> is a reconciliation of minimum cost.')
        self.boxEq1.setToolTip('The <b>event vector</b> of a reconciliation is a vector of four integers: '
                               'the number of occurrences of cospeciation, duplication, host-switch, or loss event.<p>'
                               'Two reconciliations are considered equivalent if they have the same event vector.</p>')
        self.boxEq2.setToolTip('The <b>event partition</b> of a reconciliation is a partition of the symbiont nodes '
                               'into three subsets: cospeciation, duplication, and host-switch nodes.<p>'
                               'Two reconciliations are considered equivalent if, for each symbiont node,'
                               'the associated events are the same.</p>')
        self.boxEq3.setToolTip('Two reconciliations are considered <b>equivalent</b> if, '
                               'for each symbiont node, the associated events are the same, moreover, '
                               'the associated hosts are also the same except when the event is a host-switch.')

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


class ConvertOptionBox(qtw.QGroupBox):
    def __init__(self):
        super().__init__()
        self.setTitle('Visualization task ')
        self.hostButton = qtw.QRadioButton('Host tree')
        self.hostButton.setToolTip('<b></b>Extract the host tree for visualization')
        self.parasiteButton = qtw.QRadioButton('Symbiont tree')
        self.parasiteButton.setToolTip('<b></b>Extract the symbiont tree for visualization')
        self.allButton = qtw.QRadioButton('All event partitions or equivalence classes (Animation)')
        self.allButton.setChecked(True)
        self.allButton.setToolTip('<b></b>Extract all solutions in the file (event partitions or equivalence classes) '
                                  'for animated visualization')
        vlayout = qtw.QVBoxLayout()
        vlayout.addWidget(self.hostButton)
        vlayout.addWidget(self.parasiteButton)
        vlayout.addWidget(self.allButton)
        self.setLayout(vlayout)

        self.task = 2
        self.hostButton.toggled.connect(lambda: self.validate(0, self.hostButton))
        self.parasiteButton.toggled.connect(lambda: self.validate(1, self.parasiteButton))
        self.allButton.toggled.connect(lambda: self.validate(2, self.allButton))

    def validate(self, task, box):
        if box.isChecked():
            self.task = task


class MainAppWindow(qtw.QWidget):
    sig = qt.QtCore.pyqtSignal(list)
    sig2 = qt.QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.setWindowTitle('Quokka')

        self.create_widgets()
        self.set_layout()
        self.start_thread()

        self.data = None
        self.reset()
        self.has_output = False
        self.unsaved = False
        self.default_output_name = 'log.txt'
        self.output_ext = '.txt'

    def start_thread(self):
        self.count_thread = worker.CountThread()
        self.sig.connect(self.count_thread.on_source)
        self.count_thread.sig.connect(self.thread_output)

        self.enum_thread = worker.EnumerateThread()
        self.sig2.connect(self.enum_thread.on_source)
        self.enum_thread.sig.connect(self.thread_output)

    def create_widgets(self):
        self.btnOpen = qtw.QPushButton('Open', self, icon=self.style().standardIcon(qtw.QStyle.SP_DialogOpenButton))
        self.btnOpen.setToolTip('<b>Open</b> a Nexus file')
        self.btnOpen.setFixedSize(105, 50)
        self.btnOpen.clicked.connect(self.open_event)

        self.btnCount = qtw.QPushButton('Count', self, icon=self.style().standardIcon(qtw.QStyle.SP_DialogOkButton))
        self.btnCount.setToolTip('<b>Count</b> the number of solutions')
        self.btnCount.setFixedSize(110, 50)
        self.btnCount.clicked.connect(self.count_event)

        self.btnEnumerate = qtw.QPushButton(' Enumerate', self, icon=self.style().standardIcon(qtw.QStyle.SP_DialogSaveButton))
        self.btnEnumerate.setToolTip('<b>Enumerate</b> solutions to a file')
        self.btnEnumerate.setFixedSize(110, 50)
        self.btnEnumerate.clicked.connect(self.enumerate_event)

        self.btnSave = qtw.QPushButton(' Save', self, icon=self.style().standardIcon(qtw.QStyle.SP_DialogSaveButton))
        self.btnSave.setToolTip('<b>Save</b> the text output to a file')
        self.btnSave.setFixedSize(80, 50)
        self.btnSave.clicked.connect(self.save_event)

        self.inNameBox = qtw.QLineEdit()
        self.inNameBox.setReadOnly(True)
        self.summaryTextBox = qtw.QPlainTextEdit()
        self.summaryTextBox.setFixedHeight(60)
        self.summaryTextBox.setReadOnly(True)
        self.outTextBox = qtw.QTextEdit()
        self.outTextBox.setFont(qt.QtGui.QFontDatabase.systemFont(qt.QtGui.QFontDatabase.FixedFont))  # magic trick ;)
        self.outTextBox.setReadOnly(True)
        self.outTextBox.setMinimumHeight(150)

        self.costVectorBox = CostVectorBox()
        self.taskBox = TaskBox()

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
            msg = qtw.QMessageBox.warning(self, 'Confirm new input',
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
        self.summaryTextBox.appendPlainText(f"The symbiont tree has\t {self.data.parasite_tree.size()}\t nodes.\n"
                                            f"The host tree has\t {self.data.host_tree.size()}\t nodes.")
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
            qtw.QMessageBox.critical(self, 'Nexus Error', e.message, qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            return False
        except NotImplementedError:
            qtw.QMessageBox.critical(self, 'Format Error', 'The file format is not supported.',
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
        if not self.costVectorBox.validate_all():
            return
        if not self.taskBox.tasks:
            qtw.QMessageBox.critical(self, 'Error', 'Choose at least one task!', qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            self.taskBox.last_check.setChecked(True)
            return
        self.sig.emit([self.data] + self.costVectorBox.cost_vector + sorted(list(self.taskBox.tasks)))
        self.count_thread.start()
        self.in_thread()

    def enumerate_event(self):
        if not self.costVectorBox.validate_all():
            return
        if not self.taskBox.tasks:
            qtw.QMessageBox.critical(self, 'Error', 'Choose at least one task!', qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            self.taskBox.last_check.setChecked(True)
            return
        if len(self.taskBox.tasks) > 1:
            qtw.QMessageBox.critical(self, 'Error', 'Choose one task at a time for enumeration.',
                                     qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            return
        task = list(self.taskBox.tasks).pop()
        success, filename = save_dialog('output.txt', '.txt')
        if not success:
            return
        while True:
            dlg = EnumerateDialog(filename, task)
            if dlg.exec() == qtw.QDialog.Rejected:
                return
            if dlg.validate_limit():
                break
        if not dlg.limitedText.text():
            max_nb = float('Inf')
        else:
            max_nb = int(dlg.limitedText.text())

        progress_dlg = OutputProgressDialog()
        progress_dlg.connectToThread(self.enum_thread)
        self.sig2.emit([self.data] + self.costVectorBox.cost_vector + [task, filename, max_nb,  dlg.filter_cyclic,
                                                                       dlg.label_output])
        self.enum_thread.start()
        self.in_thread()
        progress_dlg.exec_()

    def save_event(self):
        success, filename = save_dialog(self.default_output_name, self.output_ext)
        if not success:
            return
        with open(filename, 'w') as f:
            f.write(self.outTextBox.toPlainText())
        qtw.QMessageBox.information(self, 'Success', 'The output has been saved successfully!',
                                    qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
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
        msg = qtw.QMessageBox.warning(self, 'Confirm exit', 'Are you sure you want to exit the program?'
                                      + ('\n(The current output will be lost if unsaved)'
                                         if self.has_output and self.unsaved else ''),
                                      qtw.QMessageBox.Yes | qtw.QMessageBox.Cancel, qtw.QMessageBox.Yes)

        if msg == qtw.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


class SuboptWindow(MainAppWindow):
    sig3 = qt.QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.acyclic_only = False

    def start_thread(self):
        self.enum_thread = worker.BestKEnumerateThread()
        self.sig3.connect(self.enum_thread.on_source)
        self.enum_thread.sig.connect(self.thread_output)

    def create_widgets(self):
        super().create_widgets()
        self.btnCount.setVisible(False)
        self.taskBox.setVisible(False)

        self.groupBox = qtw.QGroupBox('Maximum number of output  ')
        self.limitText = qtw.QLineEdit()
        self.limitText.setText('100')
        hlayout = qtw.QHBoxLayout()
        hlayout.addWidget(qtw.QLabel('K '))
        hlayout.addWidget(self.limitText)
        self.limitText.setToolTip('<b></b>The K-best enumeration will output the the first K solutions '
                                  'with smallest cost. If there are less than K solutions having the minimum cost, '
                                  'then it will output some solutions having a sub-optimal cost. ')
        self.groupBox.setToolTip(self.limitText.toolTip())
        self.groupBox.setLayout(hlayout)
        self.groupBox.setMaximumHeight(200)

        self.groupBox2 = qtw.QGroupBox('Filter out cyclic solutions?  ')
        vlayout2 = qtw.QVBoxLayout()
        onlyButton = qtw.QRadioButton('Keep only acyclic (slower)  ')
        bothButton = qtw.QRadioButton('Keep both cyclic and acyclic  ')
        bothButton.setChecked(True)
        onlyButton.toggled.connect(self.change_cyclic)
        vlayout2.addWidget(bothButton)
        vlayout2.addWidget(onlyButton)
        self.groupBox2.setLayout(vlayout2)

    def set_layout(self):
        main_layout = qtw.QVBoxLayout()
        hlayout = qtw.QHBoxLayout()
        hlayout.addWidget(self.btnOpen)
        hlayout.addWidget(self.costVectorBox)
        vlayout = qtw.QVBoxLayout()
        vlayout.addWidget(self.groupBox)
        vlayout.addWidget(self.groupBox2)
        hlayout.addLayout(vlayout)
        hlayout.addWidget(self.btnEnumerate)
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

    def validate_limit(self):
        """
        Return true if the input value for K is valid
        """
        try:
            x = int(self.limitText.text())
            if x < 1:
                qtw.QMessageBox.critical(self, 'Error', 'K must be at least one!', qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
                self.limitText.setText('100')
                return False
        except ValueError:
            qtw.QMessageBox.critical(self, 'Error', 'K must be a number!', qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)
            self.limitText.setText('100')
            return False
        return True

    def change_cyclic(self, checked):
        self.acyclic_only = checked

    def enumerate_event(self):
        if not self.costVectorBox.validate_all():
            return
        if not self.validate_limit():
            return
        success, filename = save_dialog('output.txt', '.txt')
        if not success:
            return
        progress_dlg = OutputProgressDialog()
        progress_dlg.connectToThread(self.enum_thread)
        self.sig3.emit([self.data] + self.costVectorBox.cost_vector
                       + [filename, int(self.limitText.text()), self.acyclic_only])
        self.enum_thread.start()
        self.in_thread()
        progress_dlg.exec_()


class ConvertWindow(MainAppWindow):
    sig4 = qt.QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.default_output_name = 'output.dot'
        self.output_ext = '.dot'

    def start_thread(self):
        self.enum_thread = worker.DotFileThread()
        self.sig4.connect(self.enum_thread.on_source)
        self.enum_thread.sig.connect(self.thread_output)

    def create_widgets(self):
        super().create_widgets()
        self.btnCount.setVisible(False)
        self.taskBox.setVisible(False)
        self.summaryTextBox.setVisible(False)
        self.btnOpen.setToolTip('<b>Open</b> an enumeration output file')
        self.btnEnumerate.setText('Run')
        self.btnEnumerate.setToolTip('<b>Run</b> file conversion for visualization')
        self.btnSave.setToolTip('<b>Save</b> the output to a DOT file')
        self.taskBox = ConvertOptionBox()
        self.btnCopy = qtw.QPushButton('Copy', self, icon=self.style().standardIcon(qtw.QStyle.SP_DialogHelpButton))
        self.btnCopy.setFixedSize(80, 50)
        self.btnCopy.setToolTip('<b>Copy</b> the entire output to the clipboard')
        self.btnCopy.clicked.connect(self.copy_event)

    def set_layout(self):
        main_layout = qtw.QVBoxLayout()
        hlayout = qtw.QHBoxLayout()
        hlayout.addWidget(self.btnOpen)
        hlayout.addWidget(self.taskBox)
        hlayout.addWidget(self.btnEnumerate)
        hlayout.setSpacing(30)
        main_layout.addLayout(hlayout)
        main_layout.addItem(qtw.QSpacerItem(10, 10))

        glayout = qtw.QGridLayout()
        glayout.addWidget(qtw.QLabel('Input file'), 1, 1, qt.QtCore.Qt.AlignTop)
        glayout.addWidget(self.inNameBox, 1, 2)
        vlayout = qtw.QVBoxLayout()
        vlayout.addWidget(qtw.QLabel('Output'))
        vlayout.addWidget(self.btnSave)
        vlayout.addWidget(self.btnCopy)
        glayout.addLayout(vlayout, 3, 1, qt.QtCore.Qt.AlignTop)
        glayout.addWidget(self.outTextBox, 3, 2)
        glayout.setSpacing(10)
        main_layout.addLayout(glayout)
        main_layout.setContentsMargins(30, 30, 30, 30)
        self.setLayout(main_layout)

    def copy_event(self):
        cb = qtw.QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(self.outTextBox.toPlainText(), mode=cb.Clipboard)
        qtw.QMessageBox.information(self, 'Success', 'The output has been copied to the clipboard!',
                                    qtw.QMessageBox.Ok, qtw.QMessageBox.Ok)

    def open_event(self):
        if self.has_output and self.unsaved:
            msg = qtw.QMessageBox.warning(self, 'Confirm new input',
                                          'The current output will be lost if not saved.\n'
                                          'Do you want to continue?',
                                          qtw.QMessageBox.Ok | qtw.QMessageBox.Cancel, qtw.QMessageBox.Ok)
            if msg == qtw.QMessageBox.Cancel:
                return
        success, filename = open_dialog(False)
        if not success:
            return
        self.reset()
        self.inNameBox.setText(filename)
        self.btnEnumerate.setEnabled(True)
        self.btnSave.setEnabled(True)

    def enumerate_event(self):
        self.outTextBox.clear()
        self.sig4.emit([self.inNameBox.text(), self.taskBox.task])
        self.enum_thread.start()
        self.in_thread()

    def closeEvent(self, event):
        event.accept()


class WelcomeWindow(qtw.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Quokka')
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        vlayout = qtw.QVBoxLayout()
        vlayout.setSpacing(10)
        main_button = qtw.QPushButton('Standard counting and enumeration')
        subopt_button = qtw.QPushButton('Sub-optimal enumeration')
        viz_button = qtw.QPushButton('Convert enumeration files for visualization')

        for b in (main_button, subopt_button, viz_button):
            b.setSizePolicy(qtw.QSizePolicy.Expanding, qtw.QSizePolicy.Expanding)

        self.choice = None
        main_button.clicked.connect(lambda: self.choose(1))
        subopt_button.clicked.connect(lambda: self.choose(2))
        viz_button.clicked.connect(lambda: self.choose(3))

        vlayout.addWidget(main_button)
        vlayout.addWidget(subopt_button)
        vlayout.addWidget(viz_button)
        self.setLayout(vlayout)
        self.show()

    def choose(self, choice):
        self.choice = choice
        self.accept()


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    welcome = WelcomeWindow()
    value = welcome.exec()
    if value == qtw.QDialog.Accepted:
        if welcome.choice == 1:
            widget = MainAppWindow()
        elif welcome.choice == 2:
            widget = SuboptWindow()
        else:
            widget = ConvertWindow()
    else:
        sys.exit(0)
    widget.move(qtw.QApplication.desktop().screen().rect().center() - widget.rect().center())
    widget.show()
    app.exec_()

