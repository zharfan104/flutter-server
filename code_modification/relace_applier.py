"""
Relace Code Applier Service
Handles integration with Relace API for precise code modifications
"""

import requests
import json
from typing import Dict, Optional, List
from dataclasses import dataclass

# Import advanced logging and monitoring
try:
    from utils.advanced_logger import logger, LogCategory, LogLevel
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


@dataclass
class RelaceRequest:
    """Request to Relace API"""
    initial_code: str
    edit_snippet: str
    file_path: str


@dataclass
class RelaceResult:
    """Result from Relace API"""
    success: bool
    modified_code: Optional[str] = None
    error: Optional[str] = None
    file_path: Optional[str] = None


class RelaceCodeApplier:
    """
    Service for applying code changes using Relace API
    Provides precise, targeted code modifications instead of full file regeneration
    """
    
    def __init__(self):
        self.api_url = "https://instantapply.endpoint.relace.run/v1/code/apply"
        self.api_key = "rlc-lu6pnPzS2peEuyh39TByRA506aOF-0T9oiLVaQ"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.SYSTEM, "RelaceCodeApplier initialized")
    
    async def apply_fix(self, request: RelaceRequest) -> RelaceResult:
        """
        Apply a code fix using Relace API
        
        Args:
            request: RelaceRequest with initial code and edit snippet
            
        Returns:
            RelaceResult with modified code or error information
        """
        try:
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.CODE_MOD, f"Applying Relace fix to {request.file_path}",
                           context={
                               "file_path": request.file_path,
                               "code_length": len(request.initial_code),
                               "snippet_length": len(request.edit_snippet)
                           })
            
            # Prepare API request
            data = {
                "initialCode": request.initial_code,
                "editSnippet": request.edit_snippet
            }
            
            # Make API call
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result_data = response.json()
                modified_code = result_data.get("mergedCode") or result_data.get("modifiedCode")
                
                if modified_code:
                    if MONITORING_AVAILABLE:
                        logger.info(LogCategory.CODE_MOD, f"Relace fix applied successfully to {request.file_path}")
                    
                    return RelaceResult(
                        success=True,
                        modified_code=modified_code,
                        file_path=request.file_path
                    )
                else:
                    error_msg = f"No modified code returned from Relace API"
                    if MONITORING_AVAILABLE:
                        logger.warn(LogCategory.CODE_MOD, error_msg)
                    
                    return RelaceResult(
                        success=False,
                        error=error_msg,
                        file_path=request.file_path
                    )
            else:
                error_msg = f"Relace API error: {response.status_code} - {response.text}"
                if MONITORING_AVAILABLE:
                    logger.error(LogCategory.CODE_MOD, error_msg)
                
                return RelaceResult(
                    success=False,
                    error=error_msg,
                    file_path=request.file_path
                )
                
        except requests.Timeout:
            error_msg = "Relace API request timed out"
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.CODE_MOD, error_msg)
            
            return RelaceResult(
                success=False,
                error=error_msg,
                file_path=request.file_path
            )
            
        except Exception as e:
            error_msg = f"Relace API error: {str(e)}"
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.CODE_MOD, error_msg)
            
            return RelaceResult(
                success=False,
                error=error_msg,
                file_path=request.file_path
            )
    
    async def apply_multiple_fixes(self, requests: List[RelaceRequest]) -> List[RelaceResult]:
        """
        Apply multiple code fixes using Relace API
        
        Args:
            requests: List of RelaceRequest objects
            
        Returns:
            List of RelaceResult objects
        """
        results = []
        
        for request in requests:
            result = await self.apply_fix(request)
            results.append(result)
            
            # Log progress
            if MONITORING_AVAILABLE:
                status = "SUCCESS" if result.success else "FAILED"
                logger.info(LogCategory.CODE_MOD, f"Relace fix {status} for {request.file_path}")
        
        return results
    
    def test_connection(self) -> bool:
        """
        Test connection to Relace API
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Simple test with minimal code
            test_data = {
                "initialCode": "// test",
                "editSnippet": "// test comment"
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=test_data,
                timeout=10
            )
            
            success = response.status_code in [200, 400]  # 400 might be expected for test data
            
            if MONITORING_AVAILABLE:
                if success:
                    logger.info(LogCategory.SYSTEM, "Relace API connection test successful")
                else:
                    logger.warn(LogCategory.SYSTEM, f"Relace API connection test failed: {response.status_code}")
            
            return success
            
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.SYSTEM, f"Relace API connection test error: {e}")
            return False


# Global instance for easy access
_relace_applier = None

def get_relace_applier() -> RelaceCodeApplier:
    """Get or create the global Relace applier instance"""
    global _relace_applier
    if _relace_applier is None:
        _relace_applier = RelaceCodeApplier()
    return _relace_applier