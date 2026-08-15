"""initial schema - all core tables

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''-- Enum types
CREATE TYPE businesstype AS ENUM ('RESTAURANT', 'HOTEL', 'RESORT', 'LODGE', 'LOUNGE', 'CAFE', 'CLOUD_KITCHEN', 'OTHER');
CREATE TYPE featuremodule AS ENUM ('CORE_POS', 'QR_ORDERING', 'ONLINE_WEBSITE', 'PICKUP', 'DELIVERY', 'LOYALTY', 'HOTEL_ROOMS', 'ROOM_SERVICE', 'ONLINE_PAYMENT', 'ZOMATO', 'SWIGGY', 'REVIEWS', 'CUSTOMER_MARKETING');
CREATE TYPE integrationprovider AS ENUM ('RAZORPAY', 'ZOMATO', 'SWIGGY');
CREATE TYPE locationtype AS ENUM ('TABLE', 'ROOM', 'COUNTER', 'SECTION', 'OTHER');
CREATE TYPE locationstatus AS ENUM ('AVAILABLE', 'OCCUPIED', 'ORDERING', 'KITCHEN', 'READY', 'SERVED', 'BILL_PENDING', 'PAID', 'CLOSED');
CREATE TYPE userrole AS ENUM ('OWNER', 'MANAGER', 'CASH_COUNTER', 'SERVICE_COUNTER', 'KITCHEN', 'DELIVERY');
CREATE TYPE webhookprocessstatus AS ENUM ('RECEIVED', 'PROCESSED', 'FAILED', 'DUPLICATE');
CREATE TYPE ordersource AS ENUM ('DINE_IN', 'QR', 'ROOM_SERVICE', 'PICKUP', 'DELIVERY', 'POS', 'ZOMATO', 'SWIGGY');
CREATE TYPE billstatus AS ENUM ('OPEN', 'PARTIALLY_PAID', 'PAID', 'CANCELLED');
CREATE TYPE pricingcontext AS ENUM ('DINE_IN', 'PICKUP', 'DELIVERY', 'ROOM_SERVICE', 'SECTION_A', 'SECTION_B', 'POOL_AREA', 'LOUNGE', 'CUSTOM');
CREATE TYPE orderstatus AS ENUM ('PLACED', 'CONFIRMED', 'PREPARING', 'READY', 'OUT_FOR_DELIVERY', 'SERVED', 'DELIVERED', 'COMPLETED', 'CANCELLED');
CREATE TYPE kotstatus AS ENUM ('NEW', 'ACCEPTED', 'PREPARING', 'READY', 'SERVED', 'CANCELLED');
CREATE TYPE paymentmethod AS ENUM ('CASH', 'UPI', 'CARD', 'ONLINE', 'OTHER');
CREATE TYPE paymentstatus AS ENUM ('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED');

-- Tables
CREATE TABLE businesses (
	name VARCHAR(200) NOT NULL, 
	slug VARCHAR(220) NOT NULL, 
	business_type businesstype NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE business_settings (
	business_id UUID NOT NULL, 
	default_language VARCHAR(10) NOT NULL, 
	supported_languages VARCHAR(100) NOT NULL, 
	timezone VARCHAR(64) NOT NULL, 
	default_tax_percent FLOAT NOT NULL, 
	default_service_charge_percent FLOAT NOT NULL, 
	currency VARCHAR(8) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (business_id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE customers (
	business_id UUID NOT NULL, 
	first_name VARCHAR(100) NOT NULL, 
	mobile VARCHAR(20) NOT NULL, 
	birthday DATE, 
	marketing_opt_in BOOLEAN NOT NULL, 
	sms_opt_in BOOLEAN NOT NULL, 
	email_opt_in BOOLEAN NOT NULL, 
	whatsapp_opt_in BOOLEAN NOT NULL, 
	email VARCHAR(255), 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_customers_business_mobile UNIQUE (business_id, mobile), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE feature_flags (
	business_id UUID NOT NULL, 
	module featuremodule NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_feature_flag_business_module UNIQUE (business_id, module), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE idempotency_keys (
	business_id UUID, 
	scope VARCHAR(60) NOT NULL, 
	key VARCHAR(255) NOT NULL, 
	response_snapshot TEXT, 
	resource_id UUID, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE integration_events (
	business_id UUID NOT NULL, 
	provider integrationprovider NOT NULL, 
	event_type VARCHAR(60) NOT NULL, 
	payload TEXT, 
	status VARCHAR(30) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE integration_logs (
	business_id UUID, 
	provider integrationprovider NOT NULL, 
	action VARCHAR(100) NOT NULL, 
	success BOOLEAN NOT NULL, 
	detail TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE integrations (
	business_id UUID NOT NULL, 
	provider integrationprovider NOT NULL, 
	is_connected BOOLEAN NOT NULL, 
	last_synced_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_integration_business_provider UNIQUE (business_id, provider), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE locations (
	business_id UUID NOT NULL, 
	location_type locationtype NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	capacity INTEGER, 
	floor VARCHAR(50), 
	room_type VARCHAR(100), 
	status locationstatus NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE loyalty_rules (
	business_id UUID NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	rule_type VARCHAR(40) NOT NULL, 
	threshold NUMERIC(12, 2) NOT NULL, 
	reward_type VARCHAR(40) NOT NULL, 
	reward_value NUMERIC(10, 2), 
	is_active BOOLEAN NOT NULL, 
	description TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE menu_categories (
	business_id UUID NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	description TEXT, 
	display_order INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE translations (
	business_id UUID NOT NULL, 
	entity_type VARCHAR(60) NOT NULL, 
	entity_id UUID NOT NULL, 
	field_name VARCHAR(60) NOT NULL, 
	language VARCHAR(10) NOT NULL, 
	value TEXT NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_translation_entity_field_lang UNIQUE (business_id, entity_type, entity_id, field_name, language), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE users (
	business_id UUID NOT NULL, 
	first_name VARCHAR(100) NOT NULL, 
	last_name VARCHAR(100) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	mobile VARCHAR(20) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role userrole NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	is_email_verified BOOLEAN NOT NULL, 
	failed_login_attempts INTEGER NOT NULL, 
	locked_until TIMESTAMP WITH TIME ZONE, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_users_email UNIQUE (email), 
	CONSTRAINT uq_users_mobile UNIQUE (mobile), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE webhook_events (
	business_id UUID, 
	provider integrationprovider NOT NULL, 
	provider_event_id VARCHAR(255) NOT NULL, 
	signature_valid BOOLEAN NOT NULL, 
	raw_payload TEXT NOT NULL, 
	status webhookprocessstatus NOT NULL, 
	processed_at TIMESTAMP WITH TIME ZONE, 
	error TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_webhook_provider_event UNIQUE (provider, provider_event_id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE website_configs (
	business_id UUID NOT NULL, 
	is_published BOOLEAN NOT NULL, 
	logo_url VARCHAR(500), 
	hero_image_url VARCHAR(500), 
	story TEXT, 
	contact_phone VARCHAR(20), 
	contact_email VARCHAR(255), 
	contact_address TEXT, 
	theme_color VARCHAR(20), 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (business_id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE TABLE audit_logs (
	business_id UUID, 
	user_id UUID, 
	action VARCHAR(100) NOT NULL, 
	resource_type VARCHAR(60), 
	resource_id VARCHAR(64), 
	ip_address VARCHAR(64), 
	metadata_json TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE email_verification_codes (
	user_id UUID NOT NULL, 
	code_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	used_at TIMESTAMP WITH TIME ZONE, 
	invalidated_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE integration_credentials (
	integration_id UUID NOT NULL, 
	encrypted_payload TEXT NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (integration_id), 
	FOREIGN KEY(integration_id) REFERENCES integrations (id) ON DELETE CASCADE
);

CREATE TABLE loyalty_accounts (
	business_id UUID NOT NULL, 
	customer_id UUID NOT NULL, 
	total_orders INTEGER NOT NULL, 
	total_spend NUMERIC(12, 2) NOT NULL, 
	points_balance NUMERIC(12, 2) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE CASCADE
);

CREATE TABLE menu_items (
	business_id UUID NOT NULL, 
	category_id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description TEXT, 
	base_price NUMERIC(10, 2) NOT NULL, 
	is_veg BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	is_sold_out BOOLEAN NOT NULL, 
	is_todays_special BOOLEAN NOT NULL, 
	is_specialty BOOLEAN NOT NULL, 
	image_url VARCHAR(500), 
	display_order INTEGER NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(category_id) REFERENCES menu_categories (id) ON DELETE CASCADE
);

CREATE TABLE order_sessions (
	business_id UUID NOT NULL, 
	location_id UUID, 
	customer_id UUID, 
	source ordersource NOT NULL, 
	is_closed BOOLEAN NOT NULL, 
	closed_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE SET NULL, 
	FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE SET NULL
);

CREATE TABLE password_reset_tokens (
	user_id UUID NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	used_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE qr_codes (
	business_id UUID NOT NULL, 
	location_id UUID NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_qr_codes_location UNIQUE (location_id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE CASCADE
);

CREATE TABLE qr_sessions (
	business_id UUID NOT NULL, 
	location_id UUID NOT NULL, 
	session_token VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	closed_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE CASCADE
);

CREATE TABLE refresh_tokens (
	user_id UUID NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	replaced_by_id UUID, 
	user_agent VARCHAR(255), 
	ip_address VARCHAR(64), 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(replaced_by_id) REFERENCES refresh_tokens (id) ON DELETE SET NULL
);

CREATE TABLE bills (
	business_id UUID NOT NULL, 
	session_id UUID NOT NULL, 
	location_id UUID, 
	bill_number VARCHAR(40) NOT NULL, 
	status billstatus NOT NULL, 
	subtotal NUMERIC(10, 2) NOT NULL, 
	tax_total NUMERIC(10, 2) NOT NULL, 
	service_charge_total NUMERIC(10, 2) NOT NULL, 
	discount_total NUMERIC(10, 2) NOT NULL, 
	grand_total NUMERIC(10, 2) NOT NULL, 
	amount_paid NUMERIC(10, 2) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(session_id) REFERENCES order_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE SET NULL
);

CREATE TABLE menu_availabilities (
	business_id UUID NOT NULL, 
	item_id UUID NOT NULL, 
	day_of_week INTEGER NOT NULL, 
	start_time_minutes INTEGER NOT NULL, 
	end_time_minutes INTEGER NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(item_id) REFERENCES menu_items (id) ON DELETE CASCADE
);

CREATE TABLE menu_option_groups (
	business_id UUID NOT NULL, 
	item_id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	is_required BOOLEAN NOT NULL, 
	allow_multiple BOOLEAN NOT NULL, 
	display_order INTEGER NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(item_id) REFERENCES menu_items (id) ON DELETE CASCADE
);

CREATE TABLE menu_variants (
	business_id UUID NOT NULL, 
	item_id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	price_delta NUMERIC(10, 2) NOT NULL, 
	is_default BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(item_id) REFERENCES menu_items (id) ON DELETE CASCADE
);

CREATE TABLE orders (
	business_id UUID NOT NULL, 
	session_id UUID NOT NULL, 
	location_id UUID, 
	customer_id UUID, 
	order_number VARCHAR(40) NOT NULL, 
	source ordersource NOT NULL, 
	pricing_context pricingcontext NOT NULL, 
	status orderstatus NOT NULL, 
	is_additional BOOLEAN NOT NULL, 
	parent_order_id UUID, 
	subtotal NUMERIC(10, 2) NOT NULL, 
	notes TEXT, 
	placed_by_staff_id UUID, 
	delivery_status VARCHAR(30), 
	delivery_address TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(session_id) REFERENCES order_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE SET NULL, 
	FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE SET NULL, 
	FOREIGN KEY(parent_order_id) REFERENCES orders (id) ON DELETE SET NULL, 
	FOREIGN KEY(placed_by_staff_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE rewards (
	business_id UUID NOT NULL, 
	account_id UUID NOT NULL, 
	rule_id UUID NOT NULL, 
	reward_type VARCHAR(40) NOT NULL, 
	reward_value NUMERIC(10, 2), 
	is_redeemed BOOLEAN NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(account_id) REFERENCES loyalty_accounts (id) ON DELETE CASCADE, 
	FOREIGN KEY(rule_id) REFERENCES loyalty_rules (id) ON DELETE CASCADE
);

CREATE TABLE bill_discounts (
	business_id UUID NOT NULL, 
	bill_id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	percent NUMERIC(5, 2), 
	amount NUMERIC(10, 2) NOT NULL, 
	reason VARCHAR(255), 
	applied_by_staff_id UUID, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(bill_id) REFERENCES bills (id) ON DELETE CASCADE, 
	FOREIGN KEY(applied_by_staff_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE bill_service_charges (
	business_id UUID NOT NULL, 
	bill_id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	percent NUMERIC(5, 2) NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(bill_id) REFERENCES bills (id) ON DELETE CASCADE
);

CREATE TABLE bill_taxes (
	business_id UUID NOT NULL, 
	bill_id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	percent NUMERIC(5, 2) NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(bill_id) REFERENCES bills (id) ON DELETE CASCADE
);

CREATE TABLE kots (
	business_id UUID NOT NULL, 
	order_id UUID NOT NULL, 
	location_id UUID, 
	kot_number VARCHAR(40) NOT NULL, 
	status kotstatus NOT NULL, 
	special_instructions TEXT, 
	estimated_minutes INTEGER, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE SET NULL
);

CREATE TABLE loyalty_transactions (
	business_id UUID NOT NULL, 
	account_id UUID NOT NULL, 
	order_id UUID, 
	points_delta NUMERIC(12, 2) NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(account_id) REFERENCES loyalty_accounts (id) ON DELETE CASCADE, 
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE SET NULL
);

CREATE TABLE menu_options (
	business_id UUID NOT NULL, 
	group_id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	price_delta NUMERIC(10, 2) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	display_order INTEGER NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(group_id) REFERENCES menu_option_groups (id) ON DELETE CASCADE
);

CREATE TABLE order_items (
	business_id UUID NOT NULL, 
	order_id UUID NOT NULL, 
	menu_item_id UUID NOT NULL, 
	variant_id UUID, 
	item_name_snapshot VARCHAR(200) NOT NULL, 
	quantity INTEGER NOT NULL, 
	unit_price NUMERIC(10, 2) NOT NULL, 
	line_total NUMERIC(10, 2) NOT NULL, 
	special_instructions TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, 
	FOREIGN KEY(menu_item_id) REFERENCES menu_items (id) ON DELETE RESTRICT, 
	FOREIGN KEY(variant_id) REFERENCES menu_variants (id) ON DELETE RESTRICT
);

CREATE TABLE payments (
	business_id UUID NOT NULL, 
	bill_id UUID NOT NULL, 
	method paymentmethod NOT NULL, 
	status paymentstatus NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL, 
	provider VARCHAR(30), 
	provider_order_id VARCHAR(120), 
	provider_payment_id VARCHAR(120), 
	provider_signature VARCHAR(255), 
	verified_at TIMESTAMP WITH TIME ZONE, 
	received_by_staff_id UUID, 
	notes TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(bill_id) REFERENCES bills (id) ON DELETE CASCADE, 
	FOREIGN KEY(received_by_staff_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE price_rules (
	business_id UUID NOT NULL, 
	item_id UUID NOT NULL, 
	variant_id UUID, 
	context pricingcontext NOT NULL, 
	price NUMERIC(10, 2) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_price_rule_item_variant_context UNIQUE (item_id, variant_id, context), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(item_id) REFERENCES menu_items (id) ON DELETE CASCADE, 
	FOREIGN KEY(variant_id) REFERENCES menu_variants (id) ON DELETE CASCADE
);

CREATE TABLE redemptions (
	business_id UUID NOT NULL, 
	reward_id UUID NOT NULL, 
	order_id UUID, 
	redeemed_by_staff_id UUID, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	UNIQUE (reward_id), 
	FOREIGN KEY(reward_id) REFERENCES rewards (id) ON DELETE CASCADE, 
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE SET NULL, 
	FOREIGN KEY(redeemed_by_staff_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE reviews (
	business_id UUID NOT NULL, 
	order_id UUID, 
	customer_id UUID, 
	first_name VARCHAR(100) NOT NULL, 
	mobile VARCHAR(20) NOT NULL, 
	rating INTEGER NOT NULL, 
	comment TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE SET NULL, 
	FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE SET NULL
);

CREATE TABLE bill_items (
	business_id UUID NOT NULL, 
	bill_id UUID NOT NULL, 
	order_item_id UUID NOT NULL, 
	item_name_snapshot VARCHAR(200) NOT NULL, 
	quantity NUMERIC(10, 2) NOT NULL, 
	unit_price NUMERIC(10, 2) NOT NULL, 
	line_total NUMERIC(10, 2) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(bill_id) REFERENCES bills (id) ON DELETE CASCADE, 
	FOREIGN KEY(order_item_id) REFERENCES order_items (id) ON DELETE RESTRICT
);

CREATE TABLE kot_items (
	business_id UUID NOT NULL, 
	kot_id UUID NOT NULL, 
	order_item_id UUID NOT NULL, 
	item_name_snapshot VARCHAR(200) NOT NULL, 
	quantity INTEGER NOT NULL, 
	options_summary TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(kot_id) REFERENCES kots (id) ON DELETE CASCADE, 
	FOREIGN KEY(order_item_id) REFERENCES order_items (id) ON DELETE CASCADE
);

CREATE TABLE order_item_options (
	business_id UUID NOT NULL, 
	order_item_id UUID NOT NULL, 
	option_id UUID NOT NULL, 
	option_name_snapshot VARCHAR(100) NOT NULL, 
	price_delta_snapshot NUMERIC(10, 2) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE, 
	FOREIGN KEY(order_item_id) REFERENCES order_items (id) ON DELETE CASCADE, 
	FOREIGN KEY(option_id) REFERENCES menu_options (id) ON DELETE RESTRICT
);

-- Indexes
CREATE UNIQUE INDEX ix_businesses_slug ON businesses (slug);
CREATE INDEX ix_customers_business_id ON customers (business_id);
CREATE INDEX ix_customers_mobile ON customers (mobile);
CREATE INDEX ix_feature_flags_business_id ON feature_flags (business_id);
CREATE INDEX ix_idempotency_keys_key ON idempotency_keys (key);
CREATE INDEX ix_idempotency_keys_business_id ON idempotency_keys (business_id);
CREATE INDEX ix_integration_events_business_id ON integration_events (business_id);
CREATE INDEX ix_integration_logs_business_id ON integration_logs (business_id);
CREATE INDEX ix_integrations_business_id ON integrations (business_id);
CREATE INDEX ix_locations_business_id ON locations (business_id);
CREATE INDEX ix_loyalty_rules_business_id ON loyalty_rules (business_id);
CREATE INDEX ix_menu_categories_business_id ON menu_categories (business_id);
CREATE INDEX ix_translations_entity_id ON translations (entity_id);
CREATE INDEX ix_translations_business_id ON translations (business_id);
CREATE INDEX ix_translations_entity_type ON translations (entity_type);
CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_business_id ON users (business_id);
CREATE INDEX ix_users_mobile ON users (mobile);
CREATE INDEX ix_webhook_events_business_id ON webhook_events (business_id);
CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX ix_audit_logs_business_id ON audit_logs (business_id);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_email_verification_codes_user_id ON email_verification_codes (user_id);
CREATE INDEX ix_loyalty_accounts_business_id ON loyalty_accounts (business_id);
CREATE UNIQUE INDEX ix_loyalty_accounts_customer_id ON loyalty_accounts (customer_id);
CREATE INDEX ix_menu_items_business_id ON menu_items (business_id);
CREATE INDEX ix_menu_items_category_id ON menu_items (category_id);
CREATE INDEX ix_order_sessions_business_id ON order_sessions (business_id);
CREATE INDEX ix_order_sessions_location_id ON order_sessions (location_id);
CREATE UNIQUE INDEX ix_password_reset_tokens_token_hash ON password_reset_tokens (token_hash);
CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens (user_id);
CREATE INDEX ix_qr_codes_business_id ON qr_codes (business_id);
CREATE INDEX ix_qr_codes_location_id ON qr_codes (location_id);
CREATE UNIQUE INDEX ix_qr_codes_code ON qr_codes (code);
CREATE INDEX ix_qr_sessions_business_id ON qr_sessions (business_id);
CREATE INDEX ix_qr_sessions_location_id ON qr_sessions (location_id);
CREATE UNIQUE INDEX ix_qr_sessions_session_token ON qr_sessions (session_token);
CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE UNIQUE INDEX ix_refresh_tokens_token_hash ON refresh_tokens (token_hash);
CREATE INDEX ix_bills_business_id ON bills (business_id);
CREATE INDEX ix_bills_session_id ON bills (session_id);
CREATE INDEX ix_bills_bill_number ON bills (bill_number);
CREATE INDEX ix_menu_availabilities_item_id ON menu_availabilities (item_id);
CREATE INDEX ix_menu_availabilities_business_id ON menu_availabilities (business_id);
CREATE INDEX ix_menu_option_groups_business_id ON menu_option_groups (business_id);
CREATE INDEX ix_menu_option_groups_item_id ON menu_option_groups (item_id);
CREATE INDEX ix_menu_variants_item_id ON menu_variants (item_id);
CREATE INDEX ix_menu_variants_business_id ON menu_variants (business_id);
CREATE INDEX ix_orders_session_id ON orders (session_id);
CREATE INDEX ix_orders_location_id ON orders (location_id);
CREATE INDEX ix_orders_order_number ON orders (order_number);
CREATE INDEX ix_orders_business_id ON orders (business_id);
CREATE INDEX ix_rewards_account_id ON rewards (account_id);
CREATE INDEX ix_rewards_business_id ON rewards (business_id);
CREATE INDEX ix_bill_discounts_business_id ON bill_discounts (business_id);
CREATE INDEX ix_bill_discounts_bill_id ON bill_discounts (bill_id);
CREATE INDEX ix_bill_service_charges_business_id ON bill_service_charges (business_id);
CREATE INDEX ix_bill_service_charges_bill_id ON bill_service_charges (bill_id);
CREATE INDEX ix_bill_taxes_bill_id ON bill_taxes (bill_id);
CREATE INDEX ix_bill_taxes_business_id ON bill_taxes (business_id);
CREATE INDEX ix_kots_business_id ON kots (business_id);
CREATE INDEX ix_kots_location_id ON kots (location_id);
CREATE INDEX ix_kots_order_id ON kots (order_id);
CREATE INDEX ix_kots_kot_number ON kots (kot_number);
CREATE INDEX ix_loyalty_transactions_business_id ON loyalty_transactions (business_id);
CREATE INDEX ix_loyalty_transactions_account_id ON loyalty_transactions (account_id);
CREATE INDEX ix_menu_options_business_id ON menu_options (business_id);
CREATE INDEX ix_menu_options_group_id ON menu_options (group_id);
CREATE INDEX ix_order_items_business_id ON order_items (business_id);
CREATE INDEX ix_order_items_order_id ON order_items (order_id);
CREATE INDEX ix_payments_bill_id ON payments (bill_id);
CREATE INDEX ix_payments_provider_order_id ON payments (provider_order_id);
CREATE INDEX ix_payments_provider_payment_id ON payments (provider_payment_id);
CREATE INDEX ix_payments_business_id ON payments (business_id);
CREATE INDEX ix_price_rules_business_id ON price_rules (business_id);
CREATE INDEX ix_price_rules_item_id ON price_rules (item_id);
CREATE INDEX ix_redemptions_business_id ON redemptions (business_id);
CREATE INDEX ix_reviews_business_id ON reviews (business_id);
CREATE INDEX ix_bill_items_bill_id ON bill_items (bill_id);
CREATE INDEX ix_bill_items_business_id ON bill_items (business_id);
CREATE INDEX ix_kot_items_business_id ON kot_items (business_id);
CREATE INDEX ix_kot_items_kot_id ON kot_items (kot_id);
CREATE INDEX ix_order_item_options_order_item_id ON order_item_options (order_item_id);
CREATE INDEX ix_order_item_options_business_id ON order_item_options (business_id);''')


def downgrade() -> None:
    op.execute('''DROP TABLE IF EXISTS order_item_options CASCADE;
DROP TABLE IF EXISTS kot_items CASCADE;
DROP TABLE IF EXISTS bill_items CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS redemptions CASCADE;
DROP TABLE IF EXISTS price_rules CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS menu_options CASCADE;
DROP TABLE IF EXISTS loyalty_transactions CASCADE;
DROP TABLE IF EXISTS kots CASCADE;
DROP TABLE IF EXISTS bill_taxes CASCADE;
DROP TABLE IF EXISTS bill_service_charges CASCADE;
DROP TABLE IF EXISTS bill_discounts CASCADE;
DROP TABLE IF EXISTS rewards CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS menu_variants CASCADE;
DROP TABLE IF EXISTS menu_option_groups CASCADE;
DROP TABLE IF EXISTS menu_availabilities CASCADE;
DROP TABLE IF EXISTS bills CASCADE;
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS qr_sessions CASCADE;
DROP TABLE IF EXISTS qr_codes CASCADE;
DROP TABLE IF EXISTS password_reset_tokens CASCADE;
DROP TABLE IF EXISTS order_sessions CASCADE;
DROP TABLE IF EXISTS menu_items CASCADE;
DROP TABLE IF EXISTS loyalty_accounts CASCADE;
DROP TABLE IF EXISTS integration_credentials CASCADE;
DROP TABLE IF EXISTS email_verification_codes CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS website_configs CASCADE;
DROP TABLE IF EXISTS webhook_events CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS translations CASCADE;
DROP TABLE IF EXISTS menu_categories CASCADE;
DROP TABLE IF EXISTS loyalty_rules CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
DROP TABLE IF EXISTS integrations CASCADE;
DROP TABLE IF EXISTS integration_logs CASCADE;
DROP TABLE IF EXISTS integration_events CASCADE;
DROP TABLE IF EXISTS idempotency_keys CASCADE;
DROP TABLE IF EXISTS feature_flags CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS business_settings CASCADE;
DROP TABLE IF EXISTS businesses CASCADE;
DROP TYPE IF EXISTS businesstype;
DROP TYPE IF EXISTS featuremodule;
DROP TYPE IF EXISTS integrationprovider;
DROP TYPE IF EXISTS locationtype;
DROP TYPE IF EXISTS locationstatus;
DROP TYPE IF EXISTS userrole;
DROP TYPE IF EXISTS webhookprocessstatus;
DROP TYPE IF EXISTS ordersource;
DROP TYPE IF EXISTS billstatus;
DROP TYPE IF EXISTS pricingcontext;
DROP TYPE IF EXISTS orderstatus;
DROP TYPE IF EXISTS kotstatus;
DROP TYPE IF EXISTS paymentmethod;
DROP TYPE IF EXISTS paymentstatus;''')
