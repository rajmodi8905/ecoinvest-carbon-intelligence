"""
Centralized LLM Manager - Single LangChain LLM instance for all services

This module provides a singleton LLM instance that's shared across:
- aibot.py
- company_service.py
- chat_service.py
- Any other services that need LLM access

Supports two modes:
- Gemini (default): Uses Google's Gemini API
- Ollama: Uses local Ollama instance

Mode selection via environment variable: LLM_MODE=ollama|gemini

Benefits:
- Single initialization (faster startup)
- Shared token budget and rate limiting
- Consistent model configuration
- Lower memory usage
- Flexible backend switching
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global LLM instance
_llm_instance: Optional[object] = None
_llm_initialized: bool = False

def _create_gemini_llm():
    """Create and return a Gemini LLM instance"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            logger.warning("⚠️ GOOGLE_API_KEY not found - Gemini LLM unavailable")
            return None
        
        llm = ChatGoogleGenerativeAI(
            model="models/gemini-2.5-flash",
            temperature=0.7,
            max_tokens=2048,
            google_api_key=api_key
        )
        
        logger.info("✅ Shared LLM initialized (Gemini 2.5 Flash)")
        return llm
        
    except ImportError as e:
        logger.warning(f"⚠️ LangChain Google GenAI not installed: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini LLM: {e}")
        return None

def _create_ollama_llm():
    """Create and return an Ollama LLM instance"""
    try:
        from langchain_ollama import ChatOllama
        
        # Get Ollama configuration from environment
        ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        ollama_model = os.getenv('OLLAMA_MODEL', 'qwen2.5')
        
        llm = ChatOllama(
            model=ollama_model,
            base_url=ollama_base_url,
            temperature=0.7,
        )
        
        logger.info(f"✅ Shared LLM initialized (Ollama - {ollama_model})")
        return llm
        
    except ImportError as e:
        logger.warning(f"⚠️ LangChain Ollama not installed: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to initialize Ollama LLM: {e}")
        return None

def get_llm():
    """
    Get or create the shared LLM instance (lazy loading).
    
    The LLM mode is determined by the LLM_MODE environment variable:
    - 'ollama' (default): Uses local Ollama instance
    - 'gemini': Uses Google Gemini API
    
    Environment variables:
    - LLM_MODE: 'gemini' or 'ollama' (default: 'ollama')
    - For Gemini:
      - GOOGLE_API_KEY or GEMINI_API_KEY: API key for Gemini
    - For Ollama:
      - OLLAMA_BASE_URL: Base URL for Ollama (default: 'http://localhost:11434')
      - OLLAMA_MODEL: Model name (default: 'qwen2.5')
    
    Returns:
        LLM instance or None if not available
    """
    global _llm_instance, _llm_initialized
    
    if _llm_initialized:
        return _llm_instance
    
    # Get LLM mode from environment (default: ollama)
    llm_mode = os.getenv('LLM_MODE', 'ollama').lower()
    logger.info(f"🔧 Initializing LLM in {llm_mode.upper()} mode...")
    
    try:
        if llm_mode == 'gemini':
            _llm_instance = _create_gemini_llm()
            if _llm_instance is None:
                logger.warning("⚠️ Gemini LLM failed or unavailable, falling back to Ollama mode...")
                _llm_instance = _create_ollama_llm()
        else:  # Default to ollama
            _llm_instance = _create_ollama_llm()
            if _llm_instance is None and (os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')):
                logger.warning("⚠️ Ollama LLM failed or unavailable, falling back to Gemini mode...")
                _llm_instance = _create_gemini_llm()
        
        _llm_initialized = True
        return _llm_instance
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize LLM: {e}")
        _llm_initialized = True
        _llm_instance = None
        return None

def is_llm_available() -> bool:
    """Check if LLM is available without initializing it"""
    if _llm_initialized:
        return _llm_instance is not None
    
    llm_mode = os.getenv('LLM_MODE', 'ollama').lower()
    
    # Check if dependencies are available based on mode
    try:
        if llm_mode == 'ollama':
            from langchain_ollama import ChatOllama
            # Ollama doesn't require API key, just check if package is installed
            return True
        else:  # gemini
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            return bool(api_key)
    except ImportError:
        return False

def get_llm_mode() -> str:
    """Get the current LLM mode"""
    return os.getenv('LLM_MODE', 'ollama').lower()

def reset_llm():
    """Reset the LLM instance (useful for testing or switching modes)"""
    global _llm_instance, _llm_initialized
    _llm_instance = None
    _llm_initialized = False
    logger.info("🔄 LLM instance reset")
