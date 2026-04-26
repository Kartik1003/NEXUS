import subprocess
import logging
import urllib.request
import json
import tempfile
import os

logger = logging.getLogger(__name__)

class ToolSystem:
    @staticmethod
    def execute_python(code: str) -> str:
        """Executes python code safely (with basic timeout) and returns stdout."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name
                
            res = subprocess.run(["python", temp_path], capture_output=True, text=True, timeout=10)
            os.remove(temp_path)
            
            output = res.stdout
            if res.stderr:
                output += "\nErrors:\n" + res.stderr
            return output[:2000] # Cap output size
        except subprocess.TimeoutExpired:
            return "Error: Execution timed out."
        except Exception as e:
            return f"Error executing code: {e}"

    @staticmethod
    def web_search(query: str) -> str:
        """Generates a mock web search or uses a public API if available."""
        # For a truly autonomous system without API keys, we can hit DuckDuckGo HTML or similar, 
        # but a simple simulation or wikipedia lookup works for core mechanics.
        try:
            import urllib.parse
            url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit=3&namespace=0&format=json"
            req = urllib.request.Request(url, headers={'User-Agent': 'AgentForge/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                if len(data) > 2 and data[2]:
                    return "\n".join(data[2])
                return "No search results found."
        except Exception as e:
            return f"Search failed: {e}"

    @staticmethod
    def process_tools(text: str) -> (bool, str):
        """Looks for <SEARCH>query</SEARCH> or <EXECUTE>code</EXECUTE>"""
        import re
        modified = False
        result_text = text
        
        search_matches = re.finditer(r"<SEARCH>(.*?)</SEARCH>", text, re.DOTALL)
        for match in search_matches:
            modified = True
            query = match.group(1).strip()
            res = ToolSystem.web_search(query)
            result_text += f"\n\n[System: Search Result for '{query}']\n{res}\n"
            
        exec_matches = re.finditer(r"<EXECUTE>(.*?)</EXECUTE>", text, re.DOTALL)
        for match in exec_matches:
            modified = True
            code = match.group(1).strip()
            # Strip markdown if present inside <EXECUTE>
            if code.startswith("```python"): code = code[9:]
            elif code.startswith("```"): code = code[3:]
            if code.endswith("```"): code = code[:-3]
                
            res = ToolSystem.execute_python(code.strip())
            result_text += f"\n\n[System: Python Execution Result]\n{res}\n"
            
        return modified, result_text
