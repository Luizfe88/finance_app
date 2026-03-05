"""
Domain Entity: Category

Budget category with optional spending limit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
import uuid


@dataclass
class Category:
    """A spending category with optional monthly budget limit."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str = ""
    icon: str = "💰"
    color: str = "#6366F1"      # Hex color for frontend charts
    monthly_limit: Optional[Decimal] = None
    is_system: bool = False     # System categories cannot be deleted

    # Predefined system categories (Brazilian fintech standard)
    SYSTEM_CATEGORIES: list[str] = field(default_factory=lambda: [
        "Alimentação", "Transporte", "Moradia", "Saúde",
        "Educação", "Lazer", "Roupas", "Serviços", "Outros"
    ])
