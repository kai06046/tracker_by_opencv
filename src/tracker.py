# for cx_freeze (deployment)
import pywt._extensions._cwt
from scipy.linalg import _fblas
import scipy.spatial.ckdtree
# for image difference
from scipy.linalg import norm
from scipy import sum, average

#############################################
# for Tracker class
import os, cv2, sys, time
import numpy as np
import tkinter as tk
import warnings
# from tkinter import ttk
import _tkinter

from src.common import * # comman function 
from src.keyhandler import KeyHandler
from src.interface import Interface
from src.detector import MotionDetector, BeetleDetector, RatDetector

from tkinter.filedialog import askopenfilename
from tkinter.messagebox import askyesno, askokcancel, showerror, showwarning, showinfo

# for deep learning model
from keras.models import load_model

args = {'model_name': 'nadam_resnet_first_3_freeze_3', 'frame_ind': 1, 'run_model': True, 'save_pos': False}

# basic variables
WINDOW_NAME = 'Burying Beetle Tracker'
FPS, FOURCC = 30, cv2.VideoWriter_fourcc(*'XVID')
FONT = cv2.FONT_HERSHEY_TRIPLEX
COLOR = [(0, 255, 0), (255, 100, 10), (20, 50, 255), (0, 255, 255), (255, 255, 0), (255, 0, 255), (255, 255, 255), (0, 0, 0)]
WRITE = True # if True, write output video

# variables for online update xgboost model
RATIO = [0, 0.5, 1, 1.5]
N_ANGLE = 36
INTERVAL_FRAME = 10

PREFIX = 'training'

class Tracker(KeyHandler, Interface, BeetleDetector, MotionDetector, RatDetector):
    
    def __init__(self, video_path, fps = None, fourcc = None, window_name = None, track_alg = None, object_name = None):
        
        self._video = video_path
        video = cv2.VideoCapture(find_data_file(self._video))
        self.fourcc = fourcc if fourcc else FOURCC
        self.fps = fps if fps else FPS
        self.width = int(video.get(3))
        self.height = int(video.get(4))
        self.fps = int(video.get(5))
        self.resolution = (self.width, self.height)
        self.file_name = self._video.split('/')[-1]
        self.video_name = self.file_name.split('.')[0]

        self.window_name = window_name if window_name else WINDOW_NAME
        self.track_alg = track_alg if track_alg else TRACK_ALGORITHM
        self.color = COLOR
        self.font = FONT
        self.count = args['frame_ind']# index of frame
        self.orig_gray = None # original grayscale frame
        self.orig_col = None # original BGR frame
        self.frame = None # current frame
        self.object_name = []
        self.deleted_name = []
        
        self._start = None
        self._n_pass_frame = 0
        
        # setup tracker
        self.tracker = cv2.MultiTracker(self.track_alg)
        
        # different mode while tracking
        self._add_box = True # flag of add bounding box mode
        self._retargeting = False # flag of retargeting bounding box mode
        self._delete_box = False # flag of delete bounding box mode
        self._pause = False # flag of pause mode
        
        # initialize tkinter GUI variable
        self._askname  = None
        self.root = None
        self.cb = None

        # mouse coordinate
        self._roi_pts = []
        self._mv_pt = None
        
        # initiate bounding box
        self._bboxes = []
        self._roi = []
        self._init_bbox = []
        self._len_bbox = 0
        
        # index of beetle
        self._n = 0
        self._fix_target = False
        
        # variables for detector model
        # flag
        self._run_model = args['run_model']
        self._update = False
        # load model data or weight
        self._model = load_model('model/%s.h5' % args['model_name'])
        
        self._stop_obj = None
        self._is_stop = None

        # background subtractor model, for adding potential bounding box
        self._run_motion = True
        self._bs = cv2.createBackgroundSubtractorMOG2()
        self._pot_rect =  []

        # variables for online update model
        self._record = {}
        self._n_angle = N_ANGLE
        self._ratio = RATIO
        self._itv_f = INTERVAL_FRAME

        # initiate rat contour
        self._show_rat = False
        self.on_rat = []
        self.rat_cnt = []
