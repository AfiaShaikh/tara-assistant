"""Launch from any working directory: python Code/run.py"""
import os
from pathlib import Path
os.chdir(Path(__file__).resolve().parent)
if __name__=='__main__':
    import uvicorn
    uvicorn.run('app:app',host=os.getenv('TARA_HOST','127.0.0.1'),port=int(os.getenv('TARA_PORT','8000')))
