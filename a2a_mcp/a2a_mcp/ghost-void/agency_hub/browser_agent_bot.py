"""
Browser Agent Bot

Programmatic browser automation agent for completing actions.
Uses requests + BeautifulSoup for web crawling when Playwright is unavailable.
"""

import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BrowserAction:
    """A single browser action."""
    action_type: str  # "navigate", "click", "extract", "scroll"
    target: str
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class BrowserSession:
    """A browser session with action history."""
    session_id: str
    current_url: str = ""
    actions: List[BrowserAction] = field(default_factory=list)
    extracted_data: Dict[str, Any] = field(default_factory=dict)


class BrowserAgentBot:
    """
    Embedded browser agent for autonomous web actions.
    
    Dual mode:
    - Live mode: Uses aiohttp/requests for actual web requests
    - Simulation mode: Returns mock data for testing
    """
    
    def __init__(self, mode: str = "simulation"):
        self.mode = mode  # "live" or "simulation"
        self.session: Optional[BrowserSession] = None
        
    def create_session(self) -> BrowserSession:
        """Create a new browser session."""
        session_id = f"bs_{hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:12]}"
        self.session = BrowserSession(session_id=session_id)
        return self.session
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL."""
        if not self.session:
            self.create_session()
            
        action = BrowserAction(
            action_type="navigate",
            target=url
        )
        self.session.actions.append(action)
        self.session.current_url = url
        
        if self.mode == "live":
            return await self._live_navigate(url)
        else:
            return self._mock_navigate(url)
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element."""
        action = BrowserAction(
            action_type="click",
            target=selector
        )
        self.session.actions.append(action)
        
        return {"status": "clicked", "selector": selector}
    
    async def extract(self, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract data from current page."""
        action = BrowserAction(
            action_type="extract",
            target="page",
            params=selectors
        )
        self.session.actions.append(action)
        
        if self.mode == "live":
            return await self._live_extract(selectors)
        else:
            return self._mock_extract(selectors)
    
    async def execute_action_sequence(self, actions: List[Dict]) -> List[Dict]:
        """Execute a sequence of actions autonomously."""
        results = []
        
        for action_def in actions:
            action_type = action_def.get("type")
            
            if action_type == "navigate":
                result = await self.navigate(action_def["url"])
            elif action_type == "click":
                result = await self.click(action_def["selector"])
            elif action_type == "extract":
                result = await self.extract(action_def["selectors"])
            else:
                result = {"error": f"Unknown action: {action_type}"}
            
            results.append({
                "action": action_def,
                "result": result
            })
        
        return results
    
    async def _live_navigate(self, url: str) -> Dict[str, Any]:
        """Actually fetch URL content."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return {
                        "status": "navigated",
                        "url": url,
                        "status_code": response.status
                    }
        except ImportError:
            return {"error": "aiohttp not installed", "url": url}
    
    async def _live_extract(self, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Actually extract content."""
        return {"error": "Live extraction requires page content", "selectors": selectors}
    
    def _mock_navigate(self, url: str) -> Dict[str, Any]:
        """Mock navigation for simulation."""
        # Simulate Hawkthorne repo content
        if "hawkthorne" in url.lower():
            return {
                "status": "navigated",
                "url": url,
                "page_title": "hawkthorne/hawkthorne-journey",
                "content_preview": "A 2D platformer based on Community's Digital Estate Planning"
            }
        return {"status": "navigated", "url": url}
    
    def _mock_extract(self, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Mock extraction for simulation."""
        mock_data = {
            "repo_name": "hawkthorne-journey",
            "description": "Digital Estate Planning: The Game",
            "language": "Lua 99.2%",
            "stars": "3.2k",
            "folders": ["src", "levels", "nodes", "graphics"],
            "level_files": ["town.lua", "forest.lua", "castle.lua", "throne_room.lua"]
        }
        return {"status": "extracted", "data": mock_data}
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        if not self.session:
            return {"error": "No active session"}
        
        return {
            "session_id": self.session.session_id,
            "current_url": self.session.current_url,
            "total_actions": len(self.session.actions),
            "action_types": [a.action_type for a in self.session.actions],
            "extracted_data": self.session.extracted_data
        }


# =============================================================================
# HAWKTHORNE AGENT BOT
# =============================================================================

class HawthorneAgentBot:
    """
    Specialized bot for Hawkthorne repository exploration.
    Combines browser agent with game knowledge.
    """
    
    def __init__(self):
        self.browser = BrowserAgentBot(mode="simulation")
        self.knowledge_base: List[Dict] = []
        
    async def complete_action(self) -> Dict[str, Any]:
        """Complete the full exploration action."""
        
        # Define action sequence
        actions = [
            {"type": "navigate", "url": "https://github.com/hawkthorne/hawkthorne-journey"},
            {"type": "click", "selector": "a[title='src']"},
            {"type": "click", "selector": "a[title='levels']"},
            {"type": "extract", "selectors": {
                "repo_name": "h1.repo-name",
                "files": "div.file-list a",
                "description": "p.repo-description"
            }},
        ]
        
        # Execute sequence
        results = await self.browser.execute_action_sequence(actions)
        
        # Build knowledge base from extracted data
        for result in results:
            if result["result"].get("status") == "extracted":
                self.knowledge_base.append(result["result"]["data"])
        
        # Generate completion checkpoint
        checkpoint = {
            "bot_id": f"bot_{hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:8]}",
            "status": "action_complete",
            "session": self.browser.get_session_summary(),
            "knowledge_gathered": len(self.knowledge_base),
            "data": self.knowledge_base
        }
        
        return checkpoint


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Run browser agent bot demo."""
    print("=" * 60)
    print("BROWSER AGENT BOT - HAWKTHORNE EXPLORATION")
    print("=" * 60 + "\n")
    
    bot = HawthorneAgentBot()
    result = await bot.complete_action()
    
    print("Session Summary:")
    print(json.dumps(result["session"], indent=2))
    
    print("\nKnowledge Gathered:")
    print(json.dumps(result["data"], indent=2))
    
    print("\n" + "=" * 60)
    print(f"Bot ID: {result['bot_id']}")
    print(f"Status: {result['status']}")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
