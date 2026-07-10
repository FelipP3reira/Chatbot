from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import obter_configuracao


class Base(DeclarativeBase):
    pass


motor = create_async_engine(obter_configuracao().database_url, pool_pre_ping=True)
criar_sessao = async_sessionmaker(motor, expire_on_commit=False)


async def obter_sessao() -> AsyncIterator[AsyncSession]:
    async with criar_sessao() as sessao:
        yield sessao
