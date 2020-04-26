import os
import re
import threading
import time
import schedule
import shutil

from .client import Client, run_in_background
from .pygtk import _take_gtk_screen_size, _grab_gtk_pb
from .utils import _norm_path

from mss import mss
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from robot.utils import is_truthy, timestr_to_secs



class GifClient(Client):

    def __init__(self, screenshot_module, screenshot_directory):
        Client.__init__(self)
        self.screenshot_module = screenshot_module
        self._given_screenshot_dir = _norm_path(screenshot_directory)
        self._stop_condition = threading.Event()
        self.gif_frame_time = 125
        self.gif_screenshot_dir = _norm_path(screenshot_directory + '/robot_atest_gifs')

    def start_gif_recording(self, name, size_percentage,
                            embed, embed_width):
        self.name = name
        self.embed = embed
        self.embed_width = embed_width
        self.futures = self.grab_frames(size_percentage, self._stop_condition)
        self.clear_thread_queues()

    def _sorted_alphanumeric(self, data):
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        return sorted(data, key=alphanum_key)

    def stop_gif_recording(self):
        self._stop_thread()
        # self.set_screenshot_directory(self.gif_location)
        path = self._save_screenshot_path(basename=self.name, format='gif')
        list_of_images = self._sorted_alphanumeric(os.listdir(self.gif_screenshot_dir))
        first = list_of_images[0]
        img = Image.open(_norm_path(self.gif_screenshot_dir + '/' + first))
        while len(list_of_images) > 1:
            for i in list(list_of_images):
                image = _norm_path(self.gif_screenshot_dir + '/' + i)
                screenshot = [Image.open(image)]
                img.save(path, save_all=False, append_images=screenshot, duration=self.gif_frame_time,
                         optimize=True, loop=0)
                list_of_images.remove(i)
        # shutil.rmtree(self.gif_screenshot_dir)
        if is_truthy(self.embed):
            self._embed_screenshot(path, self.embed_width)
        return path

    @run_in_background
    def grab_frames(self, size_percentage, stop):
        if self.screenshot_module and self.screenshot_module.lower() == 'pygtk':
            self._grab_frames_gtk(size_percentage, stop)
        else:
            self._grab_frames_mss(size_percentage, stop)

    def _grab_frames_gtk(self, size_percentage, stop):
        self.gif_location = self._given_screenshot_dir
        if not os.path.exists(self.gif_screenshot_dir):
            os.mkdir(self.gif_screenshot_dir)
        self.set_screenshot_directory(self.gif_screenshot_dir)
        width, height = _take_gtk_screen_size()
        w = int(width * size_percentage)
        h = int(height * size_percentage)
        while not stop.isSet():
            pb = _grab_gtk_pb()
            img = Image.frombuffer('RGB', (width, height), pb.get_pixels(), 'raw', 'RGB')
            if size_percentage != 1:
                img.resize((w, h))
            schedule.every(0.1).seconds.do(self._thread_save, img)
            schedule.run_pending()
            time.sleep(self.gif_frame_time / 1000)

    def _grab_frames_mss(self, size_percentage, stop):
        self.set_screenshot_directory(self.gif_screenshot_dir)
        with mss() as sct:
            width = int(sct.grab(sct.monitors[0]).width * size_percentage)
            height = int(sct.grab(sct.monitors[0]).height * size_percentage)
            while not stop.isSet():
                sct_img = sct.grab(sct.monitors[0])
                img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
                if size_percentage != 1:
                    img.resize((width, height))
                schedule.every(0.05).seconds.do(self._thread_save, img)
                schedule.run_pending()
                time.sleep(self.gif_frame_time / 1000)

    def _thread_save(self, frame):
        path = self._save_screenshot_path(basename=self.name, format='jpg')
        job_thread = threading.Thread(target=self._frames_to_save, args=(frame, path,))
        job_thread.start()

    def _frames_to_save(self, frame, path):
        if self.screenshot_module and self.screenshot_module.lower() == 'pygtk':
            with mss() as sct:
                frame.save(path)
        else:
            frame.save(path)
