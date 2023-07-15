import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import json
import numpy as np
import os
from matplotlib.backends.backend_qt5agg import FigureCanvas as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from pydicom import dcmread
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("InsightMedi Viewer")
        # self.setFixedSize(700, 700)

        self.ds = None
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        self.frame_number = None
        self.file_name = None
        self.label_dict = {"line": [], "rectangle": [],
                           "circle": [], "freehand": []}

        self.canvas = FigureCanvas(Figure(figsize=(4, 3)))
        vbox = QVBoxLayout(self.main_widget)
        vbox.addWidget(self.canvas)

        # Create a toolbar
        toolbar = self.addToolBar("Toolbar")
        self.statusBar().showMessage("")
        '''
        파일 도구
        '''

        # 파일 열기 버튼
        open_action = QAction(
            QIcon('icon/open_file_icon.png'), "Open File", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)

        # 파일 저장하기 버튼
        save_action = QAction(QIcon('icon/save_icon.png'), "Save", self)
        save_action.triggered.connect(self.save)
        toolbar.addAction(save_action)

        # 파일 다른 이름으로 저장하기 버튼
        save_as_action = QAction(
            QIcon('icon/save_as_icon.png'), "Save As", self)
        save_as_action.triggered.connect(self.save_as)
        toolbar.addAction(save_as_action)

        toolbar.addSeparator()  # 구분선

        # 윈도잉 액션
        windowing_action = QAction(
            QIcon('icon/windowing_icon.png'), "Windowing", self)
        windowing_action.triggered.connect(self.windowing_input_dialog)
        toolbar.addAction(windowing_action)

        toolbar.addSeparator()  # 구분선

        self.is_panning = False
        self.pan_start = None

        '''
        어노테이션 도구
        '''

        # 직선 액션
        straightline_action = QAction(
            QIcon('icon/straightline_icon.png'), "Line", self)
        straightline_action.triggered.connect(self.draw_straight_line)
        toolbar.addAction(straightline_action)

        # 원 액션
        circle_action = QAction(QIcon('icon/circle_icon.png'), "Circle", self)
        circle_action.triggered.connect(self.draw_circle)
        toolbar.addAction(circle_action)

        # 사각형 액션
        rectangle_action = QAction(
            QIcon('icon/rectangle_icon.png'), "Rectangle", self)
        rectangle_action.triggered.connect(self.draw_rectangle)
        toolbar.addAction(rectangle_action)

        # 곡선 액션
        curve_action = QAction(QIcon('icon/curve_icon.png'), "Curve", self)
        curve_action.triggered.connect(self.draw_curve)
        toolbar.addAction(curve_action)

        # 자유형 액션
        freehand_action = QAction(
            QIcon('icon/freehand_icon.png'), "Free Hand", self)
        freehand_action.triggered.connect(self.draw_freehand)
        toolbar.addAction(freehand_action)

        toolbar.addSeparator()  # 구분선

        '''
        보기 도구
        '''

        # 확대 액션
        zoom_in_action = QAction(
            QIcon('icon/zoom_in_icon.png'), "Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        # 축소 액션
        zoom_out_action = QAction(
            QIcon('icon/zoom_out_icon.png'), "Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        # 창 중앙 정렬
        screen_geometry = QApplication.desktop().availableGeometry()
        center_x = (screen_geometry.width() - self.width()) // 2
        center_y = (screen_geometry.height() - self.height()) // 2
        self.move(center_x, center_y)
        
    def set_status_bar(self):
        try:
            wl = self.ds.WindowCenter
            ww = self.ds.WindowWidth
            # print(wl, ww)
            self.statusBar().showMessage(f"WL: {wl} WW:{ww}")
        except AttributeError:
            pass

    def open_file(self):
        # 파일 열기 기능 구현
        fname = QFileDialog.getOpenFileName(self, 'Open file', './')
        label = False
        file_name = fname[0].split(sep='/')[-1].split(sep=".")[0]
        path = os.path.dirname(fname[0])
        try:
            os.mkdir(path + f"/{file_name}")
        except FileExistsError:
            pass

        if fname[0]:
            self.ds = dcmread(fname[0])
            with self.ds:
                ds = self.ds
                # print(ds)
                self.ax = self.canvas.figure.subplots()
                pixel = ds.pixel_array
                self.frame_number = 0
                if len(pixel.shape) == 3:
                    self.image = ds.pixel_array[0]
                    self.ax.imshow(ds.pixel_array[0], cmap=plt.cm.gray)
                else:
                    self.image = ds.pixel_array
                    self.ax.imshow(ds.pixel_array, cmap=plt.cm.gray)
            self.set_status_bar()

        self.fname = path + f"/{file_name}/" + f"{self.frame_number}.txt"
        # print(self.fname)
        try:
            with open(self.fname, "r") as f:
                t = json.load(f)
                self.label_dict["line"] = t["line"]
                self.label_dict["rectangle"] = t["rectangle"]
                self.label_dict["circle"] = t["circle"]
                self.label_dict["freehand"] = t["freehand"]
                label = True
        except FileNotFoundError:
            label = False
        if label:
            if self.label_dict["line"]:
                line = self.label_dict["line"]
                for coor in line:
                    self.annotation = self.ax.plot(
                        (coor[0], coor[2]), (coor[1], coor[3]), color='red')[0]
                    self.canvas.draw()
            if self.label_dict["rectangle"]:
                rec = self.label_dict["rectangle"]
                for coor in rec:
                    self.annotation = self.ax.add_patch(
                        Rectangle((coor[0], coor[1]), coor[2], coor[3], fill=False, edgecolor='red'))
                self.canvas.draw()
            if self.label_dict["circle"]:
                cir = self.label_dict["circle"]
                for coor in cir:
                    self.annotation = self.ax.add_patch(
                        Circle(coor[0], coor[1], fill=False, edgecolor='red'))
                self.canvas.draw()

            if self.label_dict["freehand"]:
                freehand = self.label_dict["freehand"]
                for fh in freehand:
                    x_coords, y_coords = zip(*fh)
                    self.annotation = self.ax.plot(
                        x_coords, y_coords, color='red')
        print("Open File")
        self.canvas.draw()
        plt.show()

    def save(self):
        # 저장 기능 구현
        with open(f"{self.fname}", 'w') as f:
            f.write(json.dumps(self.label_dict))
        print("Save...")

    def save_as(self):
        # 다른 이름으로 저장 기능 구현
        print("Save As...")

    def windowing_input_dialog(self):
        # Windowing 적용 기능 구현
        ww, ww_flag = QInputDialog.getText(self, "Change Windowing Value", "Enter the WW: ")

        if ww_flag:
            wl, wl_flag = QInputDialog.getText(self, "Change Windowing Value", "Enter the WL: ")

            if wl_flag:
                self.apply_windowing(ww, wl)
                #print(f"WW: {ww}")
                #print(f"WL: {wl}")            
        print("Apply Windowing")

    def apply_windowing(self, ww, wl):
        self.ds.WindowCenter = wl
        self.ds.WindowWidth = ww
        self.set_status_bar()
        print(wl, ww)
        modality_lut_image = apply_modality_lut(self.image, self.ds)
        voi_lut_image = apply_voi_lut(modality_lut_image, self.ds)

        comparison = voi_lut_image == self.image
        mismatch_count = np.count_nonzero(comparison == False)
        print(voi_lut_image)
        print(mismatch_count)

        self.ax.imshow(voi_lut_image, cmap=plt.cm.gray)
        self.canvas.draw()     

    def draw_annotation(self):
        if self.annotation_mode == "line":
            if self.line_start and self.line_end and self.is_drawing == False:
                x = [self.line_start[0], self.line_end[0]]
                y = [self.line_start[1], self.line_end[1]]
                self.annotation = self.ax.plot(x, y, color='red')[0]
                self.canvas.draw()
                self.label_dict["line"].append((x[0], y[0], x[1], y[1]))

        elif self.annotation_mode == "rectangle":
            if self.start and self.end and self.is_drawing == False:
                width = abs(self.start[0] - self.end[0])
                height = abs(self.start[1] - self.end[1])
                x = min(self.start[0], self.end[0])
                y = min(self.start[1], self.end[1])
                self.annotation = self.ax.add_patch(
                    Rectangle((x, y), width, height, fill=False, edgecolor='red'))
                self.canvas.draw()
                self.label_dict["rectangle"].append((x, y, width, height))

        elif self.annotation_mode == "circle":
            if self.center and self.radius and self.is_drawing == False:
                self.annotation = self.ax.add_patch(
                    Circle(self.center, self.radius, fill=False, edgecolor='red'))
                self.canvas.draw()
                self.label_dict["circle"].append((self.center, self.radius))

        elif self.annotation_mode == "freehand":
            if self.is_drawing == False and len(self.points) > 1:
                x, y = zip(*self.points)
                self.annotation = self.ax.plot(x, y, color='red')
                self.canvas.draw()
                self.label_dict["freehand"].append(self.points)

    def draw_straight_line(self):
        # 직선 그리기 기능 구현
        self.canvas.mpl_connect('button_press_event', self.on_line_mouse_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_line_mouse_move)
        self.canvas.mpl_connect('button_release_event',
                                self.on_line_mouse_release)

        self.annotation_mode = "line"
        self.line_start = None
        self.line_end = None
        self.is_drawing = False

    def on_line_mouse_press(self, event):
        if event.button == 1:
            self.is_drawing = True
            self.line_start = (event.xdata, event.ydata)

    def on_line_mouse_move(self, event):
        if self.is_drawing:
            self.line_end = (event.xdata, event.ydata)
            self.draw_annotation()

    def on_line_mouse_release(self, event):
        if event.button == 1:
            self.is_drawing = False
            self.line_end = (event.xdata, event.ydata)
            self.draw_annotation()

    def draw_circle(self):
        self.canvas.mpl_connect('button_press_event',
                                self.on_mouse_circle_press)
        self.canvas.mpl_connect('motion_notify_event',
                                self.on_mouse_circle_move)
        self.canvas.mpl_connect('button_release_event',
                                self.on_mouse_circle_release)

        self.annotation_mode = "circle"
        self.center = None
        self.radius = None
        self.is_drawing = False

    def on_mouse_circle_press(self, event):
        # print("cirlce_press")
        if event.button == 1:
            self.is_drawing = True
            self.center = (event.xdata, event.ydata)

    def on_mouse_circle_move(self, event):
        if self.is_drawing:
            dx = event.xdata - self.center[0]
            dy = event.ydata - self.center[1]
            self.radius = np.sqrt(dx ** 2 + dy ** 2)
            self.draw_annotation()

    def on_mouse_circle_release(self, event):
        if event.button == 1:  # Left mouse button
            self.is_drawing = False
            dx = event.xdata - self.center[0]
            dy = event.ydata - self.center[1]
            self.radius = np.sqrt(dx ** 2 + dy ** 2)
            self.draw_annotation()

    def draw_rectangle(self):
        # 사각형 그리기 기능 구현
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)

        self.annotation_mode = "rectangle"
        self.start = None
        self.end = None
        self.is_drawing = False

    def on_mouse_press(self, event):
        print("rec_press")
        if event.button == 1:
            self.is_drawing = True
            self.start = (event.xdata, event.ydata)

    def on_mouse_move(self, event):
        if self.is_drawing:
            self.end = (event.xdata, event.ydata)
            self.draw_annotation()

    def on_mouse_release(self, event):
        if event.button == 1:
            self.is_drawing = False
            self.end = (event.xdata, event.ydata)
            self.draw_annotation()

    def draw_curve(self):
        # 곡선 그리기 기능 구현
        print("Draw Curve")

    def draw_freehand(self):
        # 자유형 그리기 기능 구현
        self.canvas.mpl_connect('button_press_event',
                                self.on_freehand_mouse_press)
        self.canvas.mpl_connect('motion_notify_event',
                                self.on_freehand_mouse_move)
        self.canvas.mpl_connect('button_release_event',
                                self.on_freehand_mouse_release)

        self.annotation_mode = "freehand"
        self.points = []
        self.is_drawing = False

    def on_freehand_mouse_press(self, event):
        if event.button == 1:
            self.is_drawing = True
            self.points = [(event.xdata, event.ydata)]

    def on_freehand_mouse_move(self, event):
        if self.is_drawing:
            self.points.append((event.xdata, event.ydata))
            self.draw_annotation()

    def on_freehand_mouse_release(self, event):
        if event.button == 1:
            self.is_drawing = False
            self.draw_annotation()

    def zoom_in(self):
        current_xlim = self.ax.get_xlim()
        current_ylim = self.ax.get_ylim()

        new_xlim = (current_xlim[0] * 0.9, current_xlim[1] * 0.9)
        new_ylim = (current_ylim[0] * 0.9, current_ylim[1] * 0.9)

        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)

        self.canvas.mpl_connect('button_press_event', self.on_pan_mouse_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_pan_mouse_move)
        self.canvas.mpl_connect('button_release_event',
                                self.on_pan_mouse_release)

        self.canvas.draw()

    def on_pan_mouse_press(self, event):  # zoom in 상태에서 화면 이동
        if event.button == 1 and not self.is_panning:
            self.is_panning = True
            self.pan_start = (event.x, event.y)

    def on_pan_mouse_move(self, event):
        if self.is_panning:
            x_diff = event.x - self.pan_start[0]
            y_diff = event.y - self.pan_start[1]

            current_xlim = self.ax.get_xlim()
            current_ylim = self.ax.get_ylim()

            new_xlim = (current_xlim[0] - x_diff, current_xlim[1] - x_diff)
            new_ylim = (current_ylim[0] - y_diff, current_ylim[1] - y_diff)

            image_width = self.ds.pixel_array.shape[1]
            image_height = self.ds.pixel_array.shape[0]

            # DICOM 이미지 경계 안에서 화면 이동하는지 확인
            if new_xlim[0] >= 0 and new_xlim[1] <= image_width:
                self.ax.set_xlim(new_xlim)

            if new_ylim[0] >= 0 and new_ylim[1] <= image_height:
                self.ax.set_ylim(new_ylim)

            self.pan_start = (event.x, event.y)
            self.canvas.draw()

    def on_pan_mouse_release(self, event):
        if event.button == 1 and self.is_panning:
            self.is_panning = False

    def zoom_out(self):
        current_xlim = self.ax.get_xlim()
        current_ylim = self.ax.get_ylim()

        new_xlim = (current_xlim[0] * 1.1, current_xlim[1] * 1.1)
        new_ylim = (current_ylim[0] * 1.1, current_ylim[1] * 1.1)

        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)

        self.canvas.draw()


app = QApplication(sys.argv)

window = MyWindow()
window.show()
sys.exit(app.exec_())
