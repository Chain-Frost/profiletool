"""Static contract for widgets/layouts generated from profiletool.ui."""

# ruff: noqa: N801, N802, N815 -- Names must match the Qt Designer form and loader.

from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class Ui_ProfileTool:
    """Named attributes created by Qt Designer's runtime form loader."""

    butSaveAs: QPushButton
    cbAddPoint: QCheckBox
    cbLiveUpdate: QCheckBox
    cbSameAxisScale: QCheckBox
    cboLibrary: QComboBox
    cbxSaveAs: QComboBox
    checkBox_mpl_tracking: QCheckBox
    checkBox_showcursor: QCheckBox
    comboBox: QComboBox
    dockWidgetContents: QWidget
    frame: QFrame
    frame_2: QFrame
    frame_for_plot: QFrame
    fullResolutionCheckBox: QCheckBox
    gridLayout: QGridLayout
    gridLayout_2: QGridLayout
    gridLayout_3: QGridLayout
    groupBox: QGroupBox
    groupBox_2: QGroupBox
    groupBox_3: QGroupBox
    horizontalLayout: QHBoxLayout
    horizontalLayout_3: QHBoxLayout
    horizontalLayout_4: QHBoxLayout
    horizontalLayout_5: QHBoxLayout
    label: QLabel
    label_2: QLabel
    label_3: QLabel
    page: QWidget
    plotComboBox: QComboBox
    profileInterpolationCheckBox: QCheckBox
    pushButton: QPushButton
    pushButton_2: QPushButton
    pushButton_reinitview: QPushButton
    sbMaxVal: QDoubleSpinBox
    sbMinVal: QDoubleSpinBox
    scrollArea: QScrollArea
    scrollAreaWidgetContents: QWidget
    splitter: QSplitter
    stackedWidget: QStackedWidget
    tab: QWidget
    tabWidget: QTabWidget
    tab_1: QWidget
    tab_2: QWidget
    tableView: QTableView
    verticalLayout: QVBoxLayout
    verticalLayout_2: QVBoxLayout
    verticalLayout_3: QVBoxLayout
    verticalLayout_4: QVBoxLayout
    verticalLayout_5: QVBoxLayout
    verticalLayout_7: QVBoxLayout
    verticalLayout_8: QVBoxLayout
    widget_save_buttons: QWidget

    def setupUi(self, _widget: QDockWidget) -> None:
        """Describe the runtime-generated form setup signature for analysis."""
