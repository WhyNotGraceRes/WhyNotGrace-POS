"""Import every model module so Base.metadata is complete for Alembic
autogenerate and for create_all() in tests. Do not remove imports even if
they look unused — they register tables as a side effect.
"""
from app.database.base import Base  # noqa: F401

from app.models import enums  # noqa: F401
from app.models.business import Business, BusinessSettings  # noqa: F401
from app.models.user import User, RefreshToken, EmailVerificationCode, PasswordResetToken  # noqa: F401
from app.models.feature_flag import FeatureFlag  # noqa: F401
from app.models.menu import (  # noqa: F401
    MenuCategory,
    MenuItem,
    MenuVariant,
    MenuOptionGroup,
    MenuOption,
    MenuAvailability,
)
from app.models.pricing import PriceRule  # noqa: F401
from app.models.location import Location, QRCode, QRSession  # noqa: F401
from app.models.order import Order, OrderItem, OrderItemOption, OrderSession  # noqa: F401
from app.models.kot import KOT, KOTItem  # noqa: F401
from app.models.billing import Bill, BillItem, BillTax, BillDiscount, BillServiceCharge  # noqa: F401
from app.models.payment import Payment, IdempotencyKey  # noqa: F401
from app.models.customer import Customer  # noqa: F401
from app.models.loyalty import LoyaltyRule, LoyaltyAccount, LoyaltyTransaction, Reward, Redemption  # noqa: F401
from app.models.review import Review  # noqa: F401
from app.models.website import WebsiteConfig  # noqa: F401
from app.models.integration import (  # noqa: F401
    Integration,
    IntegrationCredential,
    IntegrationEvent,
    WebhookEvent,
    IntegrationLog,
)
from app.models.translation import Translation  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.subscription import Subscription, SubscriptionPayment  # noqa: F401
from app.models.partner import PartnerChannel, PartnerMenuMap, PartnerRequestNonce  # noqa: F401

__all__ = ["Base"]
