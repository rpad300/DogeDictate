"""
Módulos de abas para o diálogo de configurações.
"""

from .general_tab import GeneralTab
from .languages_tab import LanguagesTab
from .apis_tab import APIsTab
from .local_tab import LocalTab
from .plan_tab import PlanTab
from .account_tab import AccountTab
from .stats_tab import StatsTab

__all__ = [
    'GeneralTab',
    'LanguagesTab',
    'APIsTab',
    'LocalTab',
    'PlanTab',
    'AccountTab',
    'StatsTab'
] 