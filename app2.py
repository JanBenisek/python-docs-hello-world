# %%
from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from threading import Lock
from tenacity import *
import logging
import os
#
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
import json
from datetime import datetime
import re

# Initialize Flask
app = Flask(__name__)

# Setup Flask Restful framework
api = Api(app)
parser = reqparse.RequestParser()
parser.add_argument('session')


class ConnectionManager(object):
    '''
    Class which manages connection to Azure Cosmos DB
    (singleton to avoid global objects)
    '''
    __instance = None
    __connection = None
    __lock = Lock()

    def __new__(cls):
        if ConnectionManager.__instance is None:
            ConnectionManager.__instance = object.__new__(cls)
        return ConnectionManager.__instance

    def __getConnection(self):
        if (self.__connection is None):
            #url = os.environ['URL']
            #key = os.environ['KEY']
            url = "https://appworkout.documents.azure.com:443/"
            key = "0ou7KqW5gKWFE9HVlzWVyOT1SqXK3rKpsVvcz0FJ57gsjsa2WXcKtDxvFgM4QNE4Y81Cl74vgMSgEf035Kambw=="

            self.__connection = CosmosClient(url, key)

        return self.__connection

    def __removeConnection(self):
        self.__connection = None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(10),
           after=after_log(app.logger, logging.DEBUG))
    def getConnection(self, db_name: str, cont_name: str):
        try:
            client = self.__getConnection()

            database = client.get_database_client(db_name)
            container = database.get_container_client(cont_name)

        except Exception as e:
            app.logger.error(e)
            self.__removeConnection()
            raise

        return database, container


class Connectable(Resource):
    def __init__(self):
        self.container = 'WorkoutSessions'
        self.database = 'workoutdb'

    def getConnection(self):
        _, container = ConnectionManager().getConnection(
                db_name=self.database,
                cont_name=self.container)
        return container

# %%
# ============================================
# ---------------- GYM API -------------------
# ============================================
class Workout(Connectable):
    def __init__(self):
        self.fields = ['sessionID', 'sessionStart',
                       'category', 'workout']
        super().__init__()

    def get(self, sessionID: str):
        ''' gets data from server'''
        session = {}
        session["sessionID"] = sessionID
        container = self.getConnection()

        try:
            result = container.read_item(
                    session['sessionID'],
                    partition_key=session['sessionID'])

            result = {key: result[key] for key in self.fields}

            return result, 200
        except CosmosResourceNotFoundError as e:
            app.logger.error(e)
            abort(404, message="Session {} doesn't exist".format(
                session['sessionID']))

    def put(self, sessionID: str):
        ''' modifies data on server (create new if non-existent)'''
        p = re.compile('(?<!\\\\)\'')

        args = parser.parse_args()
        args['session'] = p.sub('\"', args['session'])
        session = json.loads(args['session'])

        container = self.getConnection()

        try:
            # get row currently stored
            current_record = container.read_item(
                        session['sessionID'],
                        partition_key=session['sessionID'])

            # Merge
            # https://stackoverflow.com/questions/38987/how-do-i-merge-two-dictionaries-in-a-single-expression-in-python-taking-union-o
            new_record = {**current_record, **session}

            new_record = {key: new_record[key] for key in self.fields}

            return new_record, 201
        except CosmosResourceNotFoundError as e:
            app.logger.error(e)
            abort(404, message="Session {} doesn't exist".format(
                session['sessionID']))

    def post(self):
        ''' pushes data to server'''
        p = re.compile('(?<!\\\\)\'')

        args = parser.parse_args()
        args['session'] = p.sub('\"', args['session'])
        session = json.loads(args['session'])

        container = self.getConnection()

        try:
            # fetch last id and +1
            cont_items = container.query_items(
                query='SELECT VALUE MAX(s.sessionID) FROM WorkoutSessions s',
                enable_cross_partition_query=True)

            for _session in cont_items:
                lst_sessionID = json.dumps(_session, indent=True)
            lst_sessionID = int(lst_sessionID.replace('"', ''))

            # insert
            new_record = dict(id=str(lst_sessionID+1),
                              sessionID=str(lst_sessionID+1),
                              sessionStart=session["sessionStart"],
                              category=session["category"],
                              workout=session["workout"])

            container.upsert_item(new_record)

            new_record = {key: new_record[key] for key in self.fields}

            return session, 202
        except CosmosResourceNotFoundError as e:
            app.logger.error(e)
            abort(404, message="Session {} doesn't exist".format(
                session['sessionID']))

    def delete(self, sessionID: str):
        ''' deletes data on server'''
        session = {}
        session["sessionID"] = sessionID
        container = self.getConnection()

        try:
            result = container.read_item(
                        session['sessionID'],
                        partition_key=session['sessionID'])
            container.delete_item(result, partition_key=session['sessionID'])

            result = {key: result[key] for key in self.fields}

            return result, 202
        except CosmosResourceNotFoundError as e:
            app.logger.error(e)
            abort(404, message="Session {} doesn't exist".format(
                session['sessionID']))


class AllSessions(Connectable):
    def get(self):
        ''' gets data from server'''
        container = self.getConnection()

        try:
            all_sessions = container.query_items(
                query=('SELECT r.sessionID, r.sessionStart, '
                       'r.category, r.workout FROM WorkoutSessions r'),
                enable_cross_partition_query=True)

            # Does not work
            # result = [x for item in all_sessions]

            result = []
            for item in all_sessions:
                result.append(item)

            return result, 200

        except CosmosResourceNotFoundError as e:
            app.logger.error(e)
            abort(404, message="Fetching all data failed.")


# ============================================
# -------------- API ROUTES ------------------
# ============================================
api.add_resource(Workout,
                 '/v1/WorkoutSession',
                 '/v1/WorkoutSession/<sessionID>')
api.add_resource(AllSessions, '/v1/all')


# Start App
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000)
