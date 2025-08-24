"""
Core services for AutoFarming Bot
"""
try:
    from .posting_service import PostingService
except ImportError:
    PostingService = None

try:
    from .worker_manager import WorkerManager
except ImportError:
    WorkerManager = None

try:
    from .auto_poster import AutoPoster
except ImportError:
    AutoPoster = None

try:
    from .payment_processor import PaymentProcessor
except ImportError:
    PaymentProcessor = None

__all__ = ['PostingService', 'WorkerManager', 'AutoPoster', 'PaymentProcessor']
