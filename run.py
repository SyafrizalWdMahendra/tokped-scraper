import asyncio
import sys
import uvicorn

if __name__ == "__main__":
    # Paksa penggunaan SelectorEventLoop di level paling dasar OS Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("✅ Mesin Selector Loop Aktif (Anti-NotImplementedError)")

    # Jalankan uvicorn dari sini, bukan dari terminal langsung
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)