import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm.exc import NoResultFound


db = SQLAlchemy()

class Currency(db.Model):
    __tablename__ = 'currencies'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(50), nullable=False, unique=True)
    symbol = db.Column(db.String(10), nullable=False)
    code = db.Column(db.String(5), nullable=False, unique=True)

    def __repr__(self):
        return f"<Currency {self.name} ({self.code})>"

    def __init__(self, name, symbol, code, exchange_rate_to_usd):
        self.name = name
        self.symbol = symbol
        self.code = code
        self.exchange_rate_to_usd = exchange_rate_to_usd

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "symbol": self.symbol,
            "code": self.code,
        }
    
    @staticmethod
    def create_currency(name, symbol, code):
        try:
            new_currency = Currency(
                name=name,
                symbol=symbol,
                code=code,
            )
            db.session.add(new_currency)
            db.session.commit()
            return new_currency
        except Exception as e:
            db.session.rollback()
            return None

    @staticmethod
    def get_currency_by_id(currency_id):
        try:
            return Currency.query.filter_by(id=currency_id).one()
        except NoResultFound:
            return None
        
    @staticmethod
    def list_currencies():
        try:
            return Currency.query.all()
        except Exception as e:
            return None
        