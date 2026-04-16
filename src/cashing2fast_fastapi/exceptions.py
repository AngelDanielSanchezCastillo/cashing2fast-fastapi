from typing import Any

class PaymentRequiredException(Exception):
    def __init__(self, message: str = "Pago Requerido", error: Any = None):
        self.message = message
        self.error = error
