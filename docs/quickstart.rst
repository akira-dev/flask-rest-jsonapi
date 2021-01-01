.. _quickstart:

Quickstart
==========

.. currentmodule:: flask_rest_jsonapi

It's time to write your first REST API. This guide assumes you have a working understanding of `Flask <http://flask.pocoo.org>`_, and that you have already installed both Flask and Flask-REST-JSONAPI. If not, then follow the steps in the :ref:`installation` section.

In this section you will learn basic usage of Flask-REST-JSONAPI around a small tutorial that use the SQLAlchemy data layer. This tutorial show you an example of a person and his computers.

First example
-------------

An example of Flask-REST-JSONAPI API looks like this:

.. code-block:: python

    # -*- coding: utf-8 -*-

    from flask import Flask
    from flask_rest_jsonapi import Api, ResourceDetail, ResourceList, ResourceRelationship
    from flask_rest_jsonapi.exceptions import ObjectNotFound
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy.orm.exc import NoResultFound
    from marshmallow_jsonapi.flask import Schema, Relationship
    from marshmallow_jsonapi import fields

    # Create the Flask application
    app = Flask(__name__)
    app.config['DEBUG'] = True


    # Initialize SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
    db = SQLAlchemy(app)


    # Create data storage
    class Person(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String)
        email = db.Column(db.String)
        birth_date = db.Column(db.Date)
        password = db.Column(db.String)


    class Computer(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        serial = db.Column(db.String)
        person_id = db.Column(db.Integer, db.ForeignKey('person.id'))
        person = db.relationship('Person', backref=db.backref('computers'))

    db.create_all()


    # Create logical data abstraction (same as data storage for this first example)
    class PersonSchema(Schema):
        class Meta:
            type_ = 'person'
            self_view = 'person_detail'
            self_view_kwargs = {'id': '<id>'}
            self_view_many = 'person_list'

        id = fields.Integer(as_string=True, dump_only=True)
        name = fields.Str(required=True, load_only=True)
        email = fields.Email(load_only=True)
        birth_date = fields.Date()
        display_name = fields.Function(lambda obj: "{} <{}>".format(obj.name.upper(), obj.email))
        computers = Relationship(self_view='person_computers',
                                 self_view_kwargs={'id': '<id>'},
                                 related_view='computer_list',
                                 related_view_kwargs={'id': '<id>'},
                                 many=True,
                                 schema='ComputerSchema',
                                 type_='computer')


    class ComputerSchema(Schema):
        class Meta:
            type_ = 'computer'
            self_view = 'computer_detail'
            self_view_kwargs = {'id': '<id>'}

        id = fields.Integer(as_string=True, dump_only=True)
        serial = fields.Str(required=True)
        owner = Relationship(attribute='person',
                             self_view='computer_person',
                             self_view_kwargs={'id': '<id>'},
                             related_view='person_detail',
                             related_view_kwargs={'computer_id': '<id>'},
                             schema='PersonSchema',
                             type_='person')


    # Create resource managers
    class PersonList(ResourceList):
        schema = PersonSchema
        data_layer = {'session': db.session,
                      'model': Person}


    class PersonDetail(ResourceDetail):
        def before_get_object(self, view_kwargs):
            if view_kwargs.get('computer_id') is not None:
                try:
                    computer = self.session.query(Computer).filter_by(id=view_kwargs['computer_id']).one()
                except NoResultFound:
                    raise ObjectNotFound({'parameter': 'computer_id'},
                                         "Computer: {} not found".format(view_kwargs['computer_id']))
                else:
                    if computer.person is not None:
                        view_kwargs['id'] = computer.person.id
                    else:
                        view_kwargs['id'] = None

        schema = PersonSchema
        data_layer = {'session': db.session,
                      'model': Person,
                      'methods': {'before_get_object': before_get_object}}


    class PersonRelationship(ResourceRelationship):
        schema = PersonSchema
        data_layer = {'session': db.session,
                      'model': Person}


    class ComputerList(ResourceList):
        def query(self, view_kwargs):
            query_ = self.session.query(Computer)
            if view_kwargs.get('id') is not None:
                try:
                    self.session.query(Person).filter_by(id=view_kwargs['id']).one()
                except NoResultFound:
                    raise ObjectNotFound({'parameter': 'id'}, "Person: {} not found".format(view_kwargs['id']))
                else:
                    query_ = query_.join(Person).filter(Person.id == view_kwargs['id'])
            return query_

        def before_create_object(self, data, view_kwargs):
            if view_kwargs.get('id') is not None:
                person = self.session.query(Person).filter_by(id=view_kwargs['id']).one()
                data['person_id'] = person.id

        schema = ComputerSchema
        data_layer = {'session': db.session,
                      'model': Computer,
                      'methods': {'query': query,
                                  'before_create_object': before_create_object}}


    class ComputerDetail(ResourceDetail):
        schema = ComputerSchema
        data_layer = {'session': db.session,
                      'model': Computer}


    class ComputerRelationship(ResourceRelationship):
        schema = ComputerSchema
        data_layer = {'session': db.session,
                      'model': Computer}


    # Create endpoints
    api = Api(app)
    api.route(PersonList, 'person_list', '/persons')
    api.route(PersonDetail, 'person_detail', '/persons/<int:id>', '/computers/<int:computer_id>/owner')
    api.route(PersonRelationship, 'person_computers', '/persons/<int:id>/relationships/computers')
    api.route(ComputerList, 'computer_list', '/computers', '/persons/<int:id>/computers')
    api.route(ComputerDetail, 'computer_detail', '/computers/<int:id>')
    api.route(ComputerRelationship, 'computer_person', '/computers/<int:id>/relationships/owner')

    if __name__ == '__main__':
        # Start application
        app.run(debug=True)

This example provides this api:

+------------------------------------------+--------+------------------+-------------------------------------------------------+
| url                                      | method | endpoint         | action                                                |
+==========================================+========+==================+=======================================================+
| /persons                                 | GET    | person_list      | Retrieve a collection of persons                      |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons                                 | POST   | person_list      | Create a person                                       |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>                        | GET    | person_detail    | Retrieve details of a person                          |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>                        | PATCH  | person_detail    | Update a person                                       |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>                        | DELETE | person_detail    | Delete a person                                       |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/computers              | GET    | computer_list    | Retrieve a collection computers related to a person   |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/computers              | POST   | computer_list    | Create a computer related to a person                 |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/relationships/computers | GET    | person_computers | Retrieve relationships between a person and computers |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/relationships/computers | POST   | person_computers | Create relationships between a person and computers   |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/relationships/computers | PATCH  | person_computers | Update relationships between a person and computers   |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/relationships/computers | DELETE | person_computers | Delete relationships between a person and computers   |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers                               | GET    | computer_list    | Retrieve a collection of computers                    |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers                               | POST   | computer_list    | Create a computer                                     |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>                      | GET    | computer_detail  | Retrieve details of a computer                        |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>                      | PATCH  | computer_detail  | Update a computer                                     |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>                      | DELETE | computer_detail  | Delete a computer                                     |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/owner                | GET    | person_detail    | Retrieve details of the owner of a computer           |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/owner                | PATCH  | person_detail    | Update the owner of a computer                        |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/owner                | DELETE | person_detail    | Delete the owner of a computer                        |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/relationships/owner   | GET    | person_computers | Retrieve relationships between a person and computers |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/relationships/owner   | POST   | person_computers | Create relationships between a person and computers   |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/relationships/owner   | PATCH  | person_computers | Update relationships between a person and computers   |
+------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/relationships/owner   | DELETE | person_computers | Delete relationships between a person and computers   |
+------------------------------------------+--------+------------------+-------------------------------------------------------+

.. warning::

    In this example, I use Flask-SQLAlchemy so you have to install it before to run the example.

    $ pip install flask_sqlalchemy

Save this as api.py and run it using your Python interpreter. Note that we've enabled
`Flask debugging <http://flask.pocoo.org/docs/quickstart/#debug-mode>`_ mode to provide code reloading and better error
messages. ::

    $ python api.py
     * Running on http://127.0.0.1:5000/
     * Restarting with reloader

.. warning::

    Debug mode should never be used in a production environment!

Classical CRUD operations
-------------------------

Create object
~~~~~~~~~~~~~

Request:

.. sourcecode:: http

    POST /computers HTTP/1.1
    Content-Type: application/vnd.api+json
    Accept: application/vnd.api+json

    {
      "data": {
        "type": "computer",
        "attributes": {
          "serial": "Amstrad"
        }
      }
    }

Response:

.. sourcecode:: http

    HTTP/1.1 201 Created
    Content-Type: application/vnd.api+json

    {
      "data": {
        "type": "computer",
        "id": "1",
        "attributes": {
          "serial": "Amstrad"
        },
        "relationships": {
          "owner": {
            "links": {
              "related": "/computers/1/owner",
              "self": "/computers/1/relationships/owner"
            }
          }
        },
        "links": {
          "self": "/computers/1"
        }
      },
      "links": {
        "self": "/computers/1"
      },
      "jsonapi": {
        "version": "1.0"
      }
    }

List objects
~~~~~~~~~~~~

Request:

.. sourcecode:: http

    GET /computers HTTP/1.1
    Accept: application/vnd.api+json

Response:

.. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

    {
      "data": [
        {
          "type": "computer",
          "id": "1",
          "attributes": {
            "serial": "Amstrad"
          },
          "relationships": {
            "owner": {
              "links": {
                "related": "/computers/1/owner",
                "self": "/computers/1/relationships/owner"
              }
            }
          },
          "links": {
            "self": "/computers/1"
          }
        }
      ],
      "meta": {
        "count": 1
      },
      "links": {
        "self": "/computers"
      },
      "jsonapi": {
        "version": "1.0"
      },
    }

Update object
~~~~~~~~~~~~~

Request:

.. sourcecode:: http

    PATCH /computers/1 HTTP/1.1
    Content-Type: application/vnd.api+json
    Accept: application/vnd.api+json

    {
      "data": {
        "type": "computer",
        "id": "1",
        "attributes": {
          "serial": "Amstrad 2"
        }
      }
    }

Response:

.. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

    {
      "data": {
        "type": "computer",
        "id": "1",
        "attributes": {
          "serial": "Amstrad 2"
        },
        "relationships": {
          "owner": {
            "links": {
              "related": "/computers/1/owner",
              "self": "/computers/1/relationships/owner"
            }
          }
        },
        "links": {
          "self": "/computers/1"
        }
      },
      "links": {
        "self": "/computers/1"
      },
      "jsonapi": {
        "version": "1.0"
      }
    }

Delete object
~~~~~~~~~~~~~

Request:

.. sourcecode:: http

    DELETE /computers/1 HTTP/1.1
    Accept: application/vnd.api+json

Response:

.. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

    {
      "meta": {
        "message": "Object successfully deleted"
      },
      "jsonapi": {
        "version": "1.0"
      }
    }

Relationships
-------------

| Now let's use relationships tools. First, create 3 computers named Halo, Nestor and Comodor like in previous example.
|
| Done ?
| Ok. So let's continue this tutorial.
|
| We assume that Halo has id: 2, Nestor id: 3 and Comodor has id: 4.

Create object with related object(s)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Request:

.. sourcecode:: http

    POST /persons?include=computers HTTP/1.1
    Content-Type: application/vnd.api+json
    Accept: application/vnd.api+json

    {
      "data": {
        "type": "person",
        "attributes": {
          "name": "John",
          "email": "john@gmail.com",
          "birth_date": "1990-12-18"
        },
        "relationships": {
          "computers": {
            "data": [
              {
                "type": "computer",
                "id": "1"
              }
            ]
          }
        }
      }
    }

Response:

.. sourcecode:: http

    HTTP/1.1 201 Created
    Content-Type: application/vnd.api+json

    {
      "data": {
        "type": "person",
        "id": "1",
        "attributes": {
          "display_name": "JOHN <john@gmail.com>",
          "birth_date": "1990-12-18"
        },
        "links": {
          "self": "/persons/1"
        },
        "relationships": {
          "computers": {
            "data": [
              {
                "id": "1",
                "type": "computer"
              }
            ],
            "links": {
              "related": "/persons/1/computers",
              "self": "/persons/1/relationships/computers"
            }
          }
        },
      },
      "included": [
        {
          "type": "computer",
          "id": "1",
          "attributes": {
            "serial": "Amstrad"
          },
          "links": {
            "self": "/computers/1"
          },
          "relationships": {
            "owner": {
              "links": {
                "related": "/computers/1/owner",
                "self": "/computers/1/relationships/owner"
              }
            }
          }
        }
      ],
      "jsonapi": {
        "version": "1.0"
      },
      "links": {
        "self": "/persons/1"
      }
    }

You can see that I have added the querystring parameter "include" to the url

.. sourcecode:: http

    POST /persons?include=computers HTTP/1.1

Thanks to this parameter, related computers details are included to the result. If you want to learn more: :ref:`include_related_objects`

Update object and his relationships
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now John sell his Amstrad and buy a new computer named Nestor (id: 3). So we want to link this new computer to John. John have also made a mistake in his birth_date so let's update this 2 things in the same time.

Request:

.. sourcecode:: http

    PATCH /persons/1?include=computers HTTP/1.1
    Content-Type: application/vnd.api+json
    Accept: application/vnd.api+json

    {
      "data": {
        "type": "person",
        "id": "1",
        "attributes": {
          "birth_date": "1990-10-18"
        },
        "relationships": {
          "computers": {
            "data": [
              {
                "type": "computer",
                "id": "3"
              }
            ]
          }
        }
      }
    }

Response:

.. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

    {
      "data": {
        "type": "person",
        "id": "1",
        "attributes": {
          "display_name": "JOHN <john@gmail.com>",
          "birth_date": "1990-10-18",
        },
        "links": {
          "self": "/persons/1"
        },
        "relationships": {
          "computers": {
            "data": [
              {
                "id": "3",
                "type": "computer"
              }
            ],
            "links": {
              "related": "/persons/1/computers",
              "self": "/persons/1/relationships/computers"
            }
          }
        },
      },
      "included": [
        {
          "type": "computer",
          "id": "3",
          "attributes": {
            "serial": "Nestor"
          },
          "relationships": {
            "owner": {
              "links": {
                "related": "/computers/3/owner",
                "self": "/computers/3/relationships/owner"
              }
            }
          },
          "links": {
            "self": "/computers/3"
          }
        }
      ],
      "links": {
        "self": "/persons/1"
      },
      "jsonapi": {
        "version": "1.0"
      }
    }

Create relationship
~~~~~~~~~~~~~~~~~~~

Now John buy a new computer named Comodor so let's link it to John.

Request:

.. sourcecode:: http

    POST /persons/1/relationships/computers HTTP/1.1
    Content-Type: application/vnd.api+json
    Accept: application/vnd.api+json

    {
      "data": [
        {
          "type": "computer",
          "id": "4"
        }
      ]
    }

Response:

.. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

    {
      "data": {
        "type": "person",
        "id": "1",
        "attributes": {
          "display_name": "JOHN <john@gmail.com>",
          "birth_date": "1990-10-18"
        },
        "relationships": {
          "computers": {
            "data": [
              {
                "id": "3",
                "type": "computer"
              },
              {
                "id": "4",
                "type": "computer"
              }
            ],
            "links": {
              "related": "/persons/1/computers",
              "self": "/persons/1/relationships/computers"
            }
          }
        },
        "links": {
          "self": "/persons/1"
        }
      },
      "included": [
        {
          "type": "computer",
          "id": "3",
          "attributes": {
            "serial": "Nestor"
          },
          "relationships": {
            "owner": {
              "links": {
                "related": "/computers/3/owner",
                "self": "/computers/3/relationships/owner"
              }
            }
          },
          "links": {
            "self": "/computers/3"
          }
        },
        {
          "type": "computer",
          "id": "4",
          "attributes": {
            "serial": "Comodor"
          },
          "relationships": {
            "owner": {
              "links": {
                "related": "/computers/4/owner",
                "self": "/computers/4/relationships/owner"
              }
            }
          },
          "links": {
            "self": "/computers/4"
          }
        }
      ],
      "links": {
        "self": "/persons/1/relationships/computers"
      },
      "jsonapi": {
        "version": "1.0"
      }
    }


Delete relationship
~~~~~~~~~~~~~~~~~~~

Now John sell his old Nestor computer so let's unlink it from John.

Request:

.. sourcecode:: http

    DELETE /persons/1/relationships/computers HTTP/1.1
    Content-Type: application/vnd.api+json
    Accept: application/vnd.api+json

    {
      "data": [
        {
          "type": "computer",
          "id": "3"
        }
      ]
    }

Response:

.. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

    {
      "data": {
        "type": "person",
        "id": "1",
        "attributes": {
          "display_name": "JOHN <john@gmail.com>",
          "birth_date": "1990-10-18"
        },
        "relationships": {
          "computers": {
            "data": [
              {
                "id": "4",
                "type": "computer"
              }
            ],
            "links": {
              "related": "/persons/1/computers",
              "self": "/persons/1/relationships/computers"
            }
          }
        },
        "links": {
          "self": "/persons/1"
        }
      },
      "included": [
        {
          "type": "computer",
          "id": "4",
          "attributes": {
            "serial": "Comodor"
          },
          "relationships": {
            "owner": {
              "links": {
                "related": "/computers/4/owner",
                "self": "/computers/4/relationships/owner"
              }
            }
          },
          "links": {
            "self": "/computers/4"
          }
        }
      ],
      "links": {
          "self": "/persons/1/relationships/computers"
      },
      "jsonapi": {
          "version": "1.0"
      }
    }

If you want to see more examples go to `JSON API 1.0 specification <http://jsonapi.org/>`_
