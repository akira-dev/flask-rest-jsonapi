# -*- coding: utf-8 -*-

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema as MarshmallowSchema
from marshmallow_jsonapi import fields
from marshmallow_jsonapi.flask import Relationship, Schema
from sqlalchemy.orm.exc import NoResultFound

from flask_rest_jsonapi import Api, ResourceDetail, ResourceList, ResourceRelationship
from flask_rest_jsonapi.exceptions import ObjectNotFound

# Create the Flask application
app = Flask(__name__)
app.config["DEBUG"] = True
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# Initialize SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/test.db"
db = SQLAlchemy(app)


# Create data storage
class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String)
    birth_date = db.Column(db.Date)
    password = db.Column(db.String)
    tags = db.relationship(
        "Person_Tag", cascade="save-update, merge, delete, delete-orphan"
    )
    single_tag = db.relationship(
        "Person_Single_Tag",
        uselist=False,
        cascade="save-update, merge, delete, delete-orphan",
    )
    json_tags = db.Column(db.JSON)


class Computer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"))
    person = db.relationship("Person", backref=db.backref("computers"))


class Person_Tag(db.Model):
    id = db.Column(db.Integer, db.ForeignKey("person.id"), primary_key=True, index=True)
    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.String, primary_key=True)


class Person_Single_Tag(db.Model):
    id = db.Column(db.Integer, db.ForeignKey("person.id"), primary_key=True, index=True)
    key = db.Column(db.String)
    value = db.Column(db.String)


db.create_all()


# Create schema
class PersonTagSchema(MarshmallowSchema):
    class Meta:
        type_ = "person_tag"

    id = fields.Str(dump_only=True, load_only=True)
    key = fields.Str()
    value = fields.Str()


class PersonSingleTagSchema(MarshmallowSchema):
    class Meta:
        type_ = "person_single_tag"

    id = fields.Str(dump_only=True, load_only=True)
    key = fields.Str()
    value = fields.Str()


# Create logical data abstraction (same as data storage for this first example)
class PersonSchema(Schema):
    class Meta:
        type_ = "person"
        self_view = "person_detail"
        self_view_kwargs = {"id": "<id>"}
        self_view_many = "person_list"

    id = fields.Integer(as_string=True, dump_only=True)
    name = fields.Str(requried=True, load_only=True)
    email = fields.Email(load_only=True)
    birth_date = fields.Date()
    display_name = fields.Function(
        lambda obj: "{} <{}>".format(obj.name.upper(), obj.email)
    )
    computers = Relationship(
        self_view="person_computers",
        self_view_kwargs={"id": "<id>"},
        related_view="computer_list",
        related_view_kwargs={"id": "<id>"},
        many=True,
        schema="ComputerSchema",
        type_="computer",
    )
    tags = fields.Nested(PersonTagSchema, many=True)


class ComputerSchema(Schema):
    class Meta:
        type_ = "computer"
        self_view = "computer_detail"
        self_view_kwargs = {"id": "<id>"}

    id = fields.Integer(as_string=True, dump_only=True)
    serial = fields.Str(requried=True)
    owner = Relationship(
        attribute="person",
        self_view="computer_person",
        self_view_kwargs={"id": "<id>"},
        related_view="person_detail",
        related_view_kwargs={"computer_id": "<id>"},
        schema="PersonSchema",
        type_="person",
    )


# Create resource managers
class PersonList(ResourceList):
    schema = PersonSchema
    data_layer = {"session": db.session, "model": Person}


class PersonDetail(ResourceDetail):
    def before_get_object(self, view_kwargs):
        if view_kwargs.get("computer_id") is not None:
            try:
                computer = (
                    self.session.query(Computer)
                    .filter_by(id=view_kwargs["computer_id"])
                    .one()
                )
            except NoResultFound:
                raise ObjectNotFound(
                    {"parameter": "computer_id"},
                    "Computer: {} not found".format(view_kwargs["computer_id"]),
                )
            else:
                if computer.person is not None:
                    view_kwargs["id"] = computer.person.id
                else:
                    view_kwargs["id"] = None

    schema = PersonSchema
    data_layer = {
        "session": db.session,
        "model": Person,
        "methods": {"before_get_object": before_get_object},
    }


class PersonRelationship(ResourceRelationship):
    schema = PersonSchema
    data_layer = {"session": db.session, "model": Person}


class PersonTagList(ResourceList):
    schema = PersonTagSchema
    data_layer = {"session": db.session, "model": Person_Tag}


class PersonTagDetail(ResourceDetail):
    schema = PersonTagSchema
    data_layer = {"session": db.session, "model": Person_Tag}


class ComputerList(ResourceList):
    def query(self, view_kwargs):
        query_ = self.session.query(Computer)
        if view_kwargs.get("id") is not None:
            try:
                self.session.query(Person).filter_by(id=view_kwargs["id"]).one()
            except NoResultFound:
                raise ObjectNotFound(
                    {"parameter": "id"},
                    "Person: {} not found".format(view_kwargs["id"]),
                )
            else:
                query_ = query_.join(Person).filter(Person.id == view_kwargs["id"])
        return query_

    def before_create_object(self, data, view_kwargs):
        if view_kwargs.get("id") is not None:
            person = self.session.query(Person).filter_by(id=view_kwargs["id"]).one()
            data["person_id"] = person.id

    schema = ComputerSchema
    data_layer = {
        "session": db.session,
        "model": Computer,
        "methods": {"query": query, "before_create_object": before_create_object},
    }


class ComputerDetail(ResourceDetail):
    schema = ComputerSchema
    data_layer = {"session": db.session, "model": Computer}


class ComputerRelationship(ResourceRelationship):
    schema = ComputerSchema
    data_layer = {"session": db.session, "model": Computer}


# Create endpoints
api = Api(app)
api.route(PersonList, "person_list", "/persons")
api.route(
    PersonDetail,
    "person_detail",
    "/persons/<int:id>",
    "/computers/<int:computer_id>/owner",
)
api.route(
    PersonRelationship, "person_computers", "/persons/<int:id>/relationships/computers"
)
api.route(ComputerList, "computer_list", "/computers", "/persons/<int:id>/computers")
api.route(ComputerDetail, "computer_detail", "/computers/<int:id>")
api.route(
    ComputerRelationship, "computer_person", "/computers/<int:id>/relationships/owner"
)

api.route(PersonTagList, "person_tag_list", "/persontags")
api.route(PersonTagDetail, "person_tag_detail", "/persontags/<int:id>")

if __name__ == "__main__":
    # Start application
    app.run(debug=True)
