"""
Browser Tool - Automated web browsing
"""
import asyncio
import base64
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

class BrowserTool:
    """Browser automation tool using Playwright"""
    
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = workspace_dir or "/tmp/nexusos-browser"
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def _get_playwright(self):
        """Lazy load Playwright"""
        if self.playwright is None:
            try:
                from playwright.async_api import async_playwright
                self.playwright = await async_playwright().start()
            except ImportError:
                return None
        return self.playwright
    
    async def _ensure_browser(self, headless: bool = True):
        """Ensure browser is initialized"""
        pw = await self._get_playwright()
        if not pw:
            return False, "Playwright not installed: pip install playwright && playwright install chromium"
        
        if self.browser is None:
            self.browser = await pw.chromium.launch(headless=headless)
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            self.page = await self.context.new_page()
        return True, None
    
    async def open(self, url: str, headless: bool = True) -> Dict:
        """Open a URL in browser"""
        success, error = await self._ensure_browser(headless)
        if not success:
            return {"success": False, "error": error}
        
        try:
            response = await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = await self.page.title()
            return {
                "success": True,
                "url": self.page.url,
                "title": title,
                "status": response.status if response else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def click(self, selector: str, timeout: int = 5000) -> Dict:
        """Click element by CSS selector"""
        if not self.page:
            return {"success": False, "error": "No open page. Call open() first."}
        
        try:
            await self.page.click(selector, timeout=timeout)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def type(self, selector: str, text: str, clear: bool = True, timeout: int = 5000) -> Dict:
        """Type text into element"""
        if not self.page:
            return {"success": False, "error": "No open page. Call open() first."}
        
        try:
            if clear:
                await self.page.fill(selector, "", timeout=timeout)
            await self.page.fill(selector, text, timeout=timeout)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def press(self, selector: str, key: str, timeout: int = 5000) -> Dict:
        """Press key on element"""
        if not self.page:
            return {"success": False, "error": "No open page. Call open() first."}
        
        try:
            await self.page.press(selector, key, timeout=timeout)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def navigate(self, url: str) -> Dict:
        """Navigate to URL (alias for open)"""
        return await self.open(url)
    
    async def screenshot(self, path: str = None, full_page: bool = False) -> Dict:
        """Take screenshot"""
        if not self.page:
            return {"success": False, "error": "No open page. Call open() first."}
        
        try:
            if path:
                await self.page.screenshot(path=path, full_page=full_page)
                return {"success": True, "path": path}
            else:
                # Return base64
                img = await self.page.screenshot(full_page=full_page)
                b64 = base64.b64encode(img).decode()
                return {"success": True, "type": "base64", "data": b64}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_text(self, selector: str) -> Dict:
        """Get text content of element"""
        if not self.page:
            return {"success": False, "error": "No open page."}
        
        try:
            text = await self.page.text_content(selector)
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_html(self, selector: str = None) -> Dict:
        """Get HTML content"""
        if not self.page:
            return {"success": False, "error": "No open page."}
        
        try:
            if selector:
                html = await self.page.inner_html(selector)
            else:
                html = await self.page.content()
            return {"success": True, "html": html}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def evaluate(self, js: str) -> Dict:
        """Execute JavaScript"""
        if not self.page:
            return {"success": False, "error": "No open page."}
        
        try:
            result = await self.page.evaluate(js)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def wait_for(self, selector: str, timeout: int = 10000) -> Dict:
        """Wait for selector"""
        if not self.page:
            return {"success": False, "error": "No open page."}
        
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close(self) -> Dict:
        """Close browser"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_cookies(self) -> Dict:
        """Get all cookies"""
        if not self.page:
            return {"success": False, "error": "No open page."}
        
        try:
            cookies = await self.context.cookies()
            return {"success": True, "cookies": cookies}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def set_cookies(self, cookies: List[Dict]) -> Dict:
        """Set cookies"""
        if not self.page:
            return {"success": False, "error": "No open page."}
        
        try:
            await self.context.add_cookies(cookies)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
_browser_tool = None

def get_browser_tool(workspace_dir: str = None) -> BrowserTool:
    global _browser_tool
    if _browser_tool is None:
        _browser_tool = BrowserTool(workspace_dir)
    return _browser_tool