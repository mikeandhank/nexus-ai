"""
Cron Tool - Schedule and manage periodic tasks
"""
import os
import json
import time
import threading
from typing import Dict, List, Callable, Optional
from datetime import datetime, timedelta
from croniter import croniter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CronJob:
    """Represents a scheduled job"""
    
    def __init__(self, job_id: str, name: str, schedule: str, func: Callable, 
                 enabled: bool = True, max_runs: int = None):
        self.job_id = job_id
        self.name = name
        self.schedule = schedule  # cron expression
        self.func = func
        self.enabled = enabled
        self.max_runs = max_runs
        
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self.last_result = None
        
        # Calculate next run
        self._calc_next_run()
    
    def _calc_next_run(self):
        """Calculate next run time"""
        try:
            iter = croniter(self.schedule, datetime.now())
            self.next_run = iter.get_next(datetime)
        except:
            self.next_run = None
    
    def should_run(self) -> bool:
        """Check if job should run now"""
        if not self.enabled:
            return False
        if self.max_runs and self.run_count >= self.max_runs:
            return False
        if not self.next_run:
            return False
        return datetime.now() >= self.next_run
    
    def run(self) -> Dict:
        """Execute the job"""
        if not self.should_run():
            return {"success": False, "reason": "not scheduled to run"}
        
        try:
            start_time = time.time()
            result = self.func()
            duration = time.time() - start_time
            
            self.last_run = datetime.now()
            self.last_result = {"success": True, "result": result, "duration_ms": int(duration * 1000)}
            self.run_count += 1
            
            # Calculate next run
            self._calc_next_run()
            
            return self.last_result
        except Exception as e:
            self.last_run = datetime.now()
            self.last_result = {"success": False, "error": str(e)}
            self._calc_next_run()
            return self.last_result


class CronTool:
    """Cron-like job scheduler"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or "/opt/nexusos-data/cron"
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.jobs: Dict[str, CronJob] = {}
        self.running = False
        self.thread = None
        
        # Load persisted jobs
        self._load_jobs()
    
    def _load_jobs(self):
        """Load jobs from disk"""
        jobs_file = os.path.join(self.data_dir, "jobs.json")
        if os.path.exists(jobs_file):
            try:
                with open(jobs_file, "r") as f:
                    data = json.load(f)
                    # Note: functions can't be pickled, so we just load metadata
                    logger.info(f"Loaded {len(data)} job configs")
            except Exception as e:
                logger.warning(f"Failed to load jobs: {e}")
    
    def _save_jobs(self):
        """Save job configs to disk"""
        jobs_file = os.path.join(self.data_dir, "jobs.json")
        try:
            data = {
                job_id: {
                    "name": job.name,
                    "schedule": job.schedule,
                    "enabled": job.enabled,
                    "max_runs": job.max_runs,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "run_count": job.run_count
                }
                for job_id, job in self.jobs.items()
            }
            with open(jobs_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save jobs: {e}")
    
    def add(self, job_id: str, name: str, schedule: str, func: Callable,
            enabled: bool = True, max_runs: int = None) -> Dict:
        """Add a new job"""
        if job_id in self.jobs:
            return {"success": False, "error": f"Job {job_id} already exists"}
        
        job = CronJob(job_id, name, schedule, func, enabled, max_runs)
        self.jobs[job_id] = job
        self._save_jobs()
        
        return {"success": True, "job_id": job_id, "next_run": job.next_run.isoformat()}
    
    def remove(self, job_id: str) -> Dict:
        """Remove a job"""
        if job_id not in self.jobs:
            return {"success": False, "error": f"Job {job_id} not found"}
        
        del self.jobs[job_id]
        self._save_jobs()
        
        return {"success": True}
    
    def enable(self, job_id: str) -> Dict:
        """Enable a job"""
        if job_id not in self.jobs:
            return {"success": False, "error": f"Job {job_id} not found"}
        
        self.jobs[job_id].enabled = True
        self.jobs[job_id]._calc_next_run()
        self._save_jobs()
        
        return {"success": True, "next_run": self.jobs[job_id].next_run.isoformat()}
    
    def disable(self, job_id: str) -> Dict:
        """Disable a job"""
        if job_id not in self.jobs:
            return {"success": False, "error": f"Job {job_id} not found"}
        
        self.jobs[job_id].enabled = False
        self._save_jobs()
        
        return {"success": True}
    
    def list(self) -> Dict:
        """List all jobs"""
        jobs = []
        for job_id, job in self.jobs.items():
            jobs.append({
                "id": job_id,
                "name": job.name,
                "schedule": job.schedule,
                "enabled": job.enabled,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "run_count": job.run_count
            })
        return {"success": True, "jobs": jobs}
    
    def get(self, job_id: str) -> Dict:
        """Get job details"""
        if job_id not in self.jobs:
            return {"success": False, "error": f"Job {job_id} not found"}
        
        job = self.jobs[job_id]
        return {
            "success": True,
            "job": {
                "id": job_id,
                "name": job.name,
                "schedule": job.schedule,
                "enabled": job.enabled,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "run_count": job.run_count,
                "last_result": job.last_result
            }
        }
    
    def run_now(self, job_id: str) -> Dict:
        """Run job immediately"""
        if job_id not in self.jobs:
            return {"success": False, "error": f"Job {job_id} not found"}
        
        return self.jobs[job_id].run()
    
    def run_all_pending(self) -> Dict:
        """Run all pending jobs"""
        results = {}
        for job_id, job in self.jobs.items():
            if job.should_run():
                results[job_id] = job.run()
        
        self._save_jobs()
        return {"success": True, "results": results}
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Cron scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Cron scheduler stopped")
    
    def _run_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                # Run pending jobs
                for job_id, job in self.jobs.items():
                    if job.should_run():
                        logger.info(f"Running job: {job_id}")
                        job.run()
                
                self._save_jobs()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            time.sleep(10)  # Check every 10 seconds


# Singleton
_cron_tool = None

def get_cron_tool(data_dir: str = None) -> CronTool:
    global _cron_tool
    if _cron_tool is None:
        _cron_tool = CronTool(data_dir)
    return _cron_tool