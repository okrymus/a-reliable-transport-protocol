import time

class Timer(object):
    # to indicate that the timer is stopped
    STOP_TIMER = -1

    def __init__(self, duration):
        self.start_time = self.STOP_TIMER
        self.duration = duration

    # starts the timer
    def start(self):
        if (self.start_time == self.STOP_TIMER):
            self.start_time = time.time()

    # the timer is runnning or not
    def running(self):
        isRunning = self.start_time != self.STOP_TIMER
        return isRunning

    # stops the timer
    def stop(self):
        if (self.start_time != self.STOP_TIMER):
            self.start_time = self.STOP_TIMER

    # is it time out? 
    def timeout(self):
        if (not self.running()):
            return False
        else:
            elapse = time.time() - self.start_time
            return elapse >= self.duration
    