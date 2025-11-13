"""
Enhanced NFC Bridge API with Rate Limiting and Validation

High-performance NFC scanning API with:
- Rate limiting per client
- Enhanced validation
- Retry mechanisms
- Background processing
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import asyncio
import json
import hashlib
import time
import uuid
from functools import lru_cache

from backend.app.database import get_db
from backend.app.models import Employee, PunchRecord, PunchType
from backend.app.services.punch_service import PunchService
from backend.app.websocket_enhanced import get_enhanced_connection_manager
import logging

logger = logging.getLogger(__name__)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

# Add rate limit exceeded handler
router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Request/Response Models
class NFCScanRequest(BaseModel):
    """NFC scan request model with validation"""
    scan_id: str = Field(..., description="Unique scan identifier")
    client_id: str = Field(..., description="Client device identifier")
    card_data: Dict[str, Any] = Field(..., description="Encrypted card data")
    timestamp: int = Field(..., description="Scan timestamp in milliseconds")
    device_info: Optional[Dict[str, Any]] = Field(None, description="Device information")
    retry_count: int = Field(0, ge=0, le=3, description="Retry attempt count")
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp is within acceptable range"""
        current_time = int(time.time() * 1000)
        # Allow 5 minutes time difference
        if abs(current_time - v) > 300000:
            raise ValueError("Timestamp is too far from current time")
        return v
    
    @validator('scan_id')
    def validate_scan_id(cls, v):
        """Validate scan ID format"""
        if not v or len(v) < 10:
            raise ValueError("Invalid scan_id format")
        return v


class NFCScanResult(BaseModel):
    """NFC scan result model"""
    scan_id: str
    success: bool
    message: str
    employee_info: Optional[Dict[str, Any]] = None
    punch_record: Optional[Dict[str, Any]] = None
    processing_time_ms: float
    server_timestamp: str


class NFCBatchScanRequest(BaseModel):
    """Batch NFC scan request"""
    scans: List[NFCScanRequest]
    client_id: str
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


