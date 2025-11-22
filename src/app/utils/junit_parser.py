"""Parser for JUnit XML test reports."""
from typing import List, Optional
from dataclasses import dataclass
from defusedxml import ElementTree as ET


@dataclass
class TestResultModel:
    """Normalized test result model."""
    name: str
    classname: Optional[str] = None
    status: str = "passed"  # passed, failed, skipped, error
    duration: Optional[float] = None
    failure_message: Optional[str] = None
    failure_type: Optional[str] = None
    system_out: Optional[str] = None
    system_err: Optional[str] = None


def parse_junit(xml_bytes: bytes) -> List[TestResultModel]:
    """
    Parse JUnit XML test results.
    
    Args:
        xml_bytes: JUnit XML content as bytes
    
    Returns:
        List of TestResultModel objects
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ValueError(f"Invalid JUnit XML: {e}")
    
    results = []
    
    # Handle both <testsuites> and <testsuite> root elements
    if root.tag == 'testsuites':
        testsuites = root.findall('testsuite') or [root]
    elif root.tag == 'testsuite':
        testsuites = [root]
    else:
        # Try to find testsuite elements
        testsuites = root.findall('.//testsuite') or [root]
    
    for testsuite in testsuites:
        # Get classname from testsuite if not in testcase
        suite_name = testsuite.get('name', '')
        
        for testcase in testsuite.findall('.//testcase'):
            name = testcase.get('name', '')
            classname = testcase.get('classname') or suite_name
            duration = testcase.get('time')
            
            # Determine status
            status = "passed"
            failure_message = None
            failure_type = None
            
            # Check for failure
            failure = testcase.find('failure')
            if failure is not None:
                status = "failed"
                failure_message = failure.text
                failure_type = failure.get('type')
            else:
                # Check for error
                error = testcase.find('error')
                if error is not None:
                    status = "error"
                    failure_message = error.text
                    failure_type = error.get('type')
                else:
                    # Check for skipped
                    skipped = testcase.find('skipped')
                    if skipped is not None:
                        status = "skipped"
            
            # Get system-out and system-err
            system_out_elem = testcase.find('system-out')
            system_out = system_out_elem.text if system_out_elem is not None else None
            
            system_err_elem = testcase.find('system-err')
            system_err = system_err_elem.text if system_err_elem is not None else None
            
            results.append(TestResultModel(
                name=name,
                classname=classname,
                status=status,
                duration=float(duration) if duration else None,
                failure_message=failure_message,
                failure_type=failure_type,
                system_out=system_out,
                system_err=system_err
            ))
    
    return results

