from sqlalchemy import Column, Integer, String, Text

from app.db import Base


class Chunk(Base):
    """One retrievable RAG chunk. id doubles as the FAISS vector ID —
    crawler/build_index.py assigns both from the same sequence.
    """

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    title = Column(String)
    topic = Column(String)
    source = Column(String)
    content = Column(Text, nullable=False)
    crawled_at = Column(String)
