"""Storage adapter for file operations (currently minimal)."""
import aiofiles
from typing import Optional
import os


class StorageAdapter:
    """Adapter for file storage operations."""
    
    def __init__(self, base_path: str = "/tmp/autoqa"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    async def save_file(self, filename: str, content: bytes) -> str:
        """
        Save file content.
        
        Args:
            filename: Name of the file
            content: File content as bytes
        
        Returns:
            Path to saved file
        """
        file_path = os.path.join(self.base_path, filename)
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        return file_path
    
    async def read_file(self, filename: str) -> Optional[bytes]:
        """
        Read file content.
        
        Args:
            filename: Name of the file
        
        Returns:
            File content as bytes, or None if file doesn't exist
        """
        file_path = os.path.join(self.base_path, filename)
        if not os.path.exists(file_path):
            return None
        
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()
    
    async def delete_file(self, filename: str) -> bool:
        """
        Delete a file.
        
        Args:
            filename: Name of the file
        
        Returns:
            True if deleted, False otherwise
        """
        file_path = os.path.join(self.base_path, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

