"""Application package for the Auto MDF control center.

Guia de edição (resumido)
- Modificável pelo usuário:
	- Importações públicas referenciadas por scripts e pontos de entrada simples.
	- Ajustes de comportamento UI de alto nível.
- Requer atenção:
	- Alterações que mudem contratos públicos (ex.: nomes de funções exportadas) podem quebrar scripts.
- Apenas para devs:
	- Refatorações internas, mudanças de API, otimizações de baixo nível.

Veja `docs/EDIT_GUIDELINES.md` para regras e exemplos.
"""

from .main import main, run

__all__ = ["main", "run"]
