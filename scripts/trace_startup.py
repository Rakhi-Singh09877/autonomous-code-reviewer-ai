"""Trace the full startup sequence from main.py's lifespan(), catching each failure."""
import sys, os, asyncio, time, traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

STEP = 0
def step(name):
    global STEP
    STEP += 1
    print(f"\n{'='*60}")
    print(f"[STEP {STEP}] {name}")
    print(f"{'='*60}")

def fail(e):
    print(f"  RESULT: FAILED")
    print(f"  EXCEPTION: {type(e).__name__}: {e}")
    traceback.print_exc()
    return False

def ok():
    print(f"  RESULT: OK")

async def main():
    step("Import core modules")
    try:
        from app.core.config import settings, _ENV_FILE
        print(f"  _ENV_FILE = {_ENV_FILE}")
        print(f"  _ENV_FILE.exists() = {_ENV_FILE.exists()}")
        print(f"  LLM_PROVIDER = {settings.LLM_PROVIDER}")
        print(f"  GROQ_API_KEY length = {len(settings.GROQ_API_KEY) if settings.GROQ_API_KEY else 0}")
        print(f"  DATABASE_URL = {settings.DATABASE_URL}")
        print(f"  EMBEDDING_PROVIDER = {settings.EMBEDDING_PROVIDER}")
        ok()
    except Exception as e:
        if not fail(e): return

    step("Setup logging")
    try:
        from app.core.logging import setup_logging, logger
        setup_logging()
        logger.info("Logging configured")
        ok()
    except Exception as e:
        if not fail(e): return

    step("Validate configuration (validate_config)")
    try:
        settings.validate_config()
        ok()
    except Exception as e:
        if not fail(e): return

    step("Get DB port (get_db_port)")
    try:
        from app.infrastructure.api.dependencies import get_db_port
        db_port = get_db_port()
        print(f"  db_port type: {type(db_port).__name__}")
        ok()
    except Exception as e:
        if not fail(e): return

    step("Initialize database (db_port.initialize)")
    try:
        await db_port.initialize()
        ok()
    except Exception as e:
        if not fail(e): return

    step("Check database health (db_port.check_health)")
    try:
        db_ok = await db_port.check_health()
        print(f"  db_ok = {db_ok}")
        if not db_ok:
            print("  RESULT: FAILED - database not healthy")
            return
        ok()
    except Exception as e:
        if not fail(e): return

    step("Get RAG port (via ServiceFactory)")
    try:
        from app.core.factory import ServiceFactory
        rag_port = ServiceFactory.get_rag_port()
        print(f"  rag_port type: {type(rag_port).__name__}")
        ok()
    except Exception as e:
        if not fail(e): return

    step("Check RAG health (rag_port.check_health)")
    try:
        rag_ok = await rag_port.check_health()
        print(f"  rag_ok = {rag_ok}")
        if not rag_ok:
            print("  RESULT: FAILED - RAG not healthy")
            return
        ok()
    except Exception as e:
        if not fail(e): return

    step("Get LLM port (via ServiceFactory)")
    try:
        from app.core.factory import ServiceFactory
        llm_port = ServiceFactory.get_llm_port()
        print(f"  llm_port type: {type(llm_port).__name__}")
        ok()
    except Exception as e:
        if not fail(e): return

    step("Check LLM health (llm_port.check_health)")
    try:
        llm_ok = await llm_port.check_health()
        print(f"  llm_ok = {llm_ok}")
        if not llm_ok:
            print("  RESULT: FAILED - LLM not healthy (API key may be invalid or network unavailable)")
            return
        ok()
    except Exception as e:
        if not fail(e): return

    print("\n" + "="*60)
    print("ALL STARTUP CHECKS PASSED")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
