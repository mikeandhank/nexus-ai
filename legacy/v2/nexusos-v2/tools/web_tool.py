"""
Web Search Tool - Search the web
"""
import requests
from typing import Dict, List, Optional

class WebSearchTool:
    """Web search using Perplexity/OpenRouter API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://api.openrouter.ai/api/v1"
    
    def search(self, query: str, count: int = 5, freshness: str = None) -> Dict:
        """Search the web using Perplexity Sonar"""
        if not self.api_key:
            # Fallback to DuckDuckGo HTML scrape
            return self._search_duckduckgo(query, count)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "perplexity/sonar-small-online",
            "messages": [
                {"role": "user", "content": query}
            ],
            "max_tokens": 1000
        }
        
        if freshness:
            data["freq_penalty"] = 0.5  # Approximate freshness
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "answer": result["choices"][0]["message"]["content"],
                "model": result.get("model"),
                "citations": []  # Perplexity doesn't always provide
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _search_duckduckgo(self, query: str, count: int = 5) -> Dict:
        """Fallback: DuckDuckGo Lite"""
        try:
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query, "b": count}
            
            response = requests.post(url, data=data, timeout=15)
            response.raise_for_status()
            
            # Parse results
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            results = []
            for result in soup.select(".result"):
                title_elem = result.select_one(".result__title")
                link_elem = result.select_one(".result__url")
                snippet_elem = result.select_one(".result__snippet")
                
                if title_elem and link_elem:
                    results.append({
                        "title": title_elem.get_text(strip=True),
                        "url": link_elem.get_text(strip=True),
                        "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                    })
            
            return {
                "success": True,
                "results": results[:count],
                "source": "duckduckgo"
            }
        except ImportError:
            return {"success": False, "error": "bs4 not installed and no API key"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class WebFetchTool:
    """Fetch and extract content from URLs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def fetch(self, url: str, max_chars: int = 50000) -> Dict:
        """Fetch URL and extract readable content"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            
            if "text/html" in content_type:
                return self._extract_html(response.text, max_chars)
            elif "text/plain" in content_type:
                return {
                    "success": True,
                    "content": response.text[:max_chars],
                    "type": "text",
                    "url": url
                }
            else:
                return {
                    "success": True,
                    "content": f"[Binary content: {content_type}]",
                    "type": "binary",
                    "url": url
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _extract_html(self, html: str, max_chars: int) -> Dict:
        """Extract readable text from HTML"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove scripts, styles, nav, footer
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            
            # Get title
            title = soup.title.string if soup.title else ""
            
            # Get main content
            main = soup.find("main") or soup.find("article") or soup.body
            
            text = main.get_text(separator="\n", strip=True) if main else ""
            
            # Clean up whitespace
            lines = [line.strip() for line in text.split("\n")]
            text = "\n".join(line for line in lines if line)
            
            return {
                "success": True,
                "content": text[:max_chars],
                "type": "html",
                "title": title,
                "url": ""
            }
        except ImportError:
            # Fallback: just strip tags
            import re
            text = re.sub(r"<[^>]+>", "", html)
            return {
                "success": True,
                "content": text[:max_chars],
                "type": "html",
                "url": ""
            }
    
    def fetch_json(self, url: str) -> Dict:
        """Fetch JSON from URL"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instances
_search_tool = None
_fetch_tool = None

def get_search_tool(api_key: str = None) -> WebSearchTool:
    global _search_tool
    if _search_tool is None:
        _search_tool = WebSearchTool(api_key)
    return _search_tool

def get_fetch_tool() -> WebFetchTool:
    global _fetch_tool
    if _fetch_tool is None:
        _fetch_tool = WebFetchTool()
    return _fetch_tool