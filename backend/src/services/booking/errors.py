class BookingError(Exception):
    remaining_attempts: int | None

    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.remaining_attempts = None
