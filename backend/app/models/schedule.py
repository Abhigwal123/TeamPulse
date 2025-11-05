from app.extensions import db


class Schedule(db.Model):
    __tablename__ = "schedules"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, index=True)
    sheet_id = db.Column(db.String(128))
    status = db.Column(db.String(50), default="PENDING")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "sheet_id": self.sheet_id,
            "status": self.status,
        }



