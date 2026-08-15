import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.customer import Customer


def get_or_create_by_mobile(db: Session, business_id: uuid.UUID, payload) -> Customer:
    customer = db.query(Customer).filter(
        Customer.business_id == business_id, Customer.mobile == payload.mobile
    ).first()
    if customer is not None:
        return customer
    customer = Customer(business_id=business_id, **payload.model_dump())
    db.add(customer)
    db.flush()
    return customer


def get_customer_or_404(db: Session, business_id: uuid.UUID, customer_id: uuid.UUID) -> Customer:
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.business_id == business_id).first()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


def list_customers(db: Session, business_id: uuid.UUID) -> list[Customer]:
    return db.query(Customer).filter(Customer.business_id == business_id).order_by(Customer.created_at.desc()).all()


def update_customer(db: Session, business_id: uuid.UUID, customer_id: uuid.UUID, payload) -> Customer:
    customer = get_customer_or_404(db, business_id, customer_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.flush()
    return customer
