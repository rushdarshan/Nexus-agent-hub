import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class VibeCrystal:
    """
    VibeCrystal: The AI-to-Code Compiler.
    
    Transforms fuzzy AI execution history into crystallized, deterministic Playwright code.
    "Don't generate code. Generate experiences, then crystallize them."
    """
    
    def __init__(self, history_file: str):
        self.history_path = Path(history_file)
        self.output_code = []
        self.imports = set([
            "from playwright.sync_api import sync_playwright",
            "import time"
        ])

    def load_history(self) -> List[Dict]:
        """Load the massive JSON blob that is the Agent's memory."""
        if not self.history_path.exists():
            raise FileNotFoundError(f"Crystal not found at {self.history_path}")
            
        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Support both raw list and AgentHistoryList dict wrapper
            return data.get('history', data) if isinstance(data, dict) else data

    def compile(self, output_path: str = "crystallized_agent.py"):
        """Compiles the history into a pure Python script."""
        try:
            history = self.load_history()
        except Exception as e:
            print(f"Failed to load history: {e}")
            return

        print(f"🔮 Crystallizing {len(history)} steps...")
        
        self.output_code.append("def run_crystallized_task():")
        self.output_code.append("    with sync_playwright() as p:")
        self.output_code.append("        browser = p.chromium.launch(headless=False)")
        self.output_code.append("        context = browser.new_context()")
        self.output_code.append("        page = context.new_page()")
        self.output_code.append("")
        
        for step_idx, step in enumerate(history):
            self._transmute_step(step, step_idx)
            
        self.output_code.append("        print('✨ Task completed successfully.')")
        self.output_code.append("        browser.close()")

        # Final assembly
        full_script = "\n".join(sorted(list(self.imports))) + "\n\n"
        full_script += "\n".join(self.output_code)
        full_script += "\n\nif __name__ == '__main__':\n    run_crystallized_task()\n"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_script)
            
        print(f"💎 Code instantiated at: {output_path}")

    def _transmute_step(self, step: Dict, idx: int):
        """Converting a fuzzy Agent step into concrete Playwright instruction."""
        model_output = step.get('model_output', {})
        if not model_output:
            return

        actions = model_output.get('action', [])
        
        self.output_code.append(f"        # Step {idx+1}")
        
        for action in actions:
            # Handle different action types
            for action_name, params in action.items():
                if action_name == 'navigate':
                    url = params.get('url')
                    self.output_code.append(f"        page.goto('{url}')")
                    self.output_code.append(f"        page.wait_for_load_state('networkidle')")
                    
                elif action_name == 'click_element':
                    # This is the tricky part - mapping index back to selector
                    # In a real implementation we would look up the selector from the state
                    # For VibeCrystal v1, we assume the history has enriched data or valid selectors
                    # Falling back to generic selector logic for demo purposes if not present
                    index = params.get('index')
                    
                    # If we had the DOMInteractedElement here we would use its xpath
                    # Since we are reading raw history, we check if specific metadata was saved
                    # PRO TIP: The "Great" version uses the detailed DOMInteractedElement data
                    
                    self.output_code.append(f"        # Action: Click element {index}")
                    # Placeholder for the complex selector logic I found in browser_use
                    # self.output_code.append(f"        page.locator('xpath_selector_for_{index}').click()")
                    self.output_code.append(f"        print('Clicking element index {index} (Selector needs mapping)')")
                    
                elif action_name == 'input_text':
                    index = params.get('index')
                    text = params.get('text')
                    self.output_code.append(f"        # Action: Type '{text}' into {index}")
                    self.output_code.append(f"        print('Typing \"{text}\"')")
                    
                elif action_name == 'scroll':
                    amount = params.get('amount', '500')
                    self.output_code.append(f"        page.mouse.wheel(0, {amount}) if isinstance('{amount}', int) else page.evaluate('window.scrollTo(0, document.body.scrollHeight)')")
                    self.output_code.append(f"        time.sleep(1)")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python vibe_crystal.py <path_to_history.json>")
    else:
        vc = VibeCrystal(sys.argv[1])
        vc.compile()
