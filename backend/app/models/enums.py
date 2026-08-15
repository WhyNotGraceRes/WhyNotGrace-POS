"""Shared enums used across models, schemas, and services."""
from enum import StrEnum


class BusinessType(StrEnum):
    RESTAURANT = "RESTAURANT"
    HOTEL = "HOTEL"
    RESORT = "RESORT"
    LODGE = "LODGE"
    LOUNGE = "LOUNGE"
    CAFE = "CAFE"
    CLOUD_KITCHEN = "CLOUD_KITCHEN"
    OTHER = "OTHER"


class UserRole(StrEnum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    CASH_COUNTER = "CASH_COUNTER"
    SERVICE_COUNTER = "SERVICE_COUNTER"
    KITCHEN = "KITCHEN"
    DELIVERY = "DELIVERY"


class FeatureModule(StrEnum):
    CORE_POS = "CORE_POS"
    QR_ORDERING = "QR_ORDERING"
    ONLINE_WEBSITE = "ONLINE_WEBSITE"
    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"
    LOYALTY = "LOYALTY"
    HOTEL_ROOMS = "HOTEL_ROOMS"
    ROOM_SERVICE = "ROOM_SERVICE"
    ONLINE_PAYMENT = "ONLINE_PAYMENT"
    ZOMATO = "ZOMATO"
    SWIGGY = "SWIGGY"
    REVIEWS = "REVIEWS"
    CUSTOMER_MARKETING = "CUSTOMER_MARKETING"
    # Lets a business's own website (a first-party site built for them)
    # submit orders through the partner channel API. Off by default, so a
    # business must deliberately enable inbound order submission before any
    # credential an owner issues will actually work — two independent gates,
    # not one.
    PARTNER_CHANNEL = "PARTNER_CHANNEL"


# Features that are always on and cannot be disabled by a business.
ALWAYS_ON_FEATURES = {FeatureModule.CORE_POS}


class LocationType(StrEnum):
    TABLE = "TABLE"
    ROOM = "ROOM"
    COUNTER = "COUNTER"
    SECTION = "SECTION"
    OTHER = "OTHER"


class LocationStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    ORDERING = "ORDERING"
    KITCHEN = "KITCHEN"
    READY = "READY"
    SERVED = "SERVED"
    BILL_PENDING = "BILL_PENDING"
    PAID = "PAID"
    CLOSED = "CLOSED"


class PricingContext(StrEnum):
    DINE_IN = "DINE_IN"
    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"
    ROOM_SERVICE = "ROOM_SERVICE"
    SECTION_A = "SECTION_A"
    SECTION_B = "SECTION_B"
    POOL_AREA = "POOL_AREA"
    LOUNGE = "LOUNGE"
    CUSTOM = "CUSTOM"


class OrderSource(StrEnum):
    DINE_IN = "DINE_IN"
    QR = "QR"
    ROOM_SERVICE = "ROOM_SERVICE"
    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"
    POS = "POS"
    ZOMATO = "ZOMATO"
    SWIGGY = "SWIGGY"


class OrderStatus(StrEnum):
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    SERVED = "SERVED"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class KOTStatus(StrEnum):
    NEW = "NEW"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    SERVED = "SERVED"
    CANCELLED = "CANCELLED"


class BillStatus(StrEnum):
    OPEN = "OPEN"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class PaymentMethod(StrEnum):
    CASH = "CASH"
    UPI = "UPI"
    CARD = "CARD"
    ONLINE = "ONLINE"
    OTHER = "OTHER"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class DeliveryStatus(StrEnum):
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class IntegrationProvider(StrEnum):
    RAZORPAY = "RAZORPAY"
    ZOMATO = "ZOMATO"
    SWIGGY = "SWIGGY"


class WebhookProcessStatus(StrEnum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class CommunicationChannel(StrEnum):
    SMS = "SMS"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    PUSH = "PUSH"


class LanguageCode(StrEnum):
    EN = "en"
    HI = "hi"
    MR = "mr"


class SubscriptionStatus(StrEnum):
    """Lifecycle of a business's platform subscription (WhyNotGrace being
    paid BY the business — never to be confused with IntegrationProvider.RAZORPAY,
    which is the business's own account for charging ITS customers).
    A business with no Subscription row yet is represented as NOT_CONFIGURED
    at the API layer, not as a row in this enum.
    """
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
