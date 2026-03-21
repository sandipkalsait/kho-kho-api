"""
Custom logging handlers for UTF-8 support on Windows.
"""
import logging
import sys
import io


class UTF8StreamHandler(logging.StreamHandler):
    """StreamHandler that outputs UTF-8 encoded text, handling emoji and special characters."""
    
    def __init__(self, stream=None):
        """Initialize with UTF-8 stream wrapper."""
        if stream is None:
            stream = sys.stderr
        
        # Wrap the stream with UTF-8 encoding if needed
        if hasattr(stream, 'encoding') and stream.encoding and stream.encoding.lower() != 'utf-8':
            # On Windows, replace cp1252 with UTF-8 wrapper
            if hasattr(stream, 'buffer'):
                # Standard streams have a buffer attribute
                stream = io.TextIOWrapper(stream.buffer, encoding='utf-8', errors='replace')
        
        super().__init__(stream)
    
    def emit(self, record):
        """Emit a record with UTF-8 safe handling."""
        try:
            msg = self.format(record)
            stream = self.stream
            
            # Ensure we're writing UTF-8 compatible text
            if isinstance(msg, bytes):
                stream.write(msg.decode('utf-8', errors='replace'))
            else:
                # Handle encoding errors gracefully
                try:
                    stream.write(msg)
                except UnicodeEncodeError:
                    # Fallback: encode to UTF-8 and write bytes if needed
                    stream.write(msg.encode('utf-8', errors='replace').decode('utf-8'))
            
            stream.write(self.terminator)
        except Exception:
            self.handleError(record)
