import asyncio
import logging
from decimal import Decimal

from sqlalchemy import func, select

from erp_api.database import dispose_engine, get_session_factory
from erp_api.services.produtos.models import Produto

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("seed")

PRODUTOS = [
    ("Teclado mecânico ABNT2", "349.90", 25),
    ("Mouse óptico sem fio", "89.90", 40),
    ('Monitor 27" IPS', "1299.00", 12),
    ("Notebook i5 16GB", "4599.00", 8),
    ("Cabo HDMI 2.1 2m", "39.90", 3),
    ("Hub USB-C 7 portas", "159.90", 0),
    ("Webcam Full HD", "199.90", 18),
    ("Headset com microfone", "249.90", 6),
    ("SSD NVMe 1TB", "449.90", 30),
    ("Suporte ergonômico de monitor", "119.90", 2),
]


async def seed() -> None:
    async with get_session_factory()() as session:
        total = await session.scalar(select(func.count()).select_from(Produto)) or 0
        if total > 0:
            log.info(f"Banco já tem {total} produto(s); seed ignorado.")
            return

        session.add_all(
            Produto(nome=nome, preco=Decimal(preco), quantidade_em_estoque=quantidade)
            for nome, preco, quantidade in PRODUTOS
        )
        await session.commit()
        log.info(f"Seed concluído: {len(PRODUTOS)} produtos inseridos.")


async def main() -> None:
    try:
        await seed()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
