import time

class TokenBucket:
    def __init__(self, capacity, fill_rate):
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_fill = time.time()

    def consume(self, tokens):
        if tokens <= self.tokens:
            self.tokens -= tokens
            return True
        else:
            return False

    def fill_bucket(self):
        now = time.time()
        time_passed = now - self.last_fill
        new_tokens = time_passed * self.fill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_fill = now

