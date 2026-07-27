from contextlib import contextmanager

@contextmanager
def get_session(SessionLocal):
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        session.close()