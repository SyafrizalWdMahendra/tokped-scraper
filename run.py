import asyncio
import sys
import uvicorn

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("✅ Mesin Selector Loop Aktif (Anti-NotImplementedError)")

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)