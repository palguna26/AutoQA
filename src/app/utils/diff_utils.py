"""Utilities for parsing Git diffs and extracting changed symbols."""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class SymbolChange:
    """Represents a changed symbol (function, class, etc.) in a diff."""
    name: str
    type: str  # 'function', 'class', 'method'
    file_path: str
    line_number: Optional[int] = None


def extract_changed_symbols(diff_text: str) -> List[SymbolChange]:
    """
    Extract changed symbols (functions, classes) from a unified diff.
    
    Args:
        diff_text: Unified diff text
    
    Returns:
        List of SymbolChange objects
    """
    symbols = []
    current_file = None
    current_hunk_start = None
    
    lines = diff_text.split('\n')
    
    for i, line in enumerate(lines):
        # Extract file path from diff header
        if line.startswith('+++'):
            match = re.match(r'\+\+\+\s+b/(.+)', line)
            if match:
                current_file = match.group(1)
                current_hunk_start = None
        
        # Track hunk start line numbers
        elif line.startswith('@@'):
            match = re.match(r'@@\s*-\d+,\d+\s*\+(\d+),\d+', line)
            if match:
                current_hunk_start = int(match.group(1))
        
        # Look for added/changed functions and classes
        elif line.startswith('+') and current_file:
            # Python functions and classes
            func_match = re.match(r'^\+\s*(?:async\s+)?def\s+(\w+)\s*\(', line)
            class_match = re.match(r'^\+\s*class\s+(\w+)', line)
            method_match = re.match(r'^\+\s+(?:async\s+)?def\s+(\w+)\s*\(', line)
            
            if func_match:
                line_num = current_hunk_start + i if current_hunk_start else None
                symbols.append(SymbolChange(
                    name=func_match.group(1),
                    type='function',
                    file_path=current_file,
                    line_number=line_num
                ))
            elif class_match:
                line_num = current_hunk_start + i if current_hunk_start else None
                symbols.append(SymbolChange(
                    name=class_match.group(1),
                    type='class',
                    file_path=current_file,
                    line_number=line_num
                ))
            
            # JavaScript/TypeScript functions
            js_func_match = re.match(r'^\+\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)', line)
            js_arrow_match = re.match(r'^\+\s*const\s+(\w+)\s*=\s*(?:async\s+)?\(', line)
            js_class_match = re.match(r'^\+\s*class\s+(\w+)', line)
            
            if js_func_match:
                line_num = current_hunk_start + i if current_hunk_start else None
                symbols.append(SymbolChange(
                    name=js_func_match.group(1),
                    type='function',
                    file_path=current_file,
                    line_number=line_num
                ))
            elif js_arrow_match:
                line_num = current_hunk_start + i if current_hunk_start else None
                symbols.append(SymbolChange(
                    name=js_arrow_match.group(1),
                    type='function',
                    file_path=current_file,
                    line_number=line_num
                ))
            elif js_class_match:
                line_num = current_hunk_start + i if current_hunk_start else None
                symbols.append(SymbolChange(
                    name=js_class_match.group(1),
                    type='class',
                    file_path=current_file,
                    line_number=line_num
                ))
    
    return symbols


def get_changed_file_types(file_list: List[Dict]) -> Dict[str, str]:
    """
    Determine file types from changed file list.
    
    Args:
        file_list: List of file metadata dicts with 'filename' key
    
    Returns:
        Dictionary mapping filename to file type
    """
    file_types = {}
    
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.cs': 'csharp',
    }
    
    for file_info in file_list:
        filename = file_info.get('filename', '')
        file_type = 'unknown'
        
        # Check file extension
        for ext, ftype in extension_map.items():
            if filename.endswith(ext):
                file_type = ftype
                break
        
        file_types[filename] = file_type
    
    return file_types

