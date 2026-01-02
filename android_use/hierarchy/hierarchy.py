"""
Android View Hierarchy - DOM-like parsing for Android UI
Mirrors browser-use's DOM extraction and element indexing
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import re
import logging
import json

logger = logging.getLogger('android_use.hierarchy')


@dataclass
class AndroidElement:
    """Represents a single UI element in the Android view hierarchy"""
    id: int
    text: str
    content_desc: str
    resource_id: str
    class_name: str
    package: str
    bounds: Tuple[int, int, int, int]  # x1, y1, x2, y2
    center: Tuple[int, int]
    clickable: bool
    focusable: bool
    scrollable: bool
    enabled: bool
    selected: bool
    checkable: bool
    checked: bool
    editable: bool
    depth: int
    children_count: int
    
    @property
    def display_text(self) -> str:
        """Get the best text representation"""
        return self.text or self.content_desc or self.resource_id.split('/')[-1] or self.class_name.split('.')[-1]
    
    @property
    def is_interactive(self) -> bool:
        """Check if element is interactive"""
        return self.clickable or self.focusable or self.editable or self.checkable
    
    @property
    def width(self) -> int:
        return self.bounds[2] - self.bounds[0]
    
    @property
    def height(self) -> int:
        return self.bounds[3] - self.bounds[1]
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'text': self.display_text,
            'class': self.class_name.split('.')[-1],
            'center': {'x': self.center[0], 'y': self.center[1]},
            'bounds': {'x1': self.bounds[0], 'y1': self.bounds[1], 'x2': self.bounds[2], 'y2': self.bounds[3]},
            'interactive': self.is_interactive,
            'clickable': self.clickable,
            'editable': self.editable
        }


class ViewHierarchy:
    """
    Parses and simplifies Android XML hierarchy for LLM consumption.
    Provides DOM-like access to UI elements with indexing.
    """
    
    def __init__(self, xml_string: str = None):
        self.xml_string = xml_string
        self.root: Optional[ET.Element] = None
        self.elements: List[AndroidElement] = []
        self._element_map: Dict[int, AndroidElement] = {}
        
        if xml_string:
            self.parse(xml_string)
    
    def parse(self, xml_string: str) -> 'ViewHierarchy':
        """Parse XML hierarchy string"""
        try:
            self.xml_string = xml_string
            self.root = ET.fromstring(xml_string)
            self.elements = []
            self._element_map = {}
            self._traverse(self.root, depth=0)
            logger.debug(f"Parsed {len(self.elements)} elements")
        except ET.ParseError as e:
            logger.error(f"Failed to parse hierarchy XML: {e}")
        return self
    
    def _parse_bounds(self, bounds_str: str) -> Tuple[int, int, int, int]:
        """Convert '[x1,y1][x2,y2]' to tuple"""
        match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
        if match:
            return tuple(map(int, match.groups()))
        return (0, 0, 0, 0)
    
    def _calculate_center(self, bounds: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """Calculate center point from bounds"""
        x1, y1, x2, y2 = bounds
        return ((x1 + x2) // 2, (y1 + y2) // 2)
    
    def _traverse(self, node: ET.Element, depth: int):
        """Recursively traverse and extract elements"""
        # Extract attributes
        text = node.get('text', '').strip()
        content_desc = node.get('content-desc', '').strip()
        resource_id = node.get('resource-id', '')
        class_name = node.get('class', 'unknown')
        package = node.get('package', '')
        bounds_str = node.get('bounds', '[0,0][0,0]')
        
        clickable = node.get('clickable') == 'true'
        focusable = node.get('focusable') == 'true'
        scrollable = node.get('scrollable') == 'true'
        enabled = node.get('enabled', 'true') == 'true'
        selected = node.get('selected') == 'true'
        checkable = node.get('checkable') == 'true'
        checked = node.get('checked') == 'true'
        
        # Check if editable (EditText or similar)
        editable = 'EditText' in class_name or 'TextInput' in class_name
        
        bounds = self._parse_bounds(bounds_str)
        center = self._calculate_center(bounds)
        
        # Only add meaningful elements
        is_meaningful = (
            text or 
            content_desc or 
            clickable or 
            editable or 
            scrollable or
            (resource_id and enabled)
        )
        
        # Skip tiny elements (probably not visible/useful)
        area = (bounds[2] - bounds[0]) * (bounds[3] - bounds[1])
        is_visible = area > 100  # Minimum area threshold
        
        if is_meaningful and is_visible:
            element = AndroidElement(
                id=len(self.elements),
                text=text,
                content_desc=content_desc,
                resource_id=resource_id,
                class_name=class_name,
                package=package,
                bounds=bounds,
                center=center,
                clickable=clickable,
                focusable=focusable,
                scrollable=scrollable,
                enabled=enabled,
                selected=selected,
                checkable=checkable,
                checked=checked,
                editable=editable,
                depth=depth,
                children_count=len(node)
            )
            self.elements.append(element)
            self._element_map[element.id] = element
        
        # Recurse into children
        for child in node:
            self._traverse(child, depth + 1)
    
    # ========== Query Methods ==========
    
    def get_element(self, element_id: int) -> Optional[AndroidElement]:
        """Get element by ID"""
        return self._element_map.get(element_id)
    
    def get_clickable_elements(self) -> List[AndroidElement]:
        """Get all clickable elements"""
        return [e for e in self.elements if e.clickable]
    
    def get_interactive_elements(self) -> List[AndroidElement]:
        """Get all interactive elements"""
        return [e for e in self.elements if e.is_interactive]
    
    def get_editable_elements(self) -> List[AndroidElement]:
        """Get all text input fields"""
        return [e for e in self.elements if e.editable]
    
    def get_scrollable_elements(self) -> List[AndroidElement]:
        """Get all scrollable containers"""
        return [e for e in self.elements if e.scrollable]
    
    def find_by_text(self, text: str, exact: bool = False) -> List[AndroidElement]:
        """Find elements by text content"""
        text_lower = text.lower()
        results = []
        for e in self.elements:
            if exact:
                if e.text == text or e.content_desc == text:
                    results.append(e)
            else:
                if text_lower in e.text.lower() or text_lower in e.content_desc.lower():
                    results.append(e)
        return results
    
    def find_by_resource_id(self, resource_id: str) -> Optional[AndroidElement]:
        """Find element by resource ID (partial match supported)"""
        for e in self.elements:
            if resource_id in e.resource_id:
                return e
        return None
    
    def find_by_class(self, class_name: str) -> List[AndroidElement]:
        """Find elements by class name"""
        return [e for e in self.elements if class_name in e.class_name]
    
    def find_at_point(self, x: int, y: int) -> List[AndroidElement]:
        """Find all elements containing a point (front-to-back order)"""
        results = []
        for e in self.elements:
            x1, y1, x2, y2 = e.bounds
            if x1 <= x <= x2 and y1 <= y <= y2:
                results.append(e)
        # Sort by depth (deepest = most specific)
        results.sort(key=lambda e: e.depth, reverse=True)
        return results
    
    # ========== Export Methods ==========
    
    def to_summary_string(self, max_elements: int = 50) -> str:
        """
        Returns a compact string summary of actionable elements for LLM.
        Optimized for context window efficiency.
        """
        interactive = self.get_interactive_elements()[:max_elements]
        
        lines = [f"Found {len(interactive)} interactive elements:"]
        lines.append("ID | Text | Type | Center(x,y) | Actions")
        lines.append("-" * 60)
        
        for e in interactive:
            actions = []
            if e.clickable:
                actions.append("tap")
            if e.editable:
                actions.append("type")
            if e.scrollable:
                actions.append("scroll")
            if e.checkable:
                actions.append("check")
            
            action_str = ",".join(actions) if actions else "view"
            text = e.display_text[:30] + "..." if len(e.display_text) > 30 else e.display_text
            type_short = e.class_name.split('.')[-1][:15]
            
            lines.append(f"{e.id:3} | {text:30} | {type_short:15} | ({e.center[0]},{e.center[1]}) | {action_str}")
        
        return "\n".join(lines)
    
    def to_indexed_prompt(self, max_elements: int = 40) -> str:
        """
        Returns a numbered list format ideal for LLM action selection.
        """
        interactive = self.get_interactive_elements()[:max_elements]
        
        lines = ["Clickable Elements (use element ID for actions):"]
        
        for e in interactive:
            text = e.display_text
            if not text or text == e.class_name.split('.')[-1]:
                text = f"[{e.class_name.split('.')[-1]}]"
            
            props = []
            if e.editable:
                props.append("INPUT")
            if e.checkable:
                props.append(f"{'☑' if e.checked else '☐'}")
            if e.scrollable:
                props.append("SCROLL")
            
            prop_str = f" ({', '.join(props)})" if props else ""
            lines.append(f"  [{e.id}] {text}{prop_str} @ ({e.center[0]}, {e.center[1]})")
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """Export elements as JSON"""
        return json.dumps([e.to_dict() for e in self.elements], indent=2)
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Export elements as list of dicts"""
        return [e.to_dict() for e in self.elements]
    
    # ========== Analysis Methods ==========
    
    def get_screen_regions(self) -> Dict[str, List[AndroidElement]]:
        """
        Categorize elements by screen region (top, middle, bottom).
        Useful for navigation hints.
        """
        if not self.elements:
            return {'top': [], 'middle': [], 'bottom': []}
        
        # Estimate screen height from elements
        max_y = max(e.bounds[3] for e in self.elements) if self.elements else 2400
        
        regions = {'top': [], 'middle': [], 'bottom': []}
        
        for e in self.elements:
            center_y = e.center[1]
            if center_y < max_y * 0.33:
                regions['top'].append(e)
            elif center_y < max_y * 0.66:
                regions['middle'].append(e)
            else:
                regions['bottom'].append(e)
        
        return regions
    
    def detect_screen_type(self) -> str:
        """
        Try to detect the type of screen (login, home, settings, etc.)
        based on element patterns.
        """
        text_content = " ".join([e.text.lower() + " " + e.content_desc.lower() for e in self.elements])
        
        if any(word in text_content for word in ['login', 'sign in', 'password', 'username', 'email']):
            return 'login'
        elif any(word in text_content for word in ['sign up', 'register', 'create account']):
            return 'registration'
        elif any(word in text_content for word in ['settings', 'preferences', 'options']):
            return 'settings'
        elif any(word in text_content for word in ['search', 'find']):
            return 'search'
        elif any(word in text_content for word in ['cart', 'checkout', 'payment']):
            return 'shopping'
        elif any(word in text_content for word in ['profile', 'account', 'my']):
            return 'profile'
        elif any(word in text_content for word in ['home', 'feed', 'timeline']):
            return 'home'
        else:
            return 'unknown'
    
    def __len__(self) -> int:
        return len(self.elements)
    
    def __iter__(self):
        return iter(self.elements)
    
    def __repr__(self) -> str:
        return f"ViewHierarchy(elements={len(self.elements)})"
