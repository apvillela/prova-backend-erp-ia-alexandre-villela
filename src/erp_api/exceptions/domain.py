class ErpApiError(Exception):
    """Base das exceções de domínio: o service levanta, a camada HTTP traduz em status code."""


class NotFoundError(ErpApiError): ...


class ConflictError(ErpApiError): ...


class ExternalServiceError(ErpApiError): ...
