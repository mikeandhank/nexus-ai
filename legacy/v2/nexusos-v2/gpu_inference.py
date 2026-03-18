"""
GPU Inference Module
===================
Support for GPU-accelerated inference with Ollama
"""
import os
import subprocess
from typing import Dict, List, Optional


class GPUManager:
    """
    Manage GPU inference with Ollama
    """
    
    def __init__(self):
        self.ollama_base = os.environ.get('OLLAMA_BASE_URL', 'http://nexusos-ollama:11434')
    
    def check_gpu_available(self) -> Dict:
        """Check if GPU is available"""
        try:
            import requests
            
            # Check Ollama GPU status
            resp = requests.get(f"{self.ollama_base}/api/tags", timeout=5)
            
            if resp.status_code == 200:
                models = resp.json().get('models', [])
                
                # Check for GPU-enabled models
                gpu_models = [m for m in models if m.get('size', 0) > 1_000_000_000]
                
                return {
                    "gpu_available": True,
                    "total_models": len(models),
                    "gpu_models": len(gpu_models),
                    "models": [m['name'] for m in models]
                }
            
            return {"gpu_available": False, "error": f"Status {resp.status_code}"}
            
        except ImportError:
            return {"gpu_available": False, "error": "requests library not available"}
        except Exception as e:
            return {"gpu_available": False, "error": str(e)}
    
    def get_gpu_info(self) -> Dict:
        """Get detailed GPU information"""
        try:
            import requests
            
            resp = requests.get(f"{self.ollama_base}/api/show", timeout=5)
            
            # Try different endpoints
            info_resp = requests.get(f"{self.ollama_base}/api/info", timeout=5)
            
            gpu_info = {
                "ollama_version": "unknown",
                "gpu_count": 0,
                "gpu_memory_total": 0,
                "gpu_memory_free": 0
            }
            
            if info_resp.status_code == 200:
                info = info_resp.json()
                gpu_info.update({
                    "gpu_count": info.get('gpuCount', 0),
                    "gpu_memory_total": info.get('memTotal', 0),
                })
            
            return gpu_info
            
        except Exception as e:
            return {"error": str(e)}
    
    def recommend_models(self) -> List[Dict]:
        """Recommend models based on available GPU"""
        gpu_info = self.get_gpu_info()
        
        recommendations = []
        
        # CPU-only recommendations
        cpu_models = [
            {"name": "phi3", "size": "2.3GB", "min_gpu": "0GB", "description": "Fast, efficient"},
            {"name": "mistral", "size": "4.1GB", "min_gpu": "4GB", "description": "Balanced performance"},
        ]
        
        # GPU recommendations
        if gpu_info.get('gpu_count', 0) > 0:
            vram = gpu_info.get('gpu_memory_total', 0) / (1024**3)
            
            if vram >= 8:
                recommendations.extend([
                    {"name": "llama3:8b", "size": "4.9GB", "vram": "8GB+", "description": "Best quality"},
                    {"name": "codellama", "size": "3.8GB", "vram": "8GB+", "description": "Code specialized"},
                ])
            elif vram >= 4:
                recommendations.extend([
                    {"name": "mistral", "size": "4.1GB", "vram": "4GB+", "description": "Balanced"},
                    {"name": "phi3", "size": "2.3GB", "vram": "4GB+", "description": "Fast"},
                ])
        
        recommendations.extend(cpu_models)
        
        return recommendations
    
    def benchmark(self, model: str = "phi3") -> Dict:
        """Benchmark model inference speed"""
        import time
        import requests
        
        prompt = "Write a short story about a robot."
        
        start = time.time()
        
        try:
            resp = requests.post(
                f"{self.ollama_base}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60
            )
            
            duration = time.time() - start
            
            if resp.status_code == 200:
                result = resp.json()
                tokens = result.get('eval_count', 0)
                
                return {
                    "model": model,
                    "success": True,
                    "duration_seconds": round(duration, 2),
                    "tokens_generated": tokens,
                    "tokens_per_second": round(tokens / duration, 2) if duration > 0 else 0
                }
            
            return {"model": model, "success": False, "error": f"Status {resp.status_code}"}
            
        except Exception as e:
            return {"model": model, "success": False, "error": str(e)}


# GPU-accelerated LLM wrapper
class GPULLM:
    """Use GPU for faster LLM inference"""
    
    def __init__(self, model: str = "phi3", use_gpu: bool = True):
        self.model = model
        self.use_gpu = use_gpu
    
    def generate(self, prompt: str, **kwargs) -> Dict:
        """Generate response with GPU acceleration"""
        import requests
        
        # Adjust parameters for GPU
        options = {
            "num_gpu": 1 if self.use_gpu else 0,
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
        }
        
        try:
            resp = requests.post(
                f"{os.environ.get('OLLAMA_BASE_URL', 'http://nexusos-ollama:11434')}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "options": options,
                    "stream": False
                },
                timeout=kwargs.get("timeout", 60)
            )
            
            if resp.status_code == 200:
                return {"success": True, "response": resp.json()}
            
            return {"success": False, "error": resp.text}
            
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_gpu_manager() -> GPUManager:
    return GPUManager()