# Validation helpers
class NFCValidator:
    """Enhanced NFC data validation"""
    
    @staticmethod
    def validate_card_data(card_data: Dict[str, Any]) -> bool:
        """Validate NFC card data structure"""
        required_fields = ["idm", "type"]
        
        # Check required fields
        for field in required_fields:
            if field not in card_data:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate IDm format (should be hex string)
        idm = card_data.get("idm", "")
        if not isinstance(idm, str) or len(idm) < 16:
            logger.error(f"Invalid IDm format: {idm}")
            return False
        
        # Validate card type
        valid_types = ["felica", "suica", "pasmo", "icoca", "pitapa"]
        card_type = card_data.get("type", "").lower()
        if card_type not in valid_types:
            logger.error(f"Invalid card type: {card_type}")
            return False
        
        return True
    
    @staticmethod
    def sanitize_card_data(card_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and normalize card data"""
        sanitized = {}
        
        # Extract and clean IDm
        idm = card_data.get("idm", "").strip().upper()
        sanitized["idm"] = idm
        
        # Normalize card type
        card_type = card_data.get("type", "").lower()
        sanitized["type"] = card_type
        
        # Add additional safe fields
        safe_fields = ["pmm", "system_code", "service_code"]
        for field in safe_fields:
            if field in card_data:
                sanitized[field] = card_data[field]
        
        return sanitized


# Cache for frequent queries
@lru_cache(maxsize=1000)
def get_employee_by_card_id_cached(card_id_hash: str, db_id: int):
    """Cached employee lookup (cache invalidated by db_id change)"""
    # This is a placeholder - actual implementation would query database
    pass


# Retry mechanism
class RetryHandler:
    """Handle retry logic for failed requests"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.5):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_storage = {}  # In production, use Redis
    
    async def should_retry(self, scan_id: str, current_attempt: int) -> bool:
        """Check if request should be retried"""
        if current_attempt >= self.max_retries:
            return False
        
        # Check retry history
        retry_info = self.retry_storage.get(scan_id, {})
        last_attempt = retry_info.get("last_attempt", 0)
        
        # Calculate backoff time
        backoff_time = (self.backoff_factor ** current_attempt) * 1000  # ms
        time_since_last = (time.time() * 1000) - last_attempt
        
        return time_since_last >= backoff_time
    
    def record_retry(self, scan_id: str, attempt: int):
        """Record retry attempt"""
        self.retry_storage[scan_id] = {
            "attempts": attempt,
            "last_attempt": time.time() * 1000,
            "created_at": self.retry_storage.get(scan_id, {}).get("created_at", time.time())
        }
    
    def cleanup_old_retries(self, older_than_seconds: int = 300):
        """Clean up old retry records"""
        current_time = time.time()
        to_remove = []
        
        for scan_id, info in self.retry_storage.items():
            if current_time - info.get("created_at", 0) > older_than_seconds:
                to_remove.append(scan_id)
        
        for scan_id in to_remove:
            del self.retry_storage[scan_id]


# Initialize retry handler
retry_handler = RetryHandler()


# API Endpoints
@router.post("/nfc/scan-result", response_model=NFCScanResult)
@limiter.limit("100/minute")
async def enhanced_nfc_scan_result(
    request: NFCScanRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Process NFC scan result with enhanced validation and performance
    
    Features:
    - Rate limiting (100 requests/minute per IP)
    - Enhanced validation
    - Background processing
    - Performance monitoring
    - Retry support
    """
    start_time = time.time()
    
    try:
        # Validate card data
        if not NFCValidator.validate_card_data(request.card_data):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid card data format"
            )
        
        # Sanitize card data
        sanitized_card_data = NFCValidator.sanitize_card_data(request.card_data)
        
        # Check retry eligibility
        if request.retry_count > 0:
            if not await retry_handler.should_retry(request.scan_id, request.retry_count):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Maximum retry attempts exceeded"
                )
            retry_handler.record_retry(request.scan_id, request.retry_count)
        
        # Process scan
        result = await process_nfc_scan(
            scan_request=request,
            sanitized_card_data=sanitized_card_data,
            db=db
        )
        
        # Add background tasks
        background_tasks.add_task(
            log_scan_analytics,
            request=request,
            result=result,
            processing_time=time.time() - start_time
        )
        
        background_tasks.add_task(
            broadcast_scan_update,
            client_id=request.client_id,
            result=result
        )
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        return NFCScanResult(
            scan_id=request.scan_id,
            success=result["success"],
            message=result["message"],
            employee_info=result.get("employee_info"),
            punch_record=result.get("punch_record"),
            processing_time_ms=processing_time_ms,
            server_timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing NFC scan: {str(e)}", exc_info=True)
        
        # Record error for retry
        if request.retry_count < retry_handler.max_retries:
            retry_handler.record_retry(request.scan_id, request.retry_count)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process scan: {str(e)}"
        )


@router.post("/nfc/batch-scan", response_model=List[NFCScanResult])
@limiter.limit("20/minute")
async def batch_nfc_scan(
    batch_request: NFCBatchScanRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Process multiple NFC scans in batch for better performance
    
    Features:
    - Batch processing up to 10 scans
    - Parallel processing
    - Consolidated response
    """
    if len(batch_request.scans) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 scans per batch"
        )
    
    # Process scans in parallel
    tasks = []
    for scan in batch_request.scans:
        task = process_nfc_scan_async(scan, db)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Format results
    scan_results = []
    for i, (scan, result) in enumerate(zip(batch_request.scans, results)):
        if isinstance(result, Exception):
            scan_results.append(NFCScanResult(
                scan_id=scan.scan_id,
                success=False,
                message=f"Processing error: {str(result)}",
                processing_time_ms=0,
                server_timestamp=datetime.now().isoformat()
            ))
        else:
            scan_results.append(result)
    
    # Background analytics
    background_tasks.add_task(
        log_batch_analytics,
        batch_id=batch_request.batch_id,
        results=scan_results
    )
    
    return scan_results


@router.get("/nfc/scan-status/{scan_id}")
@limiter.limit("200/minute")
async def get_scan_status(
    scan_id: str,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Get status of a specific scan
    
    Useful for checking async processing status
    """
    # In production, this would check Redis or database
    # For now, return mock status
    return {
        "scan_id": scan_id,
        "status": "completed",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/nfc/validate-card")
@limiter.limit("300/minute")
async def validate_nfc_card(
    card_data: Dict[str, Any],
    req: Request
):
    """
    Validate NFC card data without processing
    
    Quick validation endpoint for client-side checks
    """
    try:
        is_valid = NFCValidator.validate_card_data(card_data)
        sanitized = NFCValidator.sanitize_card_data(card_data) if is_valid else None
        
        return {
            "valid": is_valid,
            "sanitized_data": sanitized,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.websocket("/ws/nfc/{client_id}")
async def nfc_websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    db: Session = Depends(get_db)
):
    """
    Enhanced WebSocket endpoint for NFC real-time communication
    
    Features:
    - Automatic reconnection support
    - Message batching
    - Performance monitoring
    """
    metadata = {
        "device_type": websocket.headers.get("X-Device-Type", "unknown"),
        "app_version": websocket.headers.get("X-App-Version", "unknown"),
        "user_agent": websocket.headers.get("User-Agent", "unknown")
    }
    
    # Connect using enhanced manager
    connected = await get_enhanced_connection_manager().optimized_connect(
        websocket=websocket,
        client_id=client_id,
        metadata=metadata
    )
    
    if not connected:
        await websocket.close(code=4000, reason="Connection limit reached")
        return
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Process different message types
                if message.get("type") == "ping":
                    await get_enhanced_connection_manager().send_personal_message(
                        client_id,
                        {"type": "pong", "timestamp": datetime.now().isoformat()}
                    )
                
                elif message.get("type") == "scan":
                    # Process scan through regular API
                    scan_request = NFCScanRequest(**message.get("data", {}))
                    result = await process_nfc_scan_async(scan_request, db)
                    
                    await get_enhanced_connection_manager().send_personal_message(
                        client_id,
                        {
                            "type": "scan_result",
                            "data": result,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                
                elif message.get("type") == "subscribe":
                    # Handle subscription to specific events
                    events = message.get("events", [])
                    logger.info(f"Client {client_id} subscribed to: {events}")
                
            except json.JSONDecodeError:
                await get_enhanced_connection_manager().send_personal_message(
                    client_id,
                    {"type": "error", "message": "Invalid JSON format"}
                )
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await get_enhanced_connection_manager().send_personal_message(
                    client_id,
                    {"type": "error", "message": str(e)}
                )
    
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        await get_enhanced_connection_manager().disconnect(client_id)


# Helper functions
async def process_nfc_scan(
    scan_request: NFCScanRequest,
    sanitized_card_data: Dict[str, Any],
    db: Session
) -> Dict[str, Any]:
    """Process individual NFC scan"""
    try:
        # Hash the card ID for privacy
        card_idm = sanitized_card_data["idm"]
        card_id_hash = hashlib.sha256(card_idm.encode()).hexdigest()
        
        # Look up employee
        employee = db.query(Employee).filter(
            Employee.card_id == card_id_hash
        ).first()
        
        if not employee:
            return {
                "success": False,
                "message": "Card not registered",
                "employee_info": None,
                "punch_record": None
            }
        
        # Determine punch type (simplified logic)
        # In production, this would check last punch status
        punch_type = PunchType.IN  # Default to IN
        
        # Create punch record
        punch_service = PunchService(db)
        punch_result = await punch_service.create_punch(
            card_idm=card_idm,
            punch_type=punch_type,
            device_type="nfc_reader",
            note=f"Scan ID: {scan_request.scan_id}"
        )
        
        return {
            "success": True,
            "message": punch_result["message"],
            "employee_info": {
                "id": employee.id,
                "name": employee.name,
                "department": employee.department
            },
            "punch_record": {
                "id": punch_result["punch_record"]["id"],
                "type": punch_result["punch_record"]["punch_type"],
                "time": punch_result["punch_record"]["punch_time"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error in process_nfc_scan: {e}")
        return {
            "success": False,
            "message": f"Processing error: {str(e)}",
            "employee_info": None,
            "punch_record": None
        }


async def process_nfc_scan_async(scan_request: NFCScanRequest, db: Session) -> NFCScanResult:
    """Async wrapper for scan processing"""
    start_time = time.time()
    
    # Validate and sanitize
    if not NFCValidator.validate_card_data(scan_request.card_data):
        return NFCScanResult(
            scan_id=scan_request.scan_id,
            success=False,
            message="Invalid card data",
            processing_time_ms=0,
            server_timestamp=datetime.now().isoformat()
        )
    
    sanitized_card_data = NFCValidator.sanitize_card_data(scan_request.card_data)
    
    # Process scan
    result = await process_nfc_scan(scan_request, sanitized_card_data, db)
    
    processing_time_ms = (time.time() - start_time) * 1000
    
    return NFCScanResult(
        scan_id=scan_request.scan_id,
        success=result["success"],
        message=result["message"],
        employee_info=result.get("employee_info"),
        punch_record=result.get("punch_record"),
        processing_time_ms=processing_time_ms,
        server_timestamp=datetime.now().isoformat()
    )


async def log_scan_analytics(request: NFCScanRequest, result: Dict[str, Any], processing_time: float):
    """Log scan analytics for monitoring"""
    analytics_data = {
        "scan_id": request.scan_id,
        "client_id": request.client_id,
        "success": result["success"],
        "processing_time": processing_time,
        "timestamp": datetime.now().isoformat(),
        "card_type": request.card_data.get("type"),
        "retry_count": request.retry_count
    }
    
    # In production, send to analytics service
    logger.info(f"Scan analytics: {json.dumps(analytics_data)}")


async def log_batch_analytics(batch_id: str, results: List[NFCScanResult]):
    """Log batch processing analytics"""
    success_count = sum(1 for r in results if r.success)
    total_processing_time = sum(r.processing_time_ms for r in results)
    
    analytics_data = {
        "batch_id": batch_id,
        "total_scans": len(results),
        "success_count": success_count,
        "failure_count": len(results) - success_count,
        "avg_processing_time_ms": total_processing_time / len(results) if results else 0,
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"Batch analytics: {json.dumps(analytics_data)}")


async def broadcast_scan_update(client_id: str, result: Dict[str, Any]):
    """Broadcast scan update to relevant clients"""
    update_message = {
        "type": "scan_update",
        "client_id": client_id,
        "success": result["success"],
        "employee_info": result.get("employee_info"),
        "timestamp": datetime.now().isoformat()
    }
    
    # Broadcast to monitoring clients
    await get_enhanced_connection_manager().broadcast(
        update_message,
        exclude={client_id}  # Don't send back to originator
    )


# Cleanup task
async def cleanup_retry_records():
    """Periodic cleanup of old retry records"""
    while True:
        try:
            retry_handler.cleanup_old_retries(300)  # 5 minutes
            await asyncio.sleep(60)  # Run every minute
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(60)