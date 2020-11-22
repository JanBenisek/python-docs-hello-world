# %%
from azure.cosmos import CosmosClient
import json
from datetime import datetime

url = os.environ['URL']
key = os.environ['KEY']
client = CosmosClient(url, key)

database_name = "workoutdb"
container_name = "WorkoutSessions"

# %%
database = client.get_database_client(database_name)
container = database.get_container_client(container_name)

# %%
# List containers
for _cont in database.list_containers():
    print("Container ID: {}".format(_cont['id']))

# %%
# ========================
# POST request (insert)
# ========================

# get last ID
cont_items = container.query_items(
        query='SELECT VALUE MAX(r.sessionID) FROM WorkoutSessions r',
        enable_cross_partition_query=True)

for item in cont_items:
    lst_id = json.dumps(item, indent=True)
lst_id = int(lst_id.replace('"', ''))


# insert item
container.upsert_item(
        dict(id=str(lst_id+1),
             sessionID=str(lst_id+1),
             sessionStart=datetime.now().strftime("%Y-%m-%d %H:%M"),
             category="run",
             workout=dict(distance_km=10,
                          duraration_mins=45)))


# %%
# ========================
# PUT request (modifies an item)
# ========================
container = database.get_container_client(container_name)

item = container.read_item("1", partition_key="1")
item["workout"]['distanceKm'] = 11.6
updated_item = container.upsert_item(item)

# %%
# ========================
# GET request (select)
# ========================

for item in container.query_items(
    query='SELECT r.sessionStart, r.category FROM WorkoutSessions r',
    enable_cross_partition_query=True,
):
    print(json.dumps(item, indent=True))

# item = container.read_item("3", partition_key="3")
# container.delete_item(item, partition_key='3')

# %%
result = container.read_item('2', partition_key='2')

fields = ['sessionID','sessionStart','category','workout']

result_f = {your_key: result[your_key] for your_key in fields}

# %%
# ========================
# DELETE request (delete)
# ========================
cont_items = container.query_items(
        query='SELECT * FROM Running r WHERE r.sessionID="3"',
        enable_cross_partition_query=True)
for item in cont_items:
    container.delete_item(item, partition_key='3')

# item = container.read_item("3", partition_key="3")

# container.delete_item(item, partition_key='3')


# %%
