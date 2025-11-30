import asyncio
from asyncio import TimeoutError
import sys
import signal
import psutil

def safe_decode(b):
    """Decode bytes to string with proper encoding."""
    if b is None:
        return ""
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp1252", errors="replace")

def kill_process_tree(pid):
    """Kill a process and all its children (Chrome, ChromeDriver, etc.)."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # Terminate children first
        for child in children:
            try:
                child.terminate()
            except:
                pass
        
        # Wait a bit
        gone, alive = psutil.wait_procs(children, timeout=3)
        
        # Force kill remaining processes
        for p in alive:
            try:
                p.kill()
            except:
                pass
        
        # Terminate parent
        try:
            parent.terminate()
            parent.wait(timeout=3)
        except:
            try:
                parent.kill()
            except:
                pass
    except:
        pass

async def run_cmd_with_timeout(name, cmd, max_duration):
    """
    Run a command and automatically stop it after max_duration seconds.
    Works like pressing Ctrl+C after the time is up.
    """
    print(f"\n[START] {name} (max {max_duration}s)")
    
    process = None
    
    try:
        # Start the process
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )
        
        print(f"  Process started (PID: {process.pid})")
        
        # Wait with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=max_duration
            )
            
            # Process finished before timeout
            if stdout:
                output = safe_decode(stdout)
                if output.strip():
                    print(f"\n[{name}] Output:")
                    print(output[:500])
            
            print(f"[DONE] {name}")
            return True
            
        except asyncio.TimeoutError:
            # Timeout reached - stop the process
            print(f"\n[TIMEOUT] {name} - stopping after {max_duration}s...")
            
            # Kill process tree (includes Chrome/ChromeDriver)
            kill_process_tree(process.pid)
            
            # Wait for cleanup
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except:
                pass
            
            # Get partial output
            try:
                stdout, stderr = process.communicate()
                if stdout:
                    output = safe_decode(stdout)
                    if output.strip():
                        print(f"\n[{name}] Last output:")
                        print(output[-500:])
            except:
                pass
            
            print(f"[STOPPED] {name} - data saved")
            return True
            
    except Exception as e:
        print(f"\n[ERROR] {name}: {str(e)}")
        if process:
            kill_process_tree(process.pid)
        return False

async def run_scrapers(scraper_duration=120):
    """Run all scrapers in parallel, each stops after scraper_duration seconds."""
    print("\n" + "="*80)
    print("STAGE 1: SCRAPING")
    print("="*80)
    print(f"\nEach scraper will run for max {scraper_duration} seconds\n")
    
    scrapers = [
        run_cmd_with_timeout(
            "Scraper Emplois Tunisie",
            "python src/scrapers/emploisTunisie.py",
            max_duration=scraper_duration
        ),
        run_cmd_with_timeout(
            "Scraper Kee Jobs",
            "python src/scrapers/keejobs.py",
            max_duration=scraper_duration
        ),
        run_cmd_with_timeout(
            "Scraper Option Carriere",
            "python src/scrapers/optioncarrier.py",
            max_duration=scraper_duration
        )
    ]

    print("Running scrapers in parallel...")
    results = await asyncio.gather(*scrapers, return_exceptions=True)
    
    success_count = sum(1 for r in results if r is True)
    print(f"\nScrapers finished: {success_count}/{len(scrapers)} completed")
    
    return success_count > 0

async def run_cleaners():
    """Run all cleaners in parallel."""
    print("\n" + "="*80)
    print("STAGE 2: CLEANING")
    print("="*80)
    
    cleaners = [
        run_cmd_with_timeout(
            "Cleaning Emplois Tunisie",
            "python src/cleaning/emploisTunisie_cleaning.py",
            max_duration=300
        ),
        run_cmd_with_timeout(
            "Cleaning Kee Jobs",
            "python src/cleaning/keejobs_cleaning.py",
            max_duration=300
        ),
        run_cmd_with_timeout(
            "Cleaning Option Carriere",
            "python src/cleaning/optioncarrier_cleaning.py",
            max_duration=300
        ),
    ]

    print("\nRunning cleaners in parallel...")
    results = await asyncio.gather(*cleaners, return_exceptions=True)
    
    success_count = sum(1 for r in results if r is True)
    print(f"\nCleaners finished: {success_count}/{len(cleaners)} completed")
    
    return success_count > 0

async def load_to_db():
    """Load data to database."""
    print("\n" + "="*80)
    print("STAGE 3: LOADING TO DATABASE")
    print("="*80)
    
    print("\nLoading data to DB...")
    success = await run_cmd_with_timeout(
        "Load to DB",
        "python src/loadDB/loadData.py",
        max_duration=600
    )
    
    if success:
        print("\nData loaded to DB successfully")
    else:
        print("\nFailed to load data to DB")
    
    return success

async def run_pipeline(scraper_duration=120):
    """Main pipeline with automatic scraper timeout."""
    print("\n" + "="*80)
    print("JOB SCRAPING ASYNC PIPELINE")
    print("="*80)
    print(f"\nConfig: Scrapers run for {scraper_duration} seconds each")
    
    from datetime import datetime
    start_time = datetime.now()
    
    try:
        # Stage 1: Scraping with time limit
        scraping_success = await run_scrapers(scraper_duration=scraper_duration)
        if not scraping_success:
            print("\nWarning: All scrapers failed, continuing anyway...")
        
        # Stage 2: Cleaning
        cleaning_success = await run_cleaners()
        if not cleaning_success:
            print("\nError: All cleaners failed, stopping pipeline")
            return False
        
        # Stage 3: Load to DB
        db_success = await load_to_db()
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "="*80)
        print("PIPELINE SUMMARY")
        print("="*80)
        print(f"Started:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration}")
        print(f"Status:   {'SUCCESS' if db_success else 'PARTIAL SUCCESS'}")
        print("="*80 + "\n")
        
        return db_success
        
    except Exception as e:
        print(f"\nPipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Entry point."""
    
    # Change this value to adjust scraping duration
    SCRAPER_DURATION = 120  # seconds (2 minutes)
    
    # Other options:
    # SCRAPER_DURATION = 60    # 1 minute (quick test)
    # SCRAPER_DURATION = 300   # 5 minutes
    # SCRAPER_DURATION = 600   # 10 minutes
    
    print(f"\nStarting pipeline with {SCRAPER_DURATION} seconds per scraper...")
    
    try:
        success = asyncio.run(run_pipeline(scraper_duration=SCRAPER_DURATION))
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Install psutil if needed
    try:
        import subprocess
        import psutil
    except ImportError:
        print("Installing psutil...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
    
    main()