"""CPU 占用太高"""
import cv2
import threading


class Stack:

    def __init__(self, stack_size):
        self.items = []
        self.stack_size = stack_size

    def is_empty(self):
        return len(self.items) == 0

    def pop(self):
        return self.items.pop()

    def peek(self):
        if not self.is_empty():
            return self.items[len(self.items) - 1]

    def size(self):
        return len(self.items)

    def push(self, item):
        if self.size() >= self.stack_size:
            for i in range(self.size() - self.stack_size + 1):
                self.items.remove(self.items[0])
        self.items.append(item)


def capture_thread(video_path, frame_buffer, lock):
    print("capture_thread start")
    vid = cv2.VideoCapture(video_path)
    if not vid.isOpened():
        raise IOError("Couldn't open webcam or video")
    while True:
        return_value, frame = vid.read()
        if return_value is not True:
            break
        lock.acquire()
        frame_buffer.push(frame)
        lock.release()
        cv2.waitKey(25)


def play_thread(frame_buffer, lock):
    print("detect_thread start")
    print("detect_thread frame_buffer size is", frame_buffer.size())

    while True:
        if frame_buffer.size() > 0:
            lock.acquire()
            frame = frame_buffer.pop()
            lock.release()
            # TODO 算法
            cv2.imshow("result", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


url = 'rtsp://admin:admin777@10.86.77.12:554/h264/ch1/sub/av_stream'

frame_buffer = Stack(3)
lock = threading.RLock()
t1 = threading.Thread(target=capture_thread, args=(url, frame_buffer, lock))
t1.start()
t2 = threading.Thread(target=play_thread, args=(frame_buffer, lock))
t2.start()